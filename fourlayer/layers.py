"""Las 4 capas y el score compuesto.

Contrato del brief: cada capa aporta +1 (compra) / 0 (neutral) / -1 (venta), y
el compuesto es la suma de las 4 -> rango [-4, +4], que es exactamente lo que
hacen falta para que los umbrales >=4 / >=2 signifiquen lo que dicen.

Los "extras aprobados" (zonas de RSI, volumen, divergencias, caida >15%) no se
suman por fuera: alimentan el sub-score continuo de la capa tecnica que les
corresponde y luego la capa entera se discretiza a +-1. Si se sumaran aparte,
el compuesto podria pasar de 4 sin que las 4 capas estuvieran alineadas y los
umbrales dejarian de tener sentido.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SystemConfig, TechnicalConfig, Window
from .indicators import (
    atr,
    macd,
    rolling_drawdown,
    rsi,
    rsi_divergence,
    sma,
    stoch_rsi,
    volume_ratio,
)
from .providers import (
    EarningsCalendar,
    FundamentalProvider,
    MacroProvider,
    NeutralFundamental,
    NeutralMacro,
)

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def _sign_vote(series: pd.Series, low: float, high: float, invert: bool) -> pd.Series:
    """Voto {-1,0,+1}: por debajo de `low` y por encima de `high`.

    invert=True -> zona baja es compra (sobreventa). invert=False -> zona baja
    es venta (momentum).
    """
    out = pd.Series(0, index=series.index, dtype="int8")
    below, above = series < low, series > high
    if invert:
        out[below.fillna(False)] = 1
        out[above.fillna(False)] = -1
    else:
        out[below.fillna(False)] = -1
        out[above.fillna(False)] = 1
    return out


def window_votes(ohlcv: pd.DataFrame, w: Window, rsi_mode: str) -> pd.DataFrame:
    """Voto de RSI, MACD y StochRSI para una ventana temporal."""
    close = ohlcv["close"]

    r = rsi(close, w.rsi_period)
    if rsi_mode == "zones":
        # Reversion a la media: sobreventa = compra.
        r_vote = _sign_vote(r, w.rsi_oversold, w.rsi_overbought, invert=True)
    elif rsi_mode == "midline":
        # Momentum: por encima de 50 = compra.
        r_vote = _sign_vote(r, 50.0, 50.0, invert=False)
    else:
        raise ValueError(f"rsi_mode desconocido: {rsi_mode}")

    line, sig, _ = macd(close, *w.macd)
    m_vote = pd.Series(0, index=close.index, dtype="int8")
    m_vote[(line > sig).fillna(False)] = 1
    m_vote[(line < sig).fillna(False)] = -1
    m_vote[line.isna() | sig.isna()] = 0

    k, _d = stoch_rsi(close, w.rsi_period, w.stoch_period)
    s_vote = _sign_vote(k, w.stoch_low, w.stoch_high, invert=True)

    return pd.DataFrame(
        {f"{w.name}_rsi": r_vote, f"{w.name}_macd": m_vote, f"{w.name}_stoch": s_vote}
    )


def align(votes: pd.DataFrame, alignment: str) -> pd.Series:
    """Reduce los 3 votos de una ventana a uno solo.

    strict: los 3 apuntan al mismo lado (ninguno en contra, ninguno neutral).
    loose : 2 de 3 apuntan al mismo lado y el tercero no apunta al contrario.
    """
    need = 3 if alignment == "strict" else 2
    if alignment not in ("strict", "loose"):
        raise ValueError(f"alignment desconocido: {alignment}")
    ups = (votes > 0).sum(axis=1)
    downs = (votes < 0).sum(axis=1)
    out = pd.Series(0, index=votes.index, dtype="int8")
    out[(ups >= need) & (downs == 0)] = 1
    out[(downs >= need) & (ups == 0)] = -1
    return out


def _combine_windows(a: pd.Series, b: pd.Series, require_both: bool) -> pd.Series:
    out = pd.Series(0, index=a.index, dtype="int8")
    if require_both:
        out[(a > 0) & (b > 0)] = 1
        out[(a < 0) & (b < 0)] = -1
    else:
        total = a.astype("int16") + b.astype("int16")
        out[total > 0] = 1
        out[total < 0] = -1
    return out


def _discretize(soft: pd.Series, threshold: float) -> pd.Series:
    out = pd.Series(0, index=soft.index, dtype="int8")
    out[soft >= threshold] = 1
    out[soft <= -threshold] = -1
    return out


def technical_layers(
    ohlcv: pd.DataFrame,
    cfg: TechnicalConfig,
    structural_issue: pd.Series | None = None,
) -> pd.DataFrame:
    """Capas 3 (tecnico largo) y 4 (tecnico corto) sobre OHLCV real."""
    missing = [c for c in REQUIRED_COLUMNS if c not in ohlcv.columns]
    if missing:
        raise ValueError(f"faltan columnas OHLCV: {missing}")

    close, vol = ohlcv["close"], ohlcv["volume"]
    idx = ohlcv.index
    if structural_issue is None:
        structural_issue = pd.Series(False, index=idx)
    structural_issue = structural_issue.reindex(idx).fillna(False).astype(bool)

    # --- Capa 4: tecnico corto (1 y 2 semanas) ---
    sw_a, sw_b = cfg.short_windows
    va = align(window_votes(ohlcv, sw_a, cfg.rsi_mode), cfg.alignment)
    vb = align(window_votes(ohlcv, sw_b, cfg.rsi_mode), cfg.alignment)
    short_align = _combine_windows(va, vb, cfg.require_both_windows)

    # Medias moviles diarias 20/50/200, mas peso a las de periodo mayor.
    p20, p50, p200 = cfg.ma_periods
    w20, w50, w200 = cfg.ma_weights
    ma_score = pd.Series(0.0, index=idx)
    ma_valid = pd.Series(True, index=idx)
    for period, weight in ((p20, w20), (p50, w50), (p200, w200)):
        ma = sma(close, period)
        ma_valid &= ma.notna()
        ma_score += np.sign(close - ma).fillna(0.0) * weight
    ma_score = ma_score.where(ma_valid, 0.0)
    ma_vote = _discretize(ma_score, cfg.ma_vote_threshold)

    # Caida >15% desde el maximo de 63 dias: suma a compra, salvo problema
    # estructural en el fundamental (ahi la caida es informacion, no descuento).
    dd = rolling_drawdown(close, cfg.dip_window)
    dip = ((dd < cfg.dip_threshold) & ~structural_issue).astype("int8")

    # Zonas absolutas de RSI (extra aprobado).
    rsi_zone_series = rsi(close, cfg.rsi_zone_period)
    rsi_zone = _sign_vote(
        rsi_zone_series, cfg.rsi_zone_oversold, cfg.rsi_zone_overbought, invert=True
    )

    # Confirmacion por volumen: solo confirma, nunca origina la senal.
    vratio = volume_ratio(vol, cfg.volume_period)
    confirmed = (vratio >= cfg.volume_confirm_ratio).fillna(False)
    vol_confirm = (short_align * confirmed.astype("int8")).astype("int8")

    div_short = rsi_divergence(close, rsi_zone_series, cfg.divergence_lookback_short)

    short_soft = (
        cfg.w_short_alignment * short_align
        + cfg.w_ma * ma_vote
        + cfg.w_dip * dip
        + cfg.w_rsi_zone * rsi_zone
        + cfg.w_volume * vol_confirm
        + cfg.w_divergence_short * div_short
    ).clip(-1.0, 1.0)
    short_layer = _discretize(short_soft, cfg.layer_vote_threshold)

    # --- Capa 3: tecnico largo (1 y 2 meses) ---
    lw_a, lw_b = cfg.long_windows
    la = align(window_votes(ohlcv, lw_a, cfg.rsi_mode), cfg.alignment)
    lb = align(window_votes(ohlcv, lw_b, cfg.rsi_mode), cfg.alignment)
    long_align = _combine_windows(la, lb, cfg.require_both_windows)

    rsi_long = rsi(close, lw_b.rsi_period)
    rsi_zone_long = _sign_vote(rsi_long, lw_b.rsi_oversold, lw_b.rsi_overbought, invert=True)
    div_long = rsi_divergence(close, rsi_long, cfg.divergence_lookback_long)

    long_soft = (
        cfg.w_long_alignment * long_align
        + cfg.w_long_rsi_zone * rsi_zone_long
        + cfg.w_divergence_long * div_long
    ).clip(-1.0, 1.0)
    long_layer = _discretize(long_soft, cfg.layer_vote_threshold)

    return pd.DataFrame(
        {
            "close": close,
            "short_align_a": va,
            "short_align_b": vb,
            "short_align": short_align,
            "ma_score": ma_score,
            "ma_vote": ma_vote,
            "drawdown_63": dd,
            "dip_bonus": dip,
            "rsi14": rsi_zone_series,
            "rsi_zone": rsi_zone,
            "volume_ratio": vratio,
            "volume_confirm": vol_confirm,
            "divergence_short": div_short,
            "short_soft": short_soft,
            "layer4_short": short_layer,
            "long_align_a": la,
            "long_align_b": lb,
            "long_align": long_align,
            "rsi_long": rsi_long,
            "rsi_zone_long": rsi_zone_long,
            "divergence_long": div_long,
            "long_soft": long_soft,
            "layer3_long": long_layer,
        }
    )


@dataclass
class SignalContext:
    """Todo lo que hace falta para puntuar un ticker, ya resuelto."""

    ticker: str
    ohlcv: pd.DataFrame
    macro: MacroProvider
    fundamental: FundamentalProvider
    earnings: EarningsCalendar


def compute_signals(ctx: SignalContext, cfg: SystemConfig) -> pd.DataFrame:
    """Serie temporal completa de capas, score compuesto y veredicto.

    Cada fila t se calcula solo con datos <= t. El backtest se encarga de
    ejecutar con el retardo configurado.
    """
    idx = ctx.ohlcv.index

    # Capa 2 primero: structural_issue condiciona el bono de caida de la capa 4.
    readings = [ctx.fundamental.reading_on(ctx.ticker, d) for d in idx]
    fundamental_vote = pd.Series(
        [r.score for r in readings], index=idx, dtype="int8", name="layer2_fundamental"
    )
    structural = pd.Series([r.structural_issue for r in readings], index=idx, name="structural_issue")

    tech = technical_layers(ctx.ohlcv, cfg.technical, structural_issue=structural)

    macro_vote = pd.Series(
        [ctx.macro.score_on(d) for d in idx], index=idx, dtype="int8", name="layer1_macro"
    )

    out = tech.copy()
    out["layer1_macro"] = macro_vote
    out["layer2_fundamental"] = fundamental_vote
    out["structural_issue"] = structural

    if cfg.mode == "scanner":
        # El Scanner solo ve las capas tecnicas.
        out["layer1_macro"] = 0
        out["layer2_fundamental"] = 0

    technical_sum = out["layer3_long"].astype("int16") + out["layer4_short"].astype("int16")
    if cfg.technical.aggregation == "prototype":
        # Reproduccion del motor del chat: extras sumados por fuera de la capa.
        composite = (
            technical_sum
            + out["ma_vote"].astype("int16")
            + out["dip_bonus"].astype("int16")
            + out["rsi_zone"].astype("int16")
            + out["volume_confirm"].astype("int16")
            + out["divergence_short"].astype("int16")
        )
    else:
        composite = technical_sum
    if cfg.mode == "full":
        composite = composite + out["layer1_macro"].astype("int16") + out["layer2_fundamental"].astype("int16")
    out["composite"] = composite
    out["verdict"] = verdicts(composite, cfg)

    # ATR para el stop 2x y advertencia de earnings.
    out["atr"] = atr(ctx.ohlcv["high"], ctx.ohlcv["low"], ctx.ohlcv["close"], cfg.risk.atr_period)
    out["stop_suggested"] = out["close"] - cfg.risk.stop_atr_multiple * out["atr"]
    out["days_to_earnings"] = [
        ctx.earnings.days_to_earnings(ctx.ticker, d) for d in idx
    ]
    out["earnings_warning"] = out["days_to_earnings"].notna() & (
        out["days_to_earnings"] <= cfg.risk.earnings_warning_days
    )
    out["ticker"] = ctx.ticker
    return out


VERDICT_ORDER = ["VENDER", "VENDER_DEBIL", "NEUTRAL", "COMPRAR_DEBIL", "COMPRAR"]


def verdicts(composite: pd.Series, cfg: SystemConfig) -> pd.Series:
    """Traduce el score compuesto a veredicto, respetando el tope del Scanner."""
    v = cfg.verdict
    scanner_capped = cfg.mode == "scanner" and v.scanner_caps_at_weak
    out = pd.Series("NEUTRAL", index=composite.index, dtype="object")
    out[composite >= v.weak] = "COMPRAR_DEBIL"
    out[composite <= -v.weak] = "VENDER_DEBIL"
    if not scanner_capped:
        out[composite >= v.full] = "COMPRAR"
        out[composite <= -v.full] = "VENDER"
    return out.rename("verdict")


def verdict_changes(verdict: pd.Series) -> pd.Series:
    """Alerta de cambio de veredicto entre analisis consecutivos."""
    prev = verdict.shift(1)
    changed = (verdict != prev) & prev.notna()
    return changed.rename("verdict_changed")
