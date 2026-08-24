"""Orquestacion: de precios cacheados a senales, backtest y reporte."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from .backtest import BacktestResult, run_backtest
from .config import SystemConfig
from .data.store import PriceStore
from .layers import SignalContext, compute_signals, verdict_changes
from .metrics import per_ticker, summarize
from .providers import (
    EarningsCalendar,
    FundamentalProvider,
    MacroProvider,
    NeutralFundamental,
    NeutralMacro,
)


def build_signals(
    tickers,
    store: PriceStore,
    cfg: SystemConfig,
    macro: MacroProvider | None = None,
    fundamental: FundamentalProvider | None = None,
    earnings: EarningsCalendar | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, str]]:
    """Devuelve (senales, precios, descartes)."""
    macro = macro or NeutralMacro()
    fundamental = fundamental or NeutralFundamental()
    earnings = earnings or EarningsCalendar()

    prices, skipped = store.load_many(tickers)
    signals: dict[str, pd.DataFrame] = {}
    min_bars = cfg.warmup_bars + 20
    for ticker, df in list(prices.items()):
        if len(df) < min_bars:
            skipped[ticker] = f"solo {len(df)} barras, hacen falta {min_bars}"
            prices.pop(ticker)
            continue
        if df["volume"].fillna(0).sum() == 0:
            skipped[ticker] = "sin volumen: las capas de volumen no aplican"
        ctx = SignalContext(ticker, df, macro, fundamental, earnings)
        s = compute_signals(ctx, cfg)
        s["verdict_changed"] = verdict_changes(s["verdict"])
        liquid_from = first_liquid_bar(df["volume"], cfg.warmup_bars)
        if liquid_from is None:
            skipped[ticker] = (
                f"nunca acumula {cfg.warmup_bars} barras seguidas con volumen > 0"
            )
            prices.pop(ticker)
            continue
        if liquid_from > df.index[0]:
            s = neutralize_before(s, liquid_from, cfg)
            skipped[ticker] = (
                f"sin senal hasta {liquid_from.date()}: antes no hay "
                f"{cfg.warmup_bars} barras seguidas con volumen > 0"
            )
        signals[ticker] = s
    return signals, prices, skipped


def first_liquid_bar(volume: pd.Series, window: int):
    """Primera fecha con `window` barras consecutivas de volumen > 0 detras.

    Las acciones que fueron shells iliquidas (BMNR es el caso claro en esta
    cartera) traen cientos de barras sin operaciones: los indicadores que se
    calculan sobre ellas no describen ningun mercado y producen retornos
    fantasma. Preferimos no generar senal a generarla sobre precios que nadie
    negocio.
    """
    traded = (volume.fillna(0) > 0).astype("int8")
    run = traded.groupby((traded == 0).cumsum()).cumsum()
    ok = run[run >= window]
    return None if ok.empty else ok.index[0]


def neutralize_before(signals: pd.DataFrame, date, cfg: SystemConfig) -> pd.DataFrame:
    """Deja el veredicto en NEUTRAL antes de `date` sin tocar el resto."""
    out = signals.copy()
    mask = out.index < date
    if "composite" in out.columns:
        out.loc[mask, "composite"] = 0
    out.loc[mask, "verdict"] = "NEUTRAL"
    out["verdict_changed"] = verdict_changes(out["verdict"])
    return out


def run(
    tickers,
    store: PriceStore,
    cfg: SystemConfig,
    start: str | None = None,
    end: str | None = None,
    macro: MacroProvider | None = None,
    fundamental: FundamentalProvider | None = None,
    earnings: EarningsCalendar | None = None,
) -> tuple[BacktestResult, dict]:
    benchmark = cfg.backtest.benchmark
    universe = [t for t in tickers if t != benchmark]
    signals, prices, skipped = build_signals(
        universe, store, cfg, macro, fundamental, earnings
    )
    if not signals:
        raise RuntimeError(f"ningun ticker utilizable. Descartes: {skipped}")

    bench_df = None
    if store.has(benchmark):
        bench_df = store.load(benchmark)

    result = run_backtest(signals, prices, cfg, start=start, end=end, benchmark_prices=bench_df)
    result.skipped = skipped
    summary = summarize(result)
    summary["skipped"] = len(skipped)
    return result, summary


def sweep(
    tickers,
    store: PriceStore,
    base: SystemConfig,
    grid: list[dict],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Barrido de sensibilidad. Cada entrada de `grid` es un dict de overrides
    con claves `technical.*`, `backtest.*`, `risk.*` o `mode`."""
    rows = []
    for overrides in grid:
        cfg = _apply(base, overrides)
        try:
            _, summary = run(tickers, store, cfg, start=start, end=end)
        except Exception as e:  # noqa: BLE001
            rows.append({**overrides, "error": f"{type(e).__name__}: {e}"})
            continue
        rows.append({**overrides, **summary})
    return pd.DataFrame(rows)


def _apply(cfg: SystemConfig, overrides: dict) -> SystemConfig:
    tech, bt, risk, verdict, mode = cfg.technical, cfg.backtest, cfg.risk, cfg.verdict, cfg.mode
    t_kw, b_kw, r_kw, v_kw = {}, {}, {}, {}
    for key, value in overrides.items():
        section, _, field = key.partition(".")
        if not field:
            if section == "mode":
                mode = value
                continue
            raise KeyError(f"override sin seccion: {key}")
        {"technical": t_kw, "backtest": b_kw, "risk": r_kw, "verdict": v_kw}[section][field] = value
    return replace(
        cfg,
        mode=mode,
        technical=replace(tech, **t_kw) if t_kw else tech,
        backtest=replace(bt, **b_kw) if b_kw else bt,
        risk=replace(risk, **r_kw) if r_kw else risk,
        verdict=replace(verdict, **v_kw) if v_kw else verdict,
    )
