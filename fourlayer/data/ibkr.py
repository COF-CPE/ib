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


def parse_price_history(payload: dict | str, time_index=None) -> pd.DataFrame:
    """Convierte la respuesta de `get_price_history` en un OHLCV indexado.

    `time_index` permite reutilizar el calendario de otra serie ya ingerida
    (ver `time_ref` en `ingest_raw_dir`): todas las cotizadas de EE.UU.
    comparten las mismas sesiones, asi que guardar 83 veces el mismo vector de
    fechas no aporta nada y multiplica la superficie de error.
    """
    if isinstance(payload, str):
        payload = json.loads(payload)
    times = payload.get("time")
    if times is None:
        if time_index is None:
            raise ValueError("respuesta de IBKR sin campo 'time' y sin time_ref resuelto")
        times = list(time_index)

    n = len(times)
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
    idx = pd.to_datetime(times, utc=True, format="mixed").tz_convert(None).normalize()
    df = pd.DataFrame(data, index=pd.DatetimeIndex(idx, name="date")).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df.astype("float64")

    # IBKR consolida el cierre por separado del rango intradia, asi que en
    # algunas barras el cierre queda unos centimos (y en dias de vuelco
    # violento, algo mas) fuera del high/low. Se ensancha el rango en vez de
    # tocar el cierre: si no, el ATR y el stop se calculan sobre un rango que
    # no contiene al precio al que realmente se opero.
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)
    return df


def quality_report(df: pd.DataFrame) -> dict:
    """Chequeos basicos de una serie antes de meterla al motor."""
    gaps = df.index.to_series().diff().dt.days
    return {
        "bars": int(len(df)),
        "start": df.index[0].date().isoformat() if len(df) else None,
        "end": df.index[-1].date().isoformat() if len(df) else None,
        "nan_rows": int(df.isna().any(axis=1).sum()),
        "non_positive_close": int((df["close"] <= 0).sum()),
        "zero_volume_bars": int((df["volume"] == 0).sum()),
        "max_gap_days": int(gaps.max()) if len(df) > 1 else 0,
        "max_abs_daily_move_pct": round(float(df["close"].pct_change().abs().max() * 100), 2)
        if len(df) > 1 else 0.0,
    }


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
    payloads: dict[str, dict] = {}
    for p in sorted(raw.glob("*.json")):
        if p.stem.lower() in skip:
            continue
        try:
            payloads[p.stem.upper()] = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            failed[p.stem.upper()] = f"JSONDecodeError: {e}"

    # Primero los que traen su propio calendario: los `time_ref` dependen de ellos.
    order = sorted(payloads, key=lambda t: "time" not in payloads[t])
    calendars: dict[str, pd.DatetimeIndex] = {}
    for ticker in order:
        payload = payloads[ticker]
        try:
            ref = payload.get("time_ref")
            time_index = None
            if ref:
                ref = ref.upper()
                if ref not in calendars:
                    raise ValueError(f"time_ref '{ref}' no resuelto (falta o llego despues)")
                time_index = calendars[ref]
            df = parse_price_history(payload, time_index=time_index)
            store.save(ticker, df)
            ok[ticker] = len(df)
            if "time" in payload:
                calendars[ticker] = payload["time"]
        except Exception as e:  # noqa: BLE001 - se reporta, no se traga
            failed[ticker] = f"{type(e).__name__}: {e}"
    return {"ingested": ok, "failed": failed}
