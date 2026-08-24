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
            df, note = cut_at_scale_break(df)
            if note:
                skipped[t] = note
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


def scale_break(df: pd.DataFrame, min_side: int = 5):
    """Fecha en la que la serie deja de estar retroajustada, si la hay.

    IBKR devuelve el historico retroajustado por acciones corporativas y las
    barras mas recientes sin ajustar. En la frontera el volumen pasa de tener
    decimales a ser entero y el precio da un salto que no corresponde a ningun
    movimiento de mercado: SPGI, por ejemplo, "sube" un 7.7% en un dia con
    volumen plano. Ese retorno es del proveedor, no del activo, y operarlo
    seria inventarse una ganancia.
    """
    v = df["volume"]
    frac = (v % 1) != 0
    if not frac.any() or frac.all():
        return None
    pos = df.index.get_loc(frac[frac].index[-1])
    before, after = frac.iloc[: pos + 1], frac.iloc[pos + 1 :]
    if len(before) < min_side or len(after) < min_side:
        return None
    # El tramo ajustado tiene decimales casi siempre; un decimal suelto en una
    # serie por lo demas entera es ruido de redondeo, no una frontera.
    if before.mean() < 0.8:
        return None
    return df.index[pos + 1]


def cut_at_scale_break(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Se queda con el tramo mas largo a un lado de la frontera de ajuste."""
    date = scale_break(df)
    if date is None:
        return df, None
    before = df.loc[df.index < date]
    after = df.loc[df.index >= date]
    keep, drop, side = (
        (before, after, "posterior") if len(before) >= len(after) else (after, before, "anterior")
    )
    jump = df["close"].pct_change().loc[date]
    return keep, (
        f"frontera de retroajuste el {date.date()} (salto de {jump:+.1%} sin volumen "
        f"que lo respalde); se descarta el tramo {side} de {len(drop)} barras"
    )
