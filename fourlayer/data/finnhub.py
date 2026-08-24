"""Conector Finnhub: fundamentales historicos y calendario de earnings.

Necesita `FINNHUB_API_KEY` en el entorno. El cliente cachea en disco con TTL
(3 dias para fundamentales, como el sistema en produccion; 1 dia para el
calendario) y degrada a `None` sin lanzar cuando no hay clave o no hay red,
para que el backtest pueda correr en modo solo-tecnico sin tocar codigo.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd

BASE = "https://finnhub.io/api/v1"
FUNDAMENTAL_TTL = 3 * 24 * 3600
CALENDAR_TTL = 24 * 3600


class FinnhubClient:
    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str | Path = "data/finnhub_cache",
        timeout: float = 20.0,
    ):
        self.api_key = api_key or os.environ.get("FINNHUB_API_KEY")
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------ #
    def _cached(self, key: str, ttl: float) -> Any | None:
        p = self.cache / f"{key}.json"
        if not p.exists() or time.time() - p.stat().st_mtime > ttl:
            return None
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return None

    def _store(self, key: str, payload: Any) -> None:
        (self.cache / f"{key}.json").write_text(json.dumps(payload))

    def _get(self, endpoint: str, params: dict, key: str, ttl: float) -> Any | None:
        hit = self._cached(key, ttl)
        if hit is not None:
            return hit
        if not self.enabled:
            self.last_error = "FINNHUB_API_KEY no definida"
            return None
        try:
            import requests  # import diferido: el motor no depende de red

            r = requests.get(
                f"{BASE}/{endpoint}", params={**params, "token": self.api_key},
                timeout=self.timeout,
            )
            r.raise_for_status()
            payload = r.json()
        except Exception as e:  # noqa: BLE001
            self.last_error = f"{type(e).__name__}: {e}"
            return None
        self._store(key, payload)
        return payload

    # ------------------------------------------------------------------ #
    def basic_financials(self, ticker: str) -> dict | None:
        """Ratios financieros (`metric` + series anuales/trimestrales)."""
        return self._get(
            "stock/metric", {"symbol": ticker, "metric": "all"},
            key=f"metric_{ticker}", ttl=FUNDAMENTAL_TTL,
        )

    def earnings_calendar(self, ticker: str, frm: str, to: str) -> dict | None:
        return self._get(
            "calendar/earnings", {"symbol": ticker, "from": frm, "to": to},
            key=f"earnings_{ticker}_{frm}_{to}", ttl=CALENDAR_TTL,
        )

    def reported_financials(self, ticker: str, freq: str = "quarterly") -> dict | None:
        """Reportes con `filedDate`: la fecha que evita el sesgo retrospectivo."""
        return self._get(
            "stock/financials-reported", {"symbol": ticker, "freq": freq},
            key=f"financials_{ticker}_{freq}", ttl=FUNDAMENTAL_TTL,
        )

    # ------------------------------------------------------------------ #
    def earnings_dates(self, ticker: str, frm: str, to: str) -> list[pd.Timestamp]:
        payload = self.earnings_calendar(ticker, frm, to)
        if not payload:
            return []
        return sorted(
            pd.Timestamp(row["date"])
            for row in payload.get("earningsCalendar", [])
            if row.get("date")
        )


def score_fundamentals(metric: dict) -> tuple[int, bool, str]:
    """Traduce los ratios de Finnhub a voto de capa 2 y `structural_issue`.

    Heuristica deliberadamente simple y auditable: cuenta senales positivas y
    negativas sobre margen, crecimiento, deuda y rentabilidad. `structural_issue`
    se marca cuando hay deterioro grave (patrimonio negativo, deuda/equity
    disparada o margen operativo negativo), que es lo que en el sistema anula
    el bono por caida >15%.
    """
    m = (metric or {}).get("metric", {})

    def g(*names, default=None):
        for n in names:
            v = m.get(n)
            if v is not None:
                return float(v)
        return default

    pos = neg = 0
    notes = []
    roe = g("roeTTM", "roeRfy")
    if roe is not None:
        (pos, neg) = (pos + 1, neg) if roe > 12 else ((pos, neg + 1) if roe < 0 else (pos, neg))
        notes.append(f"roe={roe:.1f}")
    op_margin = g("operatingMarginTTM", "operatingMarginAnnual")
    if op_margin is not None:
        (pos, neg) = (pos + 1, neg) if op_margin > 10 else ((pos, neg + 1) if op_margin < 0 else (pos, neg))
        notes.append(f"opm={op_margin:.1f}")
    rev_growth = g("revenueGrowthTTMYoy", "revenueGrowth5Y")
    if rev_growth is not None:
        (pos, neg) = (pos + 1, neg) if rev_growth > 5 else ((pos, neg + 1) if rev_growth < -5 else (pos, neg))
        notes.append(f"rev={rev_growth:.1f}")
    de = g("totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual")
    if de is not None:
        (pos, neg) = (pos + 1, neg) if de < 100 else ((pos, neg + 1) if de > 250 else (pos, neg))
        notes.append(f"d/e={de:.0f}")
    current = g("currentRatioQuarterly", "currentRatioAnnual")
    if current is not None:
        (pos, neg) = (pos + 1, neg) if current > 1.5 else ((pos, neg + 1) if current < 1 else (pos, neg))
        notes.append(f"cr={current:.2f}")

    structural = bool(
        (op_margin is not None and op_margin < -10)
        or (de is not None and de > 400)
        or (roe is not None and roe < -20)
    )
    score = 1 if pos - neg >= 2 else (-1 if neg - pos >= 2 else 0)
    return score, structural, ",".join(notes)
