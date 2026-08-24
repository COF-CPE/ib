"""Capas 1 (macro) y 2 (fundamental): proveedores intercambiables.

Estas dos capas no son reproducibles matematicamente desde el precio, asi que
se modelan como proveedores que, dado un ticker y una fecha, devuelven un voto
en {-1, 0, +1}.

SESGO RETROSPECTIVO (punto 3 del brief)
---------------------------------------
Usar un LLM de hoy para "adivinar" el macro de una fecha pasada mete
look-ahead por la puerta de atras: el modelo ya sabe como termino esa historia.
Por eso el proveedor por defecto para backtest es `NeutralMacro` (voto 0
siempre), que deja el score compuesto en el rango [-2, +2] de las capas
tecnicas y hace que el backtest sea, literalmente, un backtest del Scanner.
Cualquier otra opcion tiene que ser una decision explicita de quien lanza el
backtest, y queda registrada en el reporte.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Protocol

import pandas as pd


@dataclass(frozen=True)
class FundamentalReading:
    score: int                     # -1, 0, +1
    structural_issue: bool = False
    detail: str = ""


class MacroProvider(Protocol):
    name: str

    def score_on(self, as_of: pd.Timestamp) -> int: ...


class FundamentalProvider(Protocol):
    name: str

    def reading_on(self, ticker: str, as_of: pd.Timestamp) -> FundamentalReading: ...


# --------------------------------------------------------------------------- #
# Macro
# --------------------------------------------------------------------------- #
class NeutralMacro:
    """Voto 0 siempre. Es el default honesto para backtest historico."""

    name = "neutral"
    look_ahead_safe = True

    def score_on(self, as_of: pd.Timestamp) -> int:  # noqa: ARG002
        return 0


class ConstantMacro:
    """Voto fijo. Util para el analisis de sensibilidad ('y si el macro
    hubiera estado en +1 todo el periodo?')."""

    look_ahead_safe = True

    def __init__(self, score: int):
        if score not in (-1, 0, 1):
            raise ValueError("ConstantMacro: score debe ser -1, 0 o +1")
        self.score = score
        self.name = f"constant({score:+d})"

    def score_on(self, as_of: pd.Timestamp) -> int:  # noqa: ARG002
        return self.score


class SeriesMacro:
    """Serie point-in-time provista por el usuario (CSV `date,score`).

    Es la unica forma limpia de meter macro real en un backtest: la lectura de
    cada fecha tiene que haber sido escrita en esa fecha, no reconstruida hoy.
    Se aplica forward-fill: la lectura vigente es la ultima <= as_of.
    """

    look_ahead_safe = True

    def __init__(self, path: str | Path):
        df = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
        if not {"date", "score"} <= set(df.columns):
            raise ValueError("SeriesMacro: el CSV necesita columnas date,score")
        self._s = df.set_index("date")["score"].astype(int).clip(-1, 1)
        self.name = f"series({Path(path).name})"

    def score_on(self, as_of: pd.Timestamp) -> int:
        prev = self._s.loc[:as_of]
        return int(prev.iloc[-1]) if len(prev) else 0


class CallbackMacro:
    """Envuelve una funcion evaluada en tiempo real (produccion, no backtest).

    Aqui es donde encaja la evaluacion por IA con cache de 24h del sistema en
    produccion. Marcado como NO seguro para backtest.
    """

    look_ahead_safe = False
    name = "callback"

    def __init__(self, fn: Callable[[pd.Timestamp], int], cache_hours: float = 24.0):
        self._fn = fn
        self._cache_seconds = cache_hours * 3600
        self._cached: tuple[float, int] | None = None

    def score_on(self, as_of: pd.Timestamp) -> int:
        now = time.time()
        if self._cached and now - self._cached[0] < self._cache_seconds:
            return self._cached[1]
        value = int(self._fn(as_of))
        self._cached = (now, value)
        return value


# --------------------------------------------------------------------------- #
# Fundamental
# --------------------------------------------------------------------------- #
_NEUTRAL = FundamentalReading(0, False, "sin datos")


class NeutralFundamental:
    """Voto 0 y sin structural_issue. Default honesto para backtest."""

    name = "neutral"
    look_ahead_safe = True

    def reading_on(self, ticker: str, as_of: pd.Timestamp) -> FundamentalReading:  # noqa: ARG002
        return _NEUTRAL


class StaticFundamental:
    """Lecturas fijas por ticker. Para tests y para escenarios 'que pasaria si'."""

    look_ahead_safe = True
    name = "static"

    def __init__(self, readings: dict[str, FundamentalReading]):
        self._r = readings

    def reading_on(self, ticker: str, as_of: pd.Timestamp) -> FundamentalReading:  # noqa: ARG002
        return self._r.get(ticker, _NEUTRAL)


class PanelFundamental:
    """Panel point-in-time desde CSV `date,ticker,score,structural_issue`.

    Cada fila es la lectura vigente desde esa fecha (forward fill por ticker).
    Es el formato que produce `scripts/build_fundamental_panel.py` a partir de
    Finnhub, usando la fecha de publicacion del reporte como fecha de la fila
    (no la del cierre del trimestre) para no adelantar informacion.
    """

    look_ahead_safe = True

    def __init__(self, path: str | Path):
        df = pd.read_csv(path, parse_dates=["date"])
        needed = {"date", "ticker", "score"}
        if not needed <= set(df.columns):
            raise ValueError(f"PanelFundamental: faltan columnas {needed - set(df.columns)}")
        if "structural_issue" not in df.columns:
            df["structural_issue"] = False
        df["structural_issue"] = df["structural_issue"].fillna(False).astype(bool)
        self._by_ticker = {
            t: g.sort_values("date").set_index("date") for t, g in df.groupby("ticker")
        }
        self.name = f"panel({Path(path).name})"

    def reading_on(self, ticker: str, as_of: pd.Timestamp) -> FundamentalReading:
        g = self._by_ticker.get(ticker)
        if g is None:
            return _NEUTRAL
        prev = g.loc[:as_of]
        if not len(prev):
            return _NEUTRAL
        row = prev.iloc[-1]
        return FundamentalReading(
            score=int(max(-1, min(1, row["score"]))),
            structural_issue=bool(row["structural_issue"]),
            detail=str(row.get("detail", "")),
        )


# --------------------------------------------------------------------------- #
# Calendario de earnings
# --------------------------------------------------------------------------- #
class EarningsCalendar:
    """Fechas de reporte por ticker, para la advertencia de <=14 dias.

    Se carga desde CSV `ticker,date` (lo produce `scripts/fetch_finnhub.py`).
    Sin fichero, `days_to_earnings` devuelve None y la advertencia no se emite.
    """

    def __init__(self, path: str | Path | None = None):
        self._dates: dict[str, list[pd.Timestamp]] = {}
        if path and Path(path).exists():
            df = pd.read_csv(path, parse_dates=["date"])
            for t, g in df.groupby("ticker"):
                self._dates[t] = sorted(g["date"].tolist())

    def days_to_earnings(self, ticker: str, as_of: pd.Timestamp) -> int | None:
        dates = self._dates.get(ticker)
        if not dates:
            return None
        future = [d for d in dates if d >= as_of]
        return int((future[0] - as_of).days) if future else None

    def warning(self, ticker: str, as_of: pd.Timestamp, within_days: int) -> bool:
        d = self.days_to_earnings(ticker, as_of)
        return d is not None and d <= within_days
