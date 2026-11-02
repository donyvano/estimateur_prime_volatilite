"""Step 2: realized volatility estimators."""

import numpy as np
import pandas as pd
import pytest

from vrp.realized_vol import close_to_close_vol, log_returns, parkinson_vol


def test_log_returns_simple_case() -> None:
    p = pd.Series([100.0, 110.0, 99.0])
    r = log_returns(p)
    assert np.isnan(r.iloc[0])
    assert r.iloc[1] == pytest.approx(np.log(1.1))


def test_constant_absolute_return_gives_known_vol() -> None:
    # Returns of +/-1% every day: zero-mean RV is exactly 1% * sqrt(252).
    r = np.tile([0.01, -0.01], 30)
    p = pd.Series(100 * np.exp(np.concatenate([[0], np.cumsum(r)])))
    vol = close_to_close_vol(p, window=21)
    assert vol.dropna().to_numpy() == pytest.approx(0.01 * np.sqrt(252))


def test_first_window_is_nan(prices: pd.Series) -> None:
    vol = close_to_close_vol(prices, window=21)
    assert vol.iloc[:21].isna().all()
    assert vol.iloc[21:].notna().all()


def test_recovers_simulated_vol(prices: pd.Series) -> None:
    # Fixture simulates 20% vol: the full-sample average must be close.
    vol = close_to_close_vol(prices, window=21)
    assert vol.mean() == pytest.approx(0.20, abs=0.02)


def test_demean_matches_pandas_std(prices: pd.Series) -> None:
    vol = close_to_close_vol(prices, window=21, demean=True)
    expected = log_returns(prices).rolling(21).std() * np.sqrt(252)
    pd.testing.assert_series_equal(vol, expected)


def test_rolling_vol_uses_only_past(prices: pd.Series) -> None:
    """Look-ahead check: changing prices after t must not change vol at t."""
    t = 500
    vol = close_to_close_vol(prices, 21)
    shocked = prices.copy()
    shocked.iloc[t + 1 :] *= 1.5
    assert close_to_close_vol(shocked, 21).iloc[: t + 1].equals(vol.iloc[: t + 1])


def test_parkinson_known_value() -> None:
    # Constant range H/L = e^0.02: sigma^2 = 252 * 0.02^2 / (4 ln 2).
    low = pd.Series(np.full(30, 100.0))
    high = low * np.exp(0.02)
    vol = parkinson_vol(high, low, window=21).dropna()
    assert vol.to_numpy() == pytest.approx(np.sqrt(252 * 0.02**2 / (4 * np.log(2))))


def test_parkinson_rejects_high_below_low() -> None:
    with pytest.raises(ValueError):
        parkinson_vol(pd.Series([1.0, 2.0]), pd.Series([1.5, 1.0]), window=2)


def test_window_must_be_at_least_two(prices: pd.Series) -> None:
    with pytest.raises(ValueError):
        close_to_close_vol(prices, window=1)
