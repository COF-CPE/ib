"""Metricas de rendimiento y comparacion contra benchmark."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def _clean(value: float) -> float | None:
    """None en vez de NaN/inf: el JSON del reporte tiene que ser valido."""
    return None if value is None or not np.isfinite(value) else round(float(value), 6)


def max_drawdown(equity: pd.Series) -> tuple[float, pd.Timestamp | None]:
    if equity.empty:
        return 0.0, None
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min() * 100.0), dd.idxmin()


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0 or equity.iloc[0] <= 0:
        return 0.0
    return float(((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) * 100.0)


def sharpe(equity: pd.Series, rf: float = 0.0) -> float:
    r = _returns(equity)
    if r.std() == 0 or r.empty:
        return 0.0
    excess = r - rf / TRADING_DAYS
    return float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS))


def sortino(equity: pd.Series, rf: float = 0.0) -> float:
    r = _returns(equity)
    downside = r[r < 0]
    # Sin barras negativas no hay ratio definido; 0.0 es mas honesto que NaN
    # y evita un JSON invalido en el reporte.
    if r.empty or len(downside) == 0 or downside.std() == 0:
        return 0.0
    return float((r.mean() - rf / TRADING_DAYS) / downside.std() * np.sqrt(TRADING_DAYS))


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0] - 1) * 100.0)


def trade_stats(trades: pd.DataFrame) -> dict:
    """Hit rate real y estadistica de operaciones cerradas."""
    if trades is None or trades.empty:
        return {
            "n_trades": 0, "hit_rate_pct": None, "avg_win_pct": None,
            "avg_loss_pct": None, "profit_factor": None, "avg_holding_days": None,
            "expectancy_pct": None, "stops_hit": 0,
        }
    closed = trades[trades["exit_date"].notna()]
    if closed.empty:
        return {"n_trades": 0, "hit_rate_pct": None, "avg_win_pct": None,
                "avg_loss_pct": None, "profit_factor": None,
                "avg_holding_days": None, "expectancy_pct": None, "stops_hit": 0}
    wins = closed[closed["pnl"] > 0]
    losses = closed[closed["pnl"] <= 0]
    gross_win = float(wins["pnl"].sum())
    gross_loss = float(-losses["pnl"].sum())
    return {
        "n_trades": int(len(closed)),
        "hit_rate_pct": round(len(wins) / len(closed) * 100.0, 2),
        "avg_win_pct": round(float(wins["return_pct"].mean()), 2) if len(wins) else None,
        "avg_loss_pct": round(float(losses["return_pct"].mean()), 2) if len(losses) else None,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "avg_holding_days": round(float(closed["holding_days"].mean()), 1),
        "expectancy_pct": round(float(closed["return_pct"].mean()), 3),
        "stops_hit": int((closed["exit_reason"] == "stop_loss").sum()),
    }


def beta_alpha(equity: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    """Beta y alpha anualizada (%) de la estrategia contra el benchmark."""
    r = _returns(equity)
    b = _returns(benchmark).reindex(r.index).dropna()
    r = r.reindex(b.index).dropna()
    if len(r) < 3 or b.var() == 0:
        return 0.0, 0.0
    beta = float(np.cov(r, b)[0, 1] / b.var())
    alpha_daily = float(r.mean() - beta * b.mean())
    return round(beta, 3), round(alpha_daily * TRADING_DAYS * 100.0, 2)


def summarize(result) -> dict:
    """Resumen completo de un BacktestResult."""
    eq = result.equity
    dd, dd_date = max_drawdown(eq)
    out = {
        "start": eq.index[0].date().isoformat(),
        "end": eq.index[-1].date().isoformat(),
        "initial_equity": round(float(eq.iloc[0]), 2),
        "final_equity": round(float(eq.iloc[-1]), 2),
        "total_return_pct": round(total_return(eq), 2),
        "cagr_pct": round(cagr(eq), 2),
        "sharpe": _clean(sharpe(eq)),
        "sortino": _clean(sortino(eq)),
        "max_drawdown_pct": round(dd, 2),
        "max_drawdown_date": dd_date.date().isoformat() if dd_date is not None else None,
        "avg_positions": round(float(result.daily["n_positions"].mean()), 2),
        "max_positions_used": int(result.daily["n_positions"].max()),
        "exposure_pct": round(
            float((result.daily["positions_value"] / result.daily["equity"]).mean() * 100), 2
        ),
        "universe_size": len(result.universe),
    }
    out.update(trade_stats(result.trades))
    if result.benchmark is not None and len(result.benchmark) > 1:
        bench = result.benchmark
        b_dd, _ = max_drawdown(bench)
        beta, alpha = beta_alpha(eq, bench)
        out.update(
            {
                "benchmark": result.config.backtest.benchmark,
                "benchmark_return_pct": round(total_return(bench), 2),
                "benchmark_cagr_pct": round(cagr(bench), 2),
                "benchmark_sharpe": round(sharpe(bench), 3),
                "benchmark_max_drawdown_pct": round(b_dd, 2),
                "excess_return_pct": round(total_return(eq) - total_return(bench), 2),
                "beta": beta,
                "alpha_annual_pct": alpha,
            }
        )
    return out


def per_ticker(result) -> pd.DataFrame:
    """Desglose por ticker: cuantas operaciones, hit rate y PnL."""
    t = result.trades
    if t is None or t.empty:
        return pd.DataFrame(columns=["ticker", "n_trades", "hit_rate_pct", "pnl", "avg_return_pct"])
    g = t.groupby("ticker")
    out = pd.DataFrame(
        {
            "n_trades": g.size(),
            "hit_rate_pct": g["pnl"].apply(lambda s: (s > 0).mean() * 100).round(2),
            "pnl": g["pnl"].sum().round(2),
            "avg_return_pct": g["return_pct"].mean().round(2),
        }
    ).reset_index()
    return out.sort_values("pnl", ascending=False)
