"""Realized volatility estimators (close-to-close, Parkinson). Step 2.

Convention: every volatility in this project is annualised and expressed in
decimals (0.20 = 20%). Window ``w`` at date ``t`` uses the ``w`` returns ending
at ``t`` included, so the value is known at the close of ``t`` (no look-ahead).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def log_returns(prices: pd.Series) -> pd.Series:
    """Daily log-returns ``r_t = ln(P_t / P_{t-1})``. The first value is NaN."""
    if (prices <= 0).any():
        raise ValueError("Prices must be strictly positive to compute log-returns")
    return np.log(prices / prices.shift(1))


def close_to_close_vol(
    prices: pd.Series,
    window: int = 21,
    trading_days: int = 252,
    demean: bool = False,
) -> pd.Series:
    """Rolling annualised close-to-close volatility.

    ``sigma_t = sqrt(trading_days / w * sum_{i=t-w+1..t} r_i^2)``  (``demean=False``)

    By default returns are *not* demeaned: this is the variance-swap / VIX
    convention (the daily mean, ~0.03%, is negligible next to a ~1% daily move
    and is very noisy to estimate). ``demean=True`` gives the textbook rolling
    sample standard deviation (ddof=1) times ``sqrt(trading_days)``.

    Args:
        prices: Daily close prices indexed by date.
        window: Number of daily returns in the window (21 ~ one trading month).
        trading_days: Annualisation factor.
        demean: Subtract the rolling mean return.

    Returns:
        Series aligned on ``prices``; the first ``window`` values are NaN.
    """
    if window < 2:
        raise ValueError("window must be >= 2")
    r = log_returns(prices)
    if demean:
        daily = r.rolling(window, min_periods=window).std(ddof=1)
    else:
        daily = np.sqrt((r**2).rolling(window, min_periods=window).mean())
    return daily * np.sqrt(trading_days)


def parkinson_vol(
    high: pd.Series,
    low: pd.Series,
    window: int = 21,
    trading_days: int = 252,
) -> pd.Series:
    """Rolling annualised Parkinson (1980) volatility from daily high/low prices.

    ``sigma_t^2 = trading_days / (4 ln 2) * mean_{window}( ln(H_i / L_i)^2 )``

    The intraday range carries more information than a single close-to-close
    return, so this estimator is ~5x more efficient under a Brownian motion.
    It is biased downward in practice: no overnight gaps, discrete sampling.
    """
    if ((high <= 0) | (low <= 0)).any():
        raise ValueError("High and low prices must be strictly positive")
    if (high < low).any():
        raise ValueError("High must be >= low")
    hl2 = np.log(high / low) ** 2
    var_daily = hl2.rolling(window, min_periods=window).mean() / (4 * np.log(2))
    return np.sqrt(var_daily * trading_days)
