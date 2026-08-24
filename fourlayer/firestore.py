"""Serializacion al mismo esquema que el historial en Firestore.

El sistema en produccion guarda un documento por analisis (tope 200 entradas
por ticker) para poder medir el hit rate real. El backtest emite exactamente
la misma forma, de modo que un veredicto simulado de 2025 y uno real de hoy
sean comparables fila a fila.

Coleccion sugerida:  analyses/{ticker}/history/{iso_date}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SCHEMA_VERSION = "4layer-1.0"
HISTORY_LIMIT = 200


def _num(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 6)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float):
        return round(v, 6)
    return v


def analysis_record(ticker: str, row: pd.Series, mode: str, source: str = "backtest") -> dict:
    """Un documento de analisis, con las 4 capas desglosadas."""
    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "date": row.name.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "mode": mode,
        "verdict": row.get("verdict"),
        "score": _num(row.get("composite")),
        "price": _num(row.get("close")),
        "layers": {
            "macro": _num(row.get("layer1_macro")),
            "fundamental": _num(row.get("layer2_fundamental")),
            "technical_long": _num(row.get("layer3_long")),
            "technical_short": _num(row.get("layer4_short")),
        },
        "layer_detail": {
            "short_alignment": _num(row.get("short_align")),
            "long_alignment": _num(row.get("long_align")),
            "ma_score": _num(row.get("ma_score")),
            "short_soft": _num(row.get("short_soft")),
            "long_soft": _num(row.get("long_soft")),
        },
        "extras": {
            "rsi14": _num(row.get("rsi14")),
            "rsi_zone": _num(row.get("rsi_zone")),
            "volume_ratio": _num(row.get("volume_ratio")),
            "volume_confirm": _num(row.get("volume_confirm")),
            "divergence_short": _num(row.get("divergence_short")),
            "divergence_long": _num(row.get("divergence_long")),
            "drawdown_63": _num(row.get("drawdown_63")),
            "dip_bonus": _num(row.get("dip_bonus")),
            "structural_issue": bool(row.get("structural_issue", False)),
        },
        "risk": {
            "atr": _num(row.get("atr")),
            "stop_suggested": _num(row.get("stop_suggested")),
            "stop_atr_multiple": 2.0,
        },
        "earnings": {
            "days_to_report": _num(row.get("days_to_earnings")),
            "warning": bool(row.get("earnings_warning", False)),
        },
        "verdict_changed": bool(row.get("verdict_changed", False)),
    }


def history_for(
    ticker: str, signals: pd.DataFrame, mode: str, limit: int = HISTORY_LIMIT,
    only_changes: bool = False,
) -> list[dict]:
    """Historial de un ticker, mas reciente primero, recortado a `limit`."""
    df = signals.copy()
    if "verdict_changed" not in df.columns:
        prev = df["verdict"].shift(1)
        df["verdict_changed"] = (df["verdict"] != prev) & prev.notna()
    if only_changes:
        df = df[df["verdict_changed"]]
    df = df.dropna(subset=["verdict"]).tail(limit)
    return [analysis_record(ticker, row, mode) for _, row in df.iloc[::-1].iterrows()]


def backtest_record(summary: dict, cfg, universe: Iterable[str], notes: str = "") -> dict:
    """Documento de resumen del backtest (coleccion `backtests`)."""
    t, b = cfg.technical, cfg.backtest
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "backtest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "mode": cfg.mode,
            "alignment": t.alignment,
            "aggregation": t.aggregation,
            "rsi_mode": t.rsi_mode,
            "require_both_windows": t.require_both_windows,
            "thresholds": {"full": cfg.verdict.full, "weak": cfg.verdict.weak},
            "stop_atr_multiple": cfg.risk.stop_atr_multiple,
            "sizing": b.sizing,
            "max_positions": b.max_positions,
            "max_weight": b.max_weight,
            "execution": f"t+{b.execution_lag} @ {b.execution_price}",
            "commission_bps": b.commission_bps,
            "slippage_bps": b.slippage_bps,
        },
        "universe": sorted(universe),
        "results": summary,
        "notes": notes,
    }


def dump(records, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(records, indent=2, ensure_ascii=False, default=str))
    return p
