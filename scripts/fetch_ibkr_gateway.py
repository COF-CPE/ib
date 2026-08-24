#!/usr/bin/env python3
"""Descarga OHLCV de IBKR y llena el cache local.

Este script es la via automatica para completar el universo: habla directamente
con el Client Portal Gateway de IBKR, que corre en la maquina del usuario
(normalmente https://localhost:5000/v1/api) y expone el mismo endpoint que la
herramienta MCP `get_price_history`.

    # 1. arrancar el gateway y autenticarse en el navegador
    # 2. python scripts/fetch_ibkr_gateway.py --universe data/universe.json

Si no hay gateway (por ejemplo en un entorno sin red hacia el broker), el otro
camino es volcar la respuesta JSON de la herramienta MCP en
`data/raw/<TICKER>.json` y correr `python -m fourlayer.cli ingest`. Ambos
terminan en el mismo `PriceStore`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from fourlayer.data.ibkr import parse_price_history, quality_report  # noqa: E402
from fourlayer.data.store import PriceStore, load_universe  # noqa: E402

DEFAULT_BASE = "https://localhost:5000/v1/api"


def conid_map(positions_csv: str | Path) -> dict[str, int]:
    df = pd.read_csv(positions_csv)
    return {row.ticker: int(row.contract_id) for row in df.itertuples()}


def fetch_one(session, base: str, conid: int, period: str, bar: str) -> dict:
    r = session.get(
        f"{base}/iserver/marketdata/history",
        params={"conid": conid, "period": period, "bar": bar, "outsideRth": "false"},
        timeout=60,
    )
    r.raise_for_status()
    payload = r.json()
    # El gateway devuelve [{t, o, h, l, c, v}, ...]; se normaliza al formato
    # columnar que usa `parse_price_history`.
    if "data" in payload:
        rows = payload["data"]
        return {
            "time": [pd.Timestamp(row["t"], unit="ms", tz="UTC").isoformat() for row in rows],
            "open": [row["o"] for row in rows],
            "high": [row["h"] for row in rows],
            "low": [row["l"] for row in rows],
            "close": [row["c"] for row in rows],
            "volume": [row.get("v", 0) for row in rows],
        }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--positions", default="data/positions.csv")
    ap.add_argument("--universe", default="data/universe.json")
    ap.add_argument("--prices", default="data/prices")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--period", default="2y")
    ap.add_argument("--bar", default="1d")
    ap.add_argument("--sleep", type=float, default=0.4, help="pausa entre peticiones")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--insecure", action="store_true",
                    help="el gateway usa un certificado autofirmado")
    a = ap.parse_args()

    import requests

    session = requests.Session()
    if a.insecure:
        session.verify = False
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    conids = conid_map(a.positions)
    conids.setdefault("SPY", 756733)
    tickers = load_universe(a.universe)
    store = PriceStore(a.prices)
    raw = Path(a.raw)
    raw.mkdir(parents=True, exist_ok=True)

    ok, failed = 0, {}
    for ticker in tickers:
        if a.only_missing and store.has(ticker):
            continue
        conid = conids.get(ticker)
        if conid is None:
            failed[ticker] = "sin contract_id en positions.csv"
            continue
        try:
            payload = fetch_one(session, a.base, conid, a.period, a.bar)
            (raw / f"{ticker}.json").write_text(json.dumps(payload))
            df = parse_price_history(payload)
            store.save(ticker, df)
            print(f"{ticker:8s} {quality_report(df)}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            failed[ticker] = f"{type(e).__name__}: {e}"
        time.sleep(a.sleep)

    print(f"\nDescargados {ok} tickers.")
    if failed:
        print(f"Fallaron {len(failed)}:", file=sys.stderr)
        for t, err in failed.items():
            print(f"  {t}: {err}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
