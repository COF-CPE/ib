from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from conftest import make_ohlcv
from fourlayer.backtest import run_backtest
from fourlayer.config import BacktestConfig, RiskConfig, SystemConfig
from fourlayer.metrics import summarize, trade_stats


def toy(prices, scores, atr_val=1.0):
    idx = pd.bdate_range("2025-01-01", periods=len(prices), name="date")
    px = pd.DataFrame(
        {"open": prices, "high": [p * 1.01 for p in prices],
         "low": [p * 0.99 for p in prices], "close": prices,
         "volume": [1e6] * len(prices)},
        index=idx,
    )
    sig = pd.DataFrame({"composite": scores, "atr": atr_val, "close": prices}, index=idx)
    return {"AAA": sig}, {"AAA": px}


def cfg_simple(**bt):
    base = SystemConfig()
    defaults = dict(
        initial_cash=10_000.0, max_positions=1, max_weight=1.0,
        commission_bps=0.0, slippage_bps=0.0,
    )
    return replace(
        base,
        backtest=replace(base.backtest, **{**defaults, **bt}),
        risk=replace(base.risk, stop_atr_multiple=2.0),
    )


def test_order_executes_at_next_open_not_signal_close():
    """La senal del dia 1 no puede operarse al cierre del dia 1."""
    prices = [100, 100, 120, 120, 120, 120]
    scores = [0, 2, 0, 0, 0, 0]  # senal de compra en el indice 1
    sig, px = toy(prices, scores)
    # Apertura del dia 2 distinta del cierre del dia 1, para distinguirlas.
    px["AAA"].iloc[2, px["AAA"].columns.get_loc("open")] = 110.0
    r = run_backtest(sig, px, cfg_simple())
    assert len(r.trades) == 1
    trade = r.trades.iloc[0]
    assert trade["entry_date"] == px["AAA"].index[2].date().isoformat()
    assert trade["entry_price"] == pytest.approx(110.0)


def test_no_trade_when_signal_is_on_the_last_bar():
    """Sin barra siguiente no hay ejecucion posible: no se inventa el fill."""
    sig, px = toy([100, 100, 100], [0, 0, 2])
    r = run_backtest(sig, px, cfg_simple())
    assert r.trades.empty


def test_exit_on_negative_signal():
    prices = [100] * 3 + [130] * 4
    scores = [2, 0, 0, 0, -2, 0, 0]
    sig, px = toy(prices, scores)
    r = run_backtest(sig, px, cfg_simple())
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "signal"
    assert t["return_pct"] == pytest.approx(30.0)


def test_stop_loss_at_two_atr():
    # ATR = 5 -> stop a 100 - 10 = 90. El dia 4 el minimo perfora ese nivel.
    prices = [100, 100, 100, 100, 92, 92]
    scores = [2, 0, 0, 0, 0, 0]
    sig, px = toy(prices, scores, atr_val=5.0)
    px["AAA"].iloc[4, px["AAA"].columns.get_loc("low")] = 85.0
    r = run_backtest(sig, px, cfg_simple())
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    assert t["exit_price"] == pytest.approx(90.0)


def test_stop_loss_respects_opening_gap():
    """Si abre por debajo del stop, se sale a la apertura, no al stop."""
    prices = [100, 100, 100, 100, 70, 70]
    scores = [2, 0, 0, 0, 0, 0]
    sig, px = toy(prices, scores, atr_val=5.0)
    px["AAA"].iloc[4, px["AAA"].columns.get_loc("open")] = 70.0
    px["AAA"].iloc[4, px["AAA"].columns.get_loc("low")] = 68.0
    r = run_backtest(sig, px, cfg_simple())
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    assert t["exit_price"] == pytest.approx(70.0)


def test_stop_does_not_fire_on_entry_bar():
    prices = [100, 100, 100, 100]
    scores = [2, 0, 0, 0]
    sig, px = toy(prices, scores, atr_val=5.0)
    px["AAA"].iloc[1, px["AAA"].columns.get_loc("low")] = 10.0  # barra de entrada
    r = run_backtest(sig, px, cfg_simple())
    assert r.trades.iloc[0]["exit_reason"] == "end_of_period"


def test_costs_reduce_the_result():
    prices = [100] * 3 + [130] * 3
    scores = [2, 0, 0, 0, -2, 0]
    sig, px = toy(prices, scores)
    free = run_backtest(sig, px, cfg_simple())
    costly = run_backtest(sig, px, cfg_simple(commission_bps=10.0, slippage_bps=25.0))
    assert costly.equity.iloc[-1] < free.equity.iloc[-1]


def test_max_positions_is_respected():
    idx = pd.bdate_range("2025-01-01", periods=6, name="date")
    sig, px = {}, {}
    for t in ("AAA", "BBB", "CCC"):
        px[t] = pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1e6}, index=idx
        )
        sig[t] = pd.DataFrame({"composite": 2, "atr": 1.0, "close": 100.0}, index=idx)
    cfg = cfg_simple()
    cfg = replace(cfg, backtest=replace(cfg.backtest, max_positions=2, max_weight=0.5))
    r = run_backtest(sig, px, cfg)
    assert r.daily["n_positions"].max() == 2


def test_equity_is_conserved_without_trades():
    sig, px = toy([100] * 5, [0] * 5)
    r = run_backtest(sig, px, cfg_simple())
    assert r.equity.nunique() == 1
    assert r.equity.iloc[-1] == pytest.approx(10_000.0)


def test_atr_risk_sizing_scales_with_volatility():
    cfg_low = cfg_simple(sizing="atr_risk", max_weight=1.0)
    cfg_low = replace(cfg_low, backtest=replace(cfg_low.backtest, risk_per_trade=0.02))
    calm, _ = toy([100] * 6, [2, 0, 0, 0, 0, 0], atr_val=1.0)
    wild, _ = toy([100] * 6, [2, 0, 0, 0, 0, 0], atr_val=10.0)
    _, px = toy([100] * 6, [2, 0, 0, 0, 0, 0])
    r_calm = run_backtest(calm, px, cfg_low)
    r_wild = run_backtest(wild, px, cfg_low)
    assert r_calm.trades.iloc[0]["shares"] > r_wild.trades.iloc[0]["shares"]


def test_benchmark_series_is_rebased_to_initial_cash():
    sig, px = toy([100] * 5, [0] * 5)
    bench = px["AAA"].copy() * 1.0
    r = run_backtest(sig, px, cfg_simple(), benchmark_prices=bench)
    assert r.benchmark.iloc[0] == pytest.approx(10_000.0)


def test_summary_and_hit_rate():
    prices = [100] * 3 + [130] * 3
    scores = [2, 0, 0, 0, -2, 0]
    sig, px = toy(prices, scores)
    r = run_backtest(sig, px, cfg_simple())
    s = summarize(r)
    assert s["n_trades"] == 1
    assert s["hit_rate_pct"] == 100.0
    assert s["total_return_pct"] > 0


def test_trade_stats_on_empty_frame():
    assert trade_stats(pd.DataFrame())["n_trades"] == 0


def test_empty_universe_raises():
    with pytest.raises(ValueError):
        run_backtest({}, {}, cfg_simple())


def test_summary_json_has_no_nan():
    """El resumen se serializa a JSON tal cual: nada de NaN ni inf."""
    import json
    import math

    sig, px = toy([100] * 5, [0] * 5)
    s = summarize(run_backtest(sig, px, cfg_simple()))
    for key, value in s.items():
        assert not (isinstance(value, float) and math.isnan(value)), key
    json.loads(json.dumps(s))  # json.dumps escribiria NaN, json.loads lo rechaza
