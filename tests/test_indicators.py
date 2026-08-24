import numpy as np
import pandas as pd
import pytest

from conftest import make_ohlcv
from fourlayer.indicators import (
    atr, macd, rolling_drawdown, rsi, rsi_divergence, sma, stoch_rsi, volume_ratio,
)


def test_rsi_bounds_and_warmup(ohlcv):
    r = rsi(ohlcv["close"], 14)
    assert r.iloc[:13].isna().all()
    valid = r.dropna()
    assert valid.between(0, 100).all()


def test_rsi_all_up_is_100():
    s = pd.Series(np.arange(1, 60, dtype=float))
    assert rsi(s, 14).iloc[-1] == pytest.approx(100.0)


def test_macd_requires_fast_lt_slow():
    s = pd.Series(np.arange(1, 60, dtype=float))
    with pytest.raises(ValueError):
        macd(s, 26, 12, 9)


def test_stoch_rsi_in_unit_interval(ohlcv):
    k, d = stoch_rsi(ohlcv["close"], 14, 14)
    assert k.dropna().between(0, 1).all()
    assert d.dropna().between(0, 1).all()


def test_atr_positive_and_needs_ohlc(ohlcv):
    a = atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14)
    assert (a.dropna() > 0).all()
    # El ATR usa el rango real: aplanar high/low al cierre lo reduce.
    flat = atr(ohlcv["close"], ohlcv["close"], ohlcv["close"], 14)
    assert flat.dropna().mean() < a.dropna().mean()


def test_rolling_drawdown_is_non_positive(ohlcv):
    dd = rolling_drawdown(ohlcv["close"], 63)
    assert (dd.dropna() <= 1e-12).all()


def test_volume_ratio_around_one(ohlcv):
    v = volume_ratio(ohlcv["volume"], 20).dropna()
    assert 0.5 < v.mean() < 2.0


@pytest.mark.parametrize("fn", ["rsi", "macd", "stoch_rsi", "atr", "sma", "volume_ratio", "divergence"])
def test_indicators_are_causal(fn):
    """El valor en t no puede cambiar cuando aparecen barras posteriores.

    Es la propiedad que hace posible el walk-forward: si fallara, todo el
    backtest estaria mirando el futuro.
    """
    full = make_ohlcv(n=400, seed=11)
    cut = 300
    prefix = full.iloc[:cut]

    def compute(df):
        if fn == "rsi":
            return rsi(df["close"], 14)
        if fn == "macd":
            return macd(df["close"], 12, 26, 9)[0]
        if fn == "stoch_rsi":
            return stoch_rsi(df["close"], 14, 14)[0]
        if fn == "atr":
            return atr(df["high"], df["low"], df["close"], 14)
        if fn == "sma":
            return sma(df["close"], 50)
        if fn == "volume_ratio":
            return volume_ratio(df["volume"], 20)
        return rsi_divergence(df["close"], rsi(df["close"], 14), 20)

    a = compute(full).iloc[:cut]
    b = compute(prefix)
    pd.testing.assert_series_equal(a, b, check_names=False, rtol=1e-9, atol=1e-9)
