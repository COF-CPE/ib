"""Sistema de trading de 4 capas: motor de senales y backtest walk-forward."""
from .config import (
    BacktestConfig, RiskConfig, SystemConfig, TechnicalConfig, VerdictConfig, Window,
)
from .layers import SignalContext, compute_signals, technical_layers, verdicts
from .backtest import run_backtest, BacktestResult
from .runner import build_signals, run, sweep
from .data.store import PriceStore

__version__ = "1.0.0"
__all__ = [
    "SystemConfig", "TechnicalConfig", "VerdictConfig", "RiskConfig", "BacktestConfig",
    "Window", "SignalContext", "compute_signals", "technical_layers", "verdicts",
    "run_backtest", "BacktestResult", "build_signals", "run", "sweep", "PriceStore",
]
