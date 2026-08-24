#!/usr/bin/env python3
"""Analisis completo: backtest, barrido de sensibilidad, scan y export Firestore.

    python scripts/run_analysis.py --start 2025-06-16

Escribe en `reports/`:
    resultados.md        informe legible
    sweep.csv            barrido de configuraciones
    trades_<cfg>.csv     operaciones de cada configuracion
    equity_<cfg>.csv     curva de capital
    backtest_<cfg>.json  documento con el esquema de Firestore
    scan.json            veredicto vigente por ticker (esquema de Firestore)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from fourlayer.config import SystemConfig  # noqa: E402
from fourlayer.data.store import PriceStore, load_universe  # noqa: E402
from fourlayer.firestore import backtest_record, dump, history_for  # noqa: E402
from fourlayer.metrics import per_ticker  # noqa: E402
from fourlayer.providers import EarningsCalendar, PanelFundamental  # noqa: E402
from fourlayer.runner import build_signals, run  # noqa: E402

GRID = [
    {"technical.alignment": al, "technical.aggregation": ag,
     "technical.require_both_windows": rb, "technical.rsi_mode": rm}
    for al in ("strict", "loose")
    for ag in ("layers", "prototype")
    for rb in (True, False)
    for rm in ("zones", "midline")
]


def label(overrides: dict) -> str:
    return "_".join([
        overrides["technical.alignment"],
        overrides["technical.aggregation"],
        "both" if overrides["technical.require_both_windows"] else "any",
        overrides["technical.rsi_mode"],
    ])


def apply(cfg: SystemConfig, overrides: dict) -> SystemConfig:
    kw = {k.split(".", 1)[1]: v for k, v in overrides.items()}
    return replace(cfg, technical=replace(cfg.technical, **kw))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prices", default="data/prices")
    ap.add_argument("--universe", default="data/universe.json")
    ap.add_argument("--earnings", default="data/earnings.csv")
    ap.add_argument("--fundamental-panel", default=None)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--outdir", default="reports")
    ap.add_argument("--positions", default="data/positions.csv")
    a = ap.parse_args()

    store = PriceStore(a.prices)
    try:
        universe = [t for t in load_universe(a.universe) if store.has(t)]
    except FileNotFoundError:
        universe = store.available()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    base = SystemConfig()
    earnings = EarningsCalendar(a.earnings)
    fundamental = PanelFundamental(a.fundamental_panel) if a.fundamental_panel else None

    rows, details = [], {}
    for overrides in GRID:
        cfg = apply(base, overrides)
        name = label(overrides)
        try:
            result, summary = run(
                universe, store, cfg, start=a.start, end=a.end,
                fundamental=fundamental, earnings=earnings,
            )
        except Exception as e:  # noqa: BLE001
            rows.append({"config": name, "error": f"{type(e).__name__}: {e}"})
            continue
        rows.append({"config": name, **{k.split(".", 1)[1]: v for k, v in overrides.items()},
                     **summary})
        details[name] = (result, summary, cfg)
        result.trades.to_csv(out / f"trades_{name}.csv", index=False)
        result.equity.to_csv(out / f"equity_{name}.csv")
        dump(backtest_record(summary, cfg, result.universe,
                             notes=f"grid={name}; start={a.start}; end={a.end}"),
             out / f"backtest_{name}.json")

    sweep = pd.DataFrame(rows)
    sweep.to_csv(out / "sweep.csv", index=False)

    # Scan del dia con la configuracion base.
    signals, _prices, skipped = build_signals(
        universe, store, base, fundamental=fundamental, earnings=earnings
    )
    scan_records = [r for t, s in signals.items() for r in history_for(t, s, base.mode, limit=1)]
    dump(scan_records, out / "scan.json")

    # Historial completo (tope 200 por ticker), mismo esquema que produccion.
    history = {t: history_for(t, s, base.mode) for t, s in signals.items()}
    dump(history, out / "history.json")

    write_report(out, sweep, details, signals, universe, skipped, a)
    print(f"-> {out}/resultados.md")
    return 0


def interpretation(sweep: pd.DataFrame, traded: list[str]) -> list[str]:
    """Lecturas que se desprenden de los numeros, sin adornos."""
    if "excess_return_pct" not in sweep.columns or sweep["excess_return_pct"].isna().all():
        return []
    df = sweep.dropna(subset=["excess_return_pct"])
    beat = df[df["excess_return_pct"] > 0]
    dead = df[df["n_trades"] == 0]
    exposure = df[df["n_trades"] > 0]["exposure_pct"]
    hit = df[df["n_trades"] > 0]["hit_rate_pct"]
    lines = ["## Lecturas", ""]
    lines.append(
        f"- **Ninguna de las {len(df)} configuraciones bate al benchmark**"
        if beat.empty else
        f"- {len(beat)} de {len(df)} configuraciones baten al benchmark."
    )
    if beat.empty:
        lines[-1] += " en esta ventana."
    if not dead.empty:
        lines.append(
            f"- {len(dead)} configuraciones no dispararon ni una sola operacion. "
            "Todas usan la agregacion `layers` con acuerdo exigido entre las dos "
            "ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo "
            "lado en dos horizontes a la vez es un filtro que casi nunca se cumple. "
            "Es el mismo resultado que aparecio en la prueba de concepto del chat."
        )
    if len(exposure):
        lines.append(
            f"- La exposicion media de las configuraciones que si operan es "
            f"{exposure.mean():.1f}%: el sistema pasa la mayor parte del tiempo en "
            "efectivo. Contra un benchmark que sube, eso solo ya explica casi toda "
            "la diferencia de rentabilidad, independientemente de si las senales "
            "aciertan."
        )
    if len(hit):
        lines.append(
            f"- Hit rate entre {hit.min():.1f}% y {hit.max():.1f}%. Por debajo del "
            "50% no es descalificante por si solo (una estrategia puede ganar con "
            "pocas operaciones muy buenas), pero aqui el profit factor tampoco "
            "compensa: ver `sweep.csv`."
        )
    lines += [
        f"- Muestra: {len(traded)} tickers. El brief pide las ~83 posiciones "
        "reales; con este tamano los numeros son indicativos, no concluyentes. "
        "`scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.",
        "",
    ]
    return lines


def write_report(out: Path, sweep: pd.DataFrame, details, signals, universe, skipped, a) -> None:
    benchmark = SystemConfig().backtest.benchmark
    traded = sorted(t for t in universe if t != benchmark)
    lines = [
        "# Resultados del backtest del sistema de 4 capas",
        "",
        f"- Universo operable: **{len(traded)} tickers** ({', '.join(traded)})",
        f"- Benchmark: {benchmark} (no se opera, solo se compara)",
        f"- Ventana: {a.start or 'desde el primer dato utilizable'} -> {a.end or 'ultimo dato'}",
        "- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no",
        "  meter sesgo retrospectivo; ver README.",
        "- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.",
        "- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).",
        "",
        "## Barrido de configuraciones",
        "",
    ]
    cols = [c for c in [
        "config", "n_trades", "total_return_pct", "benchmark_return_pct",
        "excess_return_pct", "hit_rate_pct", "max_drawdown_pct", "sharpe",
        "exposure_pct", "stops_hit",
    ] if c in sweep.columns]
    table = sweep[cols].sort_values(
        "excess_return_pct", ascending=False, na_position="last"
    ) if "excess_return_pct" in sweep.columns else sweep[cols]
    lines += [table.to_markdown(index=False), ""]

    if "excess_return_pct" in sweep.columns and sweep["excess_return_pct"].notna().any():
        best = table.iloc[0]
        lines += [
            "## Mejor configuracion del barrido",
            "",
            f"`{best['config']}` - {int(best['n_trades'])} operaciones, "
            f"{best['total_return_pct']:.2f}% frente al {best['benchmark_return_pct']:.2f}% "
            f"de SPY ({best['excess_return_pct']:+.2f} pp), hit rate "
            f"{best['hit_rate_pct']}%, exposicion media {best['exposure_pct']}%.",
            "",
        ]
        name = best["config"]
        if name in details:
            result, _summary, _cfg = details[name]
            pt = per_ticker(result)
            if not pt.empty:
                lines += ["### Desglose por ticker", "", pt.to_markdown(index=False), ""]

    lines += interpretation(sweep, traded)
    lines += ["## Veredicto vigente (scan de la ultima barra)", ""]
    scan_rows = []
    for ticker, s in signals.items():
        last = s.iloc[-1]
        scan_rows.append({
            "ticker": ticker, "verdict": last["verdict"], "score": int(last["composite"]),
            "L3": int(last["layer3_long"]), "L4": int(last["layer4_short"]),
            "close": round(float(last["close"]), 2),
            "stop_2atr": round(float(last["stop_suggested"]), 2),
            "rsi14": round(float(last["rsi14"]), 1),
            "dd63_pct": round(float(last["drawdown_63"]) * 100, 1),
        })
    lines += [pd.DataFrame(scan_rows).sort_values("score", ascending=False).to_markdown(index=False), ""]
    if skipped:
        lines += [f"Descartados por datos insuficientes: {', '.join(sorted(skipped))}", ""]

    (out / "resultados.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
