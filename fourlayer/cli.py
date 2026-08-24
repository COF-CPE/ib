"""Interfaz de linea de comandos.

    python -m fourlayer.cli ingest
    python -m fourlayer.cli scan --top 20
    python -m fourlayer.cli backtest --alignment loose --start 2025-01-01
    python -m fourlayer.cli sweep
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

from .config import SystemConfig
from .data.ibkr import ingest_raw_dir
from .data.store import PriceStore, load_universe
from .firestore import backtest_record, dump, history_for
from .metrics import per_ticker
from .providers import ConstantMacro, EarningsCalendar, NeutralMacro, PanelFundamental
from .runner import build_signals, run, sweep


def _config_from_args(a) -> SystemConfig:
    cfg = SystemConfig()
    tech = replace(
        cfg.technical,
        alignment=a.alignment,
        aggregation=a.aggregation,
        rsi_mode=a.rsi_mode,
        require_both_windows=not a.any_window,
    )
    bt = replace(
        cfg.backtest,
        initial_cash=a.cash,
        max_positions=a.max_positions,
        max_weight=a.max_weight,
        sizing=a.sizing,
        benchmark=a.benchmark,
    )
    risk = replace(cfg.risk, trailing_stop=a.trailing_stop, stop_atr_multiple=a.stop_atr)
    return replace(cfg, technical=tech, backtest=bt, risk=risk, mode=a.mode)


def _universe(a, store: PriceStore) -> list[str]:
    if a.tickers:
        return [t.upper() for t in a.tickers]
    try:
        return load_universe(a.universe)
    except FileNotFoundError:
        return store.available()


def cmd_ingest(a) -> int:
    store = PriceStore(a.prices)
    report = ingest_raw_dir(a.raw, store)
    print(f"Ingeridos {len(report['ingested'])} tickers en {store.root}")
    for t, n in sorted(report["ingested"].items()):
        print(f"  {t:8s} {n:4d} barras")
    if report["failed"]:
        print(f"\nFallaron {len(report['failed'])}:", file=sys.stderr)
        for t, err in report["failed"].items():
            print(f"  {t}: {err}", file=sys.stderr)
    return 0


def cmd_scan(a) -> int:
    """Veredicto vigente en la ultima barra disponible de cada ticker."""
    store = PriceStore(a.prices)
    cfg = _config_from_args(a)
    signals, _prices, skipped = build_signals(
        _universe(a, store), store, cfg,
        macro=ConstantMacro(a.macro) if a.macro else NeutralMacro(),
        fundamental=PanelFundamental(a.fundamental_panel) if a.fundamental_panel else None,
        earnings=EarningsCalendar(a.earnings),
    )
    rows = []
    for ticker, s in signals.items():
        last = s.iloc[-1]
        rows.append(
            {
                "ticker": ticker,
                "date": last.name.date().isoformat(),
                "verdict": last["verdict"],
                "score": int(last["composite"]),
                "L1": int(last["layer1_macro"]), "L2": int(last["layer2_fundamental"]),
                "L3": int(last["layer3_long"]), "L4": int(last["layer4_short"]),
                "close": round(float(last["close"]), 2),
                "stop_2atr": round(float(last["stop_suggested"]), 2),
                "rsi14": round(float(last["rsi14"]), 1),
                "dd63": round(float(last["drawdown_63"]) * 100, 1),
                "earnings": bool(last["earnings_warning"]),
                "changed": bool(last["verdict_changed"]),
            }
        )
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    with pd.option_context("display.width", 200, "display.max_rows", None):
        print(df.head(a.top).to_string(index=False))
    if skipped:
        print(f"\nDescartados: {len(skipped)} -> {', '.join(sorted(skipped))}", file=sys.stderr)
    if a.out:
        records = [r for t, s in signals.items() for r in history_for(t, s, cfg.mode, limit=1)]
        print(f"\n-> {dump(records, a.out)}")
    return 0


def cmd_backtest(a) -> int:
    store = PriceStore(a.prices)
    cfg = _config_from_args(a)
    result, summary = run(
        _universe(a, store), store, cfg, start=a.start, end=a.end,
        macro=ConstantMacro(a.macro) if a.macro else NeutralMacro(),
        fundamental=PanelFundamental(a.fundamental_panel) if a.fundamental_panel else None,
        earnings=EarningsCalendar(a.earnings),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not result.trades.empty:
        print("\nPor ticker (top 15 por PnL):")
        print(per_ticker(result).head(15).to_string(index=False))
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    result.trades.to_csv(outdir / "trades.csv", index=False)
    result.equity.to_csv(outdir / "equity.csv")
    dump(backtest_record(summary, cfg, result.universe, a.notes), outdir / "backtest.json")
    print(f"\n-> {outdir}/trades.csv, equity.csv, backtest.json")
    return 0


DEFAULT_GRID = [
    {"technical.alignment": al, "technical.aggregation": ag, "technical.require_both_windows": rb}
    for al in ("strict", "loose")
    for ag in ("layers", "prototype")
    for rb in (True, False)
]


def cmd_sweep(a) -> int:
    store = PriceStore(a.prices)
    cfg = _config_from_args(a)
    df = sweep(_universe(a, store), store, cfg, DEFAULT_GRID, start=a.start, end=a.end)
    cols = [
        "technical.alignment", "technical.aggregation", "technical.require_both_windows",
        "n_trades", "total_return_pct", "benchmark_return_pct", "excess_return_pct",
        "hit_rate_pct", "max_drawdown_pct", "sharpe", "exposure_pct",
    ]
    with pd.option_context("display.width", 220, "display.max_rows", None):
        print(df[[c for c in cols if c in df.columns]].to_string(index=False))
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    df.to_csv(Path(a.outdir) / "sweep.csv", index=False)
    print(f"\n-> {a.outdir}/sweep.csv")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("fourlayer", description="Sistema de 4 capas: senales y backtest")
    p.add_argument("--prices", default="data/prices")
    p.add_argument("--universe", default="data/universe.json")
    p.add_argument("--tickers", nargs="*")
    p.add_argument("--earnings", default="data/earnings.csv")
    p.add_argument("--fundamental-panel", default=None)
    p.add_argument("--mode", choices=("scanner", "full"), default="scanner")
    p.add_argument("--alignment", choices=("strict", "loose"), default="strict")
    p.add_argument("--aggregation", choices=("layers", "prototype"), default="layers")
    p.add_argument("--rsi-mode", choices=("zones", "midline"), default="zones")
    p.add_argument("--any-window", action="store_true",
                   help="no exigir que las dos ventanas de la capa coincidan")
    p.add_argument("--macro", type=int, choices=(-1, 0, 1), default=0,
                   help="voto macro constante (solo con --mode full)")
    p.add_argument("--cash", type=float, default=100_000.0)
    p.add_argument("--max-positions", type=int, default=20)
    p.add_argument("--max-weight", type=float, default=0.10)
    p.add_argument("--sizing", choices=("equal_weight", "atr_risk"), default="equal_weight")
    p.add_argument("--stop-atr", type=float, default=2.0)
    p.add_argument("--trailing-stop", action="store_true")
    p.add_argument("--benchmark", default="SPY")
    p.add_argument("--start"); p.add_argument("--end")
    p.add_argument("--outdir", default="reports")
    p.add_argument("--notes", default="")

    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest", help="normaliza data/raw/*.json al cache de precios")
    s.add_argument("--raw", default="data/raw")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("scan", help="veredicto vigente por ticker")
    s.add_argument("--top", type=int, default=30)
    s.add_argument("--out", default=None, help="JSON con esquema Firestore")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("backtest", help="backtest walk-forward")
    s.set_defaults(func=cmd_backtest)

    s = sub.add_parser("sweep", help="barrido de sensibilidad de parametros")
    s.set_defaults(func=cmd_sweep)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
