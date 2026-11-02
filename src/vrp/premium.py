"""Volatility risk premium: look-ahead-free alignment and statistics. Step 5.

Timeline at the close of day t:

    ... t-20 ... t | t+1 ... t+21
    ---- known ----|---- future ----
    trailing RV    |  forward RV  (realised over the life of the VIX quoted at t)
    VIX_t          |

    VRP_t = VIX_t - forward RV_t

``VRP_t`` is only *known* at t+21: it is an ex-post quantity used to measure the
premium and as a forecasting target, never as a feature at date t.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from vrp.realized_vol import close_to_close_vol, parkinson_vol


def forward_realized_vol(
    prices: pd.Series, horizon: int = 21, trading_days: int = 252
) -> pd.Series:
    """Realized volatility over the next ``horizon`` returns ``r_{t+1}, ..., r_{t+h}``.

    The trailing vol at ``t + h`` uses exactly the returns ``r_{t+1} .. r_{t+h}``,
    so the forward vol at ``t`` is the trailing vol shifted back by ``h`` days.
    The last ``h`` values are NaN: their future has not happened yet.
    """
    trailing = close_to_close_vol(prices, window=horizon, trading_days=trading_days)
    return trailing.shift(-horizon)


def build_vrp_frame(market: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Daily frame with implied, trailing and forward realized volatility and the VRP.

    Columns (decimals):
        implied   VIX / 100, known at t
        rv        trailing close-to-close RV over t-20..t, known at t
        rv_park   trailing Parkinson RV, known at t
        rv_fwd    forward RV over t+1..t+21, known at t+21
        vrp       implied - rv_fwd (vol points)
        vrp_var   implied^2 - rv_fwd^2 (variance points, the variance-swap P&L)
    """
    h = cfg["premium"]["horizon"]
    n = cfg["volatility"]["trading_days"]
    w = cfg["volatility"]["window"]
    close = market["spx_close"]
    df = pd.DataFrame(index=market.index)
    df["spx_close"] = close
    df["implied"] = market["vix"] / 100.0
    df["rv"] = close_to_close_vol(close, window=w, trading_days=n)
    df["rv_park"] = parkinson_vol(market["spx_high"], market["spx_low"], window=w, trading_days=n)
    df["rv_fwd"] = forward_realized_vol(close, horizon=h, trading_days=n)
    df["vrp"] = df["implied"] - df["rv_fwd"]
    df["vrp_var"] = df["implied"] ** 2 - df["rv_fwd"] ** 2
    return df


def vrp_summary(vrp: pd.DataFrame) -> dict[str, float | str | int]:
    """Headline statistics of the premium over the full sample (vol points, in %)."""
    d = vrp.dropna(subset=["vrp"])
    worst = d["vrp"].idxmin()
    return {
        "start": str(d.index[0].date()),
        "end": str(d.index[-1].date()),
        "n_days": int(len(d)),
        "mean_implied": 100 * float(d["implied"].mean()),
        "mean_realized": 100 * float(d["rv_fwd"].mean()),
        "mean_vrp": 100 * float(d["vrp"].mean()),
        "median_vrp": 100 * float(d["vrp"].median()),
        "std_vrp": 100 * float(d["vrp"].std()),
        "pct_positive": 100 * float((d["vrp"] > 0).mean()),
        "mean_vrp_var": 1e4 * float(d["vrp_var"].mean()),
        "worst_vrp": 100 * float(d.loc[worst, "vrp"]),
        "worst_date": str(worst.date()),
        "corr_implied_fwd": float(d["implied"].corr(d["rv_fwd"])),
        "corr_trailing_fwd": float(d["rv"].corr(d["rv_fwd"])),
    }


def crisis_table(vrp: pd.DataFrame, crises: list[dict[str, str]]) -> pd.DataFrame:
    """Behaviour of the premium during each crisis window (vol points, in %)."""
    rows = []
    for c in crises:
        d = vrp.loc[c["start"] : c["end"]].dropna(subset=["vrp"])
        if d.empty:
            continue
        rows.append(
            {
                "name": c["name"],
                "start": c["start"],
                "end": c["end"],
                "peak_vix": 100 * float(d["implied"].max()),
                "peak_rv_fwd": 100 * float(d["rv_fwd"].max()),
                "mean_vrp": 100 * float(d["vrp"].mean()),
                "min_vrp": 100 * float(d["vrp"].min()),
                "pct_positive": 100 * float((d["vrp"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def vrp_by_regime(
    vrp: pd.DataFrame, bins: tuple[float, ...] = (0, 15, 20, 30, np.inf)
) -> pd.DataFrame:
    """Average premium by VIX level: is the market's insurance priced fairly when calm?"""
    d = vrp.dropna(subset=["vrp"])
    labels = [
        f"{int(a)}-{int(b)}" if np.isfinite(b) else f"{int(a)}+"
        for a, b in zip(bins[:-1], bins[1:], strict=True)
    ]
    bucket = pd.cut(100 * d["implied"], bins=list(bins), labels=labels, right=False)
    g = d.groupby(bucket, observed=True)
    return pd.DataFrame(
        {
            "share_of_days": 100 * g.size() / len(d),
            "mean_vix": 100 * g["implied"].mean(),
            "mean_rv_fwd": 100 * g["rv_fwd"].mean(),
            "mean_vrp": 100 * g["vrp"].mean(),
            "pct_positive": 100 * g["vrp"].apply(lambda s: (s > 0).mean()),
        }
    ).rename_axis("vix_bucket")
