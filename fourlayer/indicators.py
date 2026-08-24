"""Indicadores tecnicos parametrizables sobre OHLCV.

Todas las funciones devuelven Series alineadas al indice de entrada y son
estrictamente causales: el valor en la barra t solo usa datos <= t. Eso es lo
que permite usarlas en un backtest walk-forward sin sesgo retrospectivo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "rsi",
    "macd",
    "stoch_rsi",
    "atr",
    "sma",
    "ema",
    "rolling_drawdown",
    "volume_ratio",
    "rsi_divergence",
    "true_range",
]


def _as_series(x: pd.Series | pd.DataFrame, name: str) -> pd.Series:
    if isinstance(x, pd.DataFrame):
        raise TypeError(f"{name}: se esperaba una Series, llego un DataFrame")
    return x.astype("float64")


def ema(series: pd.Series, span: int) -> pd.Series:
    return _as_series(series, "series").ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return _as_series(series, "series").rolling(period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI de Wilder (suavizado exponencial con alpha = 1/period)."""
    s = _as_series(series, "series")
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 con avg_gain > 0 => RSI 100; ambos 0 => sin informacion.
    flat = (avg_loss == 0) & (avg_gain == 0)
    out = out.where(~(avg_loss == 0), 100.0)
    out = out.where(~flat, np.nan)
    return out.rename("rsi")


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Devuelve (linea MACD, linea de senal, histograma)."""
    if fast >= slow:
        raise ValueError(f"macd: fast ({fast}) debe ser < slow ({slow})")
    s = _as_series(series, "series")
    line = ema(s, fast) - ema(s, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    # Antes de tener `slow` barras las EMA no estan formadas: se invalida.
    warmup = slow + signal
    line = line.where(np.arange(len(s)) >= slow - 1)
    sig = sig.where(np.arange(len(s)) >= warmup - 1)
    return line.rename("macd"), sig.rename("macd_signal"), (line - sig).rename("macd_hist")


def stoch_rsi(
    series: pd.Series, rsi_period: int = 14, stoch_period: int | None = None,
    k: int = 3, d: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """StochRSI en [0, 1]. Devuelve (%K suavizado, %D)."""
    stoch_period = stoch_period or rsi_period
    r = rsi(series, rsi_period)
    lo = r.rolling(stoch_period, min_periods=stoch_period).min()
    hi = r.rolling(stoch_period, min_periods=stoch_period).max()
    rng = (hi - lo).replace(0.0, np.nan)
    raw = ((r - lo) / rng).clip(0.0, 1.0)
    k_line = raw.rolling(k, min_periods=k).mean() if k > 1 else raw
    d_line = k_line.rolling(d, min_periods=d).mean() if d > 1 else k_line
    return k_line.rename("stochrsi_k"), d_line.rename("stochrsi_d")


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rename("true_range")


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR de Wilder. Necesita OHLC real, no solo cierre."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().rename("atr")


def rolling_drawdown(close: pd.Series, window: int = 63) -> pd.Series:
    """Caida porcentual (negativa) desde el maximo movil de `window` barras."""
    roll_max = close.rolling(window, min_periods=window).max()
    return ((close - roll_max) / roll_max).rename("drawdown")


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Volumen de la barra dividido por su media movil. >1 = volumen alto."""
    v = _as_series(volume, "volume")
    avg = v.rolling(period, min_periods=period).mean().replace(0.0, np.nan)
    return (v / avg).rename("volume_ratio")


def rsi_divergence(
    close: pd.Series, rsi_series: pd.Series, lookback: int = 20, min_gap: int = 5
) -> pd.Series:
    """Divergencia precio/RSI en {-1, 0, +1}, calculada de forma causal.

    +1 (alcista): el precio marca un minimo mas bajo que el minimo previo de la
    ventana pero el RSI marca un minimo mas alto.
    -1 (bajista): el precio marca un maximo mas alto pero el RSI no lo confirma.

    `min_gap` evita comparar la barra actual contra sus vecinas inmediatas.
    """
    c = _as_series(close, "close")
    r = _as_series(rsi_series, "rsi")
    n = len(c)
    out = np.zeros(n, dtype="int8")
    c_v, r_v = c.to_numpy(), r.to_numpy()

    for i in range(lookback, n):
        past_lo = slice(i - lookback, i - min_gap + 1)
        if np.isnan(r_v[i]) or np.isnan(c_v[i]):
            continue
        window_c = c_v[past_lo]
        window_r = r_v[past_lo]
        if np.all(np.isnan(window_r)):
            continue
        j_min = int(np.nanargmin(window_c))
        j_max = int(np.nanargmax(window_c))
        # Divergencia alcista: nuevo minimo de precio, RSI mas alto.
        if c_v[i] < window_c[j_min] and not np.isnan(window_r[j_min]) and r_v[i] > window_r[j_min]:
            out[i] = 1
        # Divergencia bajista: nuevo maximo de precio, RSI mas bajo.
        elif c_v[i] > window_c[j_max] and not np.isnan(window_r[j_max]) and r_v[i] < window_r[j_max]:
            out[i] = -1
    return pd.Series(out, index=c.index, name="rsi_divergence")
