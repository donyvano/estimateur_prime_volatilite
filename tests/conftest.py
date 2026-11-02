"""Shared synthetic data: tests never touch the network."""

import numpy as np
import pandas as pd
import pytest

from vrp.config import load_config


@pytest.fixture
def cfg() -> dict:
    return load_config()


@pytest.fixture
def prices() -> pd.Series:
    """~4 years of GBM prices on business days, 20% vol, fixed seed."""
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2015-01-01", periods=1000)
    r = rng.normal(0.0003, 0.2 / np.sqrt(252), len(idx))
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx, name="close")


@pytest.fixture
def market(prices: pd.Series) -> pd.DataFrame:
    """Synthetic market frame shaped like ``load_market_data`` output."""
    rng = np.random.default_rng(1)
    spread = np.abs(rng.normal(0, 0.006, len(prices)))
    return pd.DataFrame(
        {
            "spx_open": prices.shift(1).fillna(prices.iloc[0]),
            "spx_high": prices * (1 + spread),
            "spx_low": prices * (1 - spread),
            "spx_close": prices,
            "vix": 22 + rng.normal(0, 2, len(prices)),
            "rate": 0.02,
        },
        index=prices.index,
    )
