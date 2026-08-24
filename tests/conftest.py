import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_ohlcv(n=520, seed=7, drift=0.0004, vol=0.015, start="2024-01-02"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n, name="date")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)
    intraday = np.abs(rng.normal(0.008, 0.004, n))
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close * (1 + intraday),
            "low": close * (1 - intraday),
            "close": close,
            "volume": rng.integers(1_000_000, 8_000_000, n).astype(float),
        },
        index=idx,
    )


@pytest.fixture
def ohlcv():
    return make_ohlcv()
