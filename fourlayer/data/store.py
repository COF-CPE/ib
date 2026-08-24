"""Cache local de precios OHLCV en CSV, una serie por ticker."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

COLUMNS = ["open", "high", "low", "close", "volume"]


class PriceStore:
    def __init__(self, root: str | Path = "data/prices"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, ticker: str) -> Path:
        return self.root / f"{ticker.upper()}.csv"

    def has(self, ticker: str) -> bool:
        return self.path(ticker).exists()

    def save(self, ticker: str, df: pd.DataFrame) -> Path:
        missing = [c for c in COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{ticker}: faltan columnas {missing}")
        out = df[COLUMNS].copy()
        out.index.name = "date"
        p = self.path(ticker)
        out.to_csv(p, float_format="%.6f")
        return p

    def load(self, ticker: str) -> pd.DataFrame:
        p = self.path(ticker)
        if not p.exists():
            raise FileNotFoundError(f"sin datos cacheados para {ticker} ({p})")
        df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
        return df[~df.index.duplicated(keep="last")]

    def load_many(self, tickers) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
        """Devuelve (cargados, motivos_de_descarte)."""
        ok, skipped = {}, {}
        for t in tickers:
            try:
                df = self.load(t)
            except FileNotFoundError as e:
                skipped[t] = str(e)
                continue
            if df.empty:
                skipped[t] = "serie vacia"
                continue
            ok[t] = df
        return ok, skipped

    def available(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.csv"))


def save_universe(tickers, path: str | Path = "data/universe.json", meta: dict | None = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"tickers": sorted(set(tickers)), "meta": meta or {}}, indent=2))
    return p


def load_universe(path: str | Path = "data/universe.json") -> list[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"no existe el universo {p}")
    return list(json.loads(p.read_text())["tickers"])
