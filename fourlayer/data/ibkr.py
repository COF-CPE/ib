"""Conector IBKR.

IBKR llega por MCP (`get_price_history`, `get_account_positions`), que se
invoca desde el agente, no desde este proceso. El flujo es:

    1. El agente llama a la herramienta MCP.
    2. Vuelca la respuesta JSON tal cual en `data/raw/<TICKER>.json`
       (o las posiciones en `data/raw/positions.json`).
    3. `ingest_raw_dir()` las normaliza al cache de `PriceStore`.

Asi el motor de backtest es reproducible offline y no depende de tener sesion
abierta con el broker.

`get_price_history` devuelve las series en formato columnar:
    {"time": [...], "open": [...], "high": [...], "low": [...],
     "close": [...], "volume": [...]}
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_COLS = ("open", "high", "low", "close", "volume")


def parse_price_history(payload: dict | str) -> pd.DataFrame:
    """Convierte la respuesta de `get_price_history` en un OHLCV indexado."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if "time" not in payload:
        raise ValueError("respuesta de IBKR sin campo 'time'")

    n = len(payload["time"])
    data = {}
    for c in _COLS:
        col = payload.get(c)
        if col is None:
            raise ValueError(f"respuesta de IBKR sin campo '{c}'")
        if len(col) != n:
            raise ValueError(f"campo '{c}' con {len(col)} valores, se esperaban {n}")
        data[c] = col

    # Las marcas de tiempo vienen en UTC a la hora de apertura del mercado.
    # Para barras diarias interesa la fecha, no la hora.
    idx = pd.to_datetime(payload["time"], utc=True, format="mixed").tz_convert(None).normalize()
    df = pd.DataFrame(data, index=pd.DatetimeIndex(idx, name="date")).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df.astype("float64")


def parse_positions(payload: dict | str) -> pd.DataFrame:
    """Posiciones reales de la cartera IBKR (`get_account_positions`)."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    rows = payload.get("positions", payload if isinstance(payload, list) else [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # "NTDOY @PINK" -> "NTDOY"
    df["ticker"] = df["contract_description"].str.split("@").str[0].str.strip()
    keep = [
        "ticker", "contract_id", "position", "market_price", "market_value",
        "average_price", "unrealized_pnl", "currency", "asset_class",
    ]
    return df[[c for c in keep if c in df.columns]].sort_values("ticker").reset_index(drop=True)


def ingest_raw_dir(raw_dir: str | Path, store, skip: tuple[str, ...] = ("positions",)) -> dict:
    """Normaliza todos los volcados JSON de `raw_dir` al `PriceStore`.

    Devuelve {ticker: n_barras} para los que se ingirieron y lanza al final un
    resumen de los que fallaron.
    """
    raw = Path(raw_dir)
    ok, failed = {}, {}
    for p in sorted(raw.glob("*.json")):
        ticker = p.stem.upper()
        if p.stem.lower() in skip:
            continue
        try:
            df = parse_price_history(json.loads(p.read_text()))
            store.save(ticker, df)
            ok[ticker] = len(df)
        except Exception as e:  # noqa: BLE001 - se reporta, no se traga
            failed[ticker] = f"{type(e).__name__}: {e}"
    return {"ingested": ok, "failed": failed}
