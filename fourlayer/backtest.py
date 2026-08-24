"""Motor de backtest walk-forward y multi-ticker.

Reglas de oro:

1. La senal de la barra t se calcula solo con datos <= t (garantizado por
   `layers.compute_signals`, que solo usa indicadores causales).
2. La orden que nace de esa senal se ejecuta en t + `execution_lag` barras, a
   la apertura. Nunca al cierre de t: eso seria operar a un precio que en el
   momento de la decision todavia no existia.
3. El stop-loss se evalua contra el minimo/maximo real de la barra, con hueco
   de apertura respetado (si abre por debajo del stop, se sale a la apertura).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable

import numpy as np
import pandas as pd

from .config import SystemConfig


@dataclass
class Trade:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    entry_score: int
    stop_price: float
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    exit_score: int | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_date is None

    @property
    def pnl(self) -> float:
        if self.exit_price is None:
            return 0.0
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def return_pct(self) -> float:
        if self.exit_price is None or self.entry_price == 0:
            return 0.0
        return (self.exit_price / self.entry_price - 1.0) * 100.0

    @property
    def holding_days(self) -> int:
        if self.exit_date is None:
            return 0
        return int((self.exit_date - self.entry_date).days)

    def to_row(self) -> dict:
        d = asdict(self)
        d["entry_date"] = self.entry_date.date().isoformat()
        d["exit_date"] = self.exit_date.date().isoformat() if self.exit_date else None
        d["pnl"] = self.pnl
        d["return_pct"] = self.return_pct
        d["holding_days"] = self.holding_days
        return d


@dataclass
class Position:
    ticker: str
    shares: float
    entry_price: float
    stop_price: float
    trade: Trade


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    daily: pd.DataFrame
    benchmark: pd.Series | None
    config: SystemConfig
    universe: list[str]
    skipped: dict[str, str] = field(default_factory=dict)


def _apply_slippage(price: float, side: int, bps: float) -> float:
    """side=+1 compra (paga mas), side=-1 venta (recibe menos)."""
    return price * (1.0 + side * bps / 10_000.0)


def run_backtest(
    signals: dict[str, pd.DataFrame],
    prices: dict[str, pd.DataFrame],
    cfg: SystemConfig,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    benchmark_prices: pd.DataFrame | None = None,
) -> BacktestResult:
    bt = cfg.backtest
    entry_score = bt.entry_score if bt.entry_score is not None else cfg.verdict.weak
    exit_score = bt.exit_score if bt.exit_score is not None else -cfg.verdict.weak

    tickers = sorted(signals)
    if not tickers:
        raise ValueError("run_backtest: universo vacio")

    all_dates = sorted(set().union(*(signals[t].index for t in tickers)))
    dates = pd.DatetimeIndex(all_dates)
    if start is not None:
        dates = dates[dates >= pd.Timestamp(start)]
    if end is not None:
        dates = dates[dates <= pd.Timestamp(end)]
    if len(dates) == 0:
        raise ValueError("run_backtest: no quedan fechas tras aplicar start/end")

    cash = bt.initial_cash
    positions: dict[str, Position] = {}
    trades: list[Trade] = []
    pending: list[tuple[pd.Timestamp, str, int, int]] = []  # (fecha_ejec, ticker, side, score)
    rows = []

    date_pos = {d: i for i, d in enumerate(dates)}

    def exec_date(signal_date: pd.Timestamp) -> pd.Timestamp | None:
        i = date_pos.get(signal_date)
        if i is None:
            return None
        j = i + bt.execution_lag
        return dates[j] if j < len(dates) else None

    for d in dates:
        # ---------------- 1. Ordenes pendientes para hoy ----------------
        todays = [o for o in pending if o[0] == d]
        pending = [o for o in pending if o[0] != d]

        equity_open = cash + sum(
            p.shares * _bar(prices, p.ticker, d, "open", p.entry_price)
            for p in positions.values()
        )

        # Ventas primero: liberan efectivo y cupos.
        for _, ticker, side, score in todays:
            if side >= 0 or ticker not in positions:
                continue
            px = _bar(prices, ticker, d, bt.execution_price)
            if px is None:
                continue
            pos = positions.pop(ticker)
            fill = _apply_slippage(px, -1, bt.slippage_bps)
            proceeds = pos.shares * fill
            cash += proceeds - proceeds * bt.commission_bps / 10_000.0
            pos.trade.exit_date, pos.trade.exit_price = d, fill
            pos.trade.exit_reason, pos.trade.exit_score = "signal", score

        # Compras, priorizando el score mas alto.
        buys = sorted([o for o in todays if o[2] > 0], key=lambda o: -o[3])
        for _, ticker, _side, score in buys:
            if ticker in positions or len(positions) >= bt.max_positions:
                continue
            px = _bar(prices, ticker, d, bt.execution_price)
            if px is None or px <= 0:
                continue
            atr_val = _sig(signals, ticker, d, "atr")
            if atr_val is None or not np.isfinite(atr_val) or atr_val <= 0:
                continue
            fill = _apply_slippage(px, +1, bt.slippage_bps)
            notional = _target_notional(equity_open, fill, atr_val, cfg)
            notional = min(notional, cash / (1.0 + bt.commission_bps / 10_000.0))
            if notional <= 0:
                continue
            shares = notional / fill
            cost = shares * fill
            cash -= cost + cost * bt.commission_bps / 10_000.0
            stop = fill - cfg.risk.stop_atr_multiple * atr_val
            tr = Trade(ticker, d, fill, shares, int(score), stop)
            trades.append(tr)
            positions[ticker] = Position(ticker, shares, fill, stop, tr)

        # ---------------- 2. Stop-loss (2x ATR) ----------------
        for ticker in list(positions):
            pos = positions[ticker]
            if pos.trade.entry_date == d:
                continue  # el stop empieza a vigilar la barra siguiente
            low = _bar(prices, ticker, d, "low")
            if low is None or low > pos.stop_price:
                if cfg.risk.trailing_stop:
                    _trail(pos, signals, prices, ticker, d, cfg)
                continue
            open_px = _bar(prices, ticker, d, "open") or pos.stop_price
            # Si abre con hueco por debajo del stop, se sale a la apertura.
            fill = _apply_slippage(min(open_px, pos.stop_price), -1, bt.slippage_bps)
            positions.pop(ticker)
            proceeds = pos.shares * fill
            cash += proceeds - proceeds * bt.commission_bps / 10_000.0
            pos.trade.exit_date, pos.trade.exit_price = d, fill
            pos.trade.exit_reason = "stop_loss"

        # ---------------- 3. Senales de hoy -> ordenes futuras ----------------
        target = exec_date(d)
        if target is not None:
            for ticker in tickers:
                score = _sig(signals, ticker, d, "composite")
                if score is None:
                    continue
                score = int(score)
                held = ticker in positions
                if not held and score >= entry_score:
                    if cfg.risk.block_entry_on_earnings and _sig(
                        signals, ticker, d, "earnings_warning"
                    ):
                        continue
                    pending.append((target, ticker, +1, score))
                elif held and score <= exit_score:
                    pending.append((target, ticker, -1, score))

        # ---------------- 4. Marca a mercado ----------------
        mtm = 0.0
        for p in positions.values():
            px = _bar(prices, p.ticker, d, "close", p.entry_price)
            mtm += p.shares * px
        rows.append(
            {
                "date": d,
                "cash": cash,
                "positions_value": mtm,
                "equity": cash + mtm,
                "n_positions": len(positions),
            }
        )

    # Cierre forzoso al final del periodo, para que el hit rate mida trades reales.
    last = dates[-1]
    for ticker in list(positions):
        pos = positions.pop(ticker)
        px = _bar(prices, ticker, last, "close", pos.entry_price)
        pos.trade.exit_date, pos.trade.exit_price = last, px
        pos.trade.exit_reason = "end_of_period"

    daily = pd.DataFrame(rows).set_index("date")
    equity = daily["equity"].rename("equity")

    bench = None
    if benchmark_prices is not None and len(benchmark_prices):
        b = benchmark_prices["close"].reindex(dates).ffill().dropna()
        if len(b):
            bench = (b / b.iloc[0] * bt.initial_cash).rename(bt.benchmark)

    trades_df = pd.DataFrame([t.to_row() for t in trades])
    return BacktestResult(equity, trades_df, daily, bench, cfg, tickers)


def _trail(pos: Position, signals, prices, ticker, d, cfg) -> None:
    close = _bar(prices, ticker, d, "close")
    atr_val = _sig(signals, ticker, d, "atr")
    if close is None or atr_val is None or not np.isfinite(atr_val):
        return
    new_stop = close - cfg.risk.stop_atr_multiple * atr_val
    if new_stop > pos.stop_price:
        pos.stop_price = new_stop
        pos.trade.stop_price = new_stop


def _target_notional(equity: float, price: float, atr_val: float, cfg: SystemConfig) -> float:
    """Notional objetivo de una posicion nueva, acotado por `max_weight`."""
    bt = cfg.backtest
    cap = equity * bt.max_weight
    if bt.sizing == "equal_weight":
        return min(cap, equity / max(bt.max_positions, 1))
    if bt.sizing == "atr_risk":
        # El riesgo por accion es la distancia al stop (2x ATR). Se dimensiona
        # para que tocar el stop cueste `risk_per_trade` del equity.
        risk_per_share = cfg.risk.stop_atr_multiple * atr_val
        if risk_per_share <= 0:
            return 0.0
        shares = equity * bt.risk_per_trade / risk_per_share
        return min(cap, shares * price)
    raise ValueError(f"sizing desconocido: {bt.sizing}")


def _bar(prices: dict[str, pd.DataFrame], ticker: str, d, col: str, default=None):
    df = prices.get(ticker)
    if df is None:
        return default
    try:
        v = df.at[d, col]
    except KeyError:
        return default
    if pd.isna(v):
        return default
    return float(v)


def _sig(signals: dict[str, pd.DataFrame], ticker: str, d, col: str):
    df = signals.get(ticker)
    if df is None or col not in df.columns:
        return None
    try:
        v = df.at[d, col]
    except KeyError:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if pd.isna(v):
        return None
    return float(v)
