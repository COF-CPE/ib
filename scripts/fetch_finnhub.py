#!/usr/bin/env python3
"""Construye desde Finnhub el calendario de earnings y el panel fundamental.

    export FINNHUB_API_KEY=...
    python scripts/fetch_finnhub.py --from 2024-01-01 --to 2026-12-31

Salidas:
  data/earnings.csv           ticker,date          -> advertencia de <=14 dias
  data/fundamental_panel.csv  date,ticker,score,structural_issue,detail

SOBRE EL SESGO RETROSPECTIVO
----------------------------
Finnhub sirve los ratios *actuales*, no una foto de como se veian en 2024. Por
eso el panel que genera este script tiene dos modos:

  --pit  (recomendado) usa `stock/financials-reported` y fecha cada lectura con
         el `filedDate` del reporte: la fila solo entra en vigor el dia en que
         el mercado pudo verla. Es point-in-time de verdad.

  sin --pit  escribe una unica fila por ticker con fecha `--as-of`. Sirve para
         el scan de hoy, NO para backtest historico: aplicaria el fundamental
         de hoy a fechas pasadas.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from fourlayer.data.finnhub import FinnhubClient, score_fundamentals  # noqa: E402
from fourlayer.data.store import load_universe  # noqa: E402


def build_earnings(client: FinnhubClient, tickers, frm: str, to: str) -> pd.DataFrame:
    rows = []
    for t in tickers:
        for d in client.earnings_dates(t, frm, to):
            rows.append({"ticker": t, "date": d.date().isoformat()})
        if not client.enabled:
            break
    return pd.DataFrame(rows, columns=["ticker", "date"])


def build_panel_current(client: FinnhubClient, tickers, as_of: str) -> pd.DataFrame:
    rows = []
    for t in tickers:
        metric = client.basic_financials(t)
        if not metric:
            continue
        score, structural, detail = score_fundamentals(metric)
        rows.append({
            "date": as_of, "ticker": t, "score": score,
            "structural_issue": structural, "detail": detail,
        })
    return pd.DataFrame(rows, columns=["date", "ticker", "score", "structural_issue", "detail"])


def build_panel_pit(client: FinnhubClient, tickers) -> pd.DataFrame:
    """Panel point-in-time: una fila por reporte, fechada en su `filedDate`."""
    rows = []
    for t in tickers:
        payload = client.reported_financials(t)
        if not payload:
            continue
        for report in payload.get("data", []):
            filed = report.get("filedDate") or report.get("acceptedDate")
            if not filed:
                continue
            ic = {i.get("concept"): i.get("value") for i in report.get("report", {}).get("ic", [])}
            bs = {i.get("concept"): i.get("value") for i in report.get("report", {}).get("bs", [])}
            revenue = ic.get("Revenues") or ic.get("RevenueFromContractWithCustomerExcludingAssessedTax")
            op_income = ic.get("OperatingIncomeLoss")
            equity = bs.get("StockholdersEquity")
            liabilities = bs.get("Liabilities")

            pos = neg = 0
            notes = []
            if revenue and op_income is not None:
                margin = op_income / revenue * 100
                notes.append(f"opm={margin:.1f}")
                pos, neg = (pos + 1, neg) if margin > 10 else ((pos, neg + 1) if margin < 0 else (pos, neg))
            de = None
            if equity and liabilities is not None and equity != 0:
                de = liabilities / equity * 100
                notes.append(f"d/e={de:.0f}")
                pos, neg = (pos + 1, neg) if de < 100 else ((pos, neg + 1) if de > 250 else (pos, neg))

            structural = bool(
                (equity is not None and equity < 0)
                or (de is not None and de > 400)
                or (revenue and op_income is not None and op_income / revenue * 100 < -10)
            )
            rows.append({
                "date": pd.Timestamp(filed).date().isoformat(), "ticker": t,
                "score": 1 if pos - neg >= 1 else (-1 if neg - pos >= 1 else 0),
                "structural_issue": structural, "detail": ",".join(notes),
            })
    df = pd.DataFrame(rows, columns=["date", "ticker", "score", "structural_issue", "detail"])
    return df.sort_values(["ticker", "date"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", default="data/universe.json")
    ap.add_argument("--from", dest="frm", default="2024-01-01")
    ap.add_argument("--to", default="2026-12-31")
    ap.add_argument("--as-of", default=pd.Timestamp.today().date().isoformat())
    ap.add_argument("--pit", action="store_true", help="panel point-in-time por filedDate")
    ap.add_argument("--earnings-out", default="data/earnings.csv")
    ap.add_argument("--panel-out", default="data/fundamental_panel.csv")
    a = ap.parse_args()

    client = FinnhubClient()
    if not client.enabled:
        print("FINNHUB_API_KEY no definida: no hay nada que descargar.", file=sys.stderr)
        print("El motor corre igual en modo solo-tecnico (proveedores neutrales).",
              file=sys.stderr)
        return 1

    tickers = load_universe(a.universe)
    earnings = build_earnings(client, tickers, a.frm, a.to)
    earnings.to_csv(a.earnings_out, index=False)
    print(f"{len(earnings)} fechas de earnings -> {a.earnings_out}")

    panel = build_panel_pit(client, tickers) if a.pit else build_panel_current(client, tickers, a.as_of)
    panel.to_csv(a.panel_out, index=False)
    print(f"{len(panel)} lecturas fundamentales -> {a.panel_out}")
    if not a.pit:
        print("AVISO: panel no point-in-time. Valido para `scan`, NO para backtest.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
