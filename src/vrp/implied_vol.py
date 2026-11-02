"""Implied volatility inversion, smile and surface. Step 4.

Implied volatility = the unique sigma that makes the Black-Scholes price equal to
the market price. Black-Scholes is strictly increasing in sigma (vega > 0), so the
inverse exists as long as the price respects the no-arbitrage bounds.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from scipy.optimize import brentq

from vrp.black_scholes import OptionType, bs_price, vega

logger = logging.getLogger(__name__)

SIGMA_LOW, SIGMA_HIGH = 1e-4, 5.0


# ---------------------------------------------------------------------------
# Inversion
# ---------------------------------------------------------------------------
def price_bounds(
    S: float, K: float, T: float, r: float, option_type: OptionType, q: float = 0.0
) -> tuple[float, float]:
    """No-arbitrage bounds of a European option price (sigma -> 0 and sigma -> inf)."""
    fwd_s, pv_k = S * np.exp(-q * T), K * np.exp(-r * T)
    if option_type == "call":
        return max(fwd_s - pv_k, 0.0), fwd_s
    return max(pv_k - fwd_s, 0.0), pv_k


def implied_vol(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType = "call",
    q: float = 0.0,
    tol: float = 1e-8,
    max_iter: int = 50,
) -> float:
    """Invert Black-Scholes: Newton-Raphson on vega, Brent's method as a fallback.

    Newton: ``sigma_{n+1} = sigma_n - (BS(sigma_n) - price) / vega(sigma_n)``.
    It converges quadratically near the ATM, but vega vanishes for deep OTM/ITM
    options and short maturities: the step then explodes. In that case (or if
    sigma leaves ``[1e-4, 5]``) we switch to Brent, which brackets the root and
    always converges because BS is monotone in sigma.

    Returns:
        The implied volatility, or ``NaN`` if the price violates the bounds.
    """
    if T <= 0 or price <= 0:
        return float("nan")
    lower, upper = price_bounds(S, K, T, r, option_type, q)
    if not (lower < price < upper):
        return float("nan")

    # Brenner-Subrahmanyam (1988) ATM approximation as a starting point.
    sigma = float(np.clip(np.sqrt(2 * np.pi / T) * price / S, 0.05, 1.5))
    for _ in range(max_iter):
        diff = float(bs_price(S, K, T, r, sigma, option_type, q)) - price
        if abs(diff) < tol:
            return sigma
        v = float(vega(S, K, T, r, sigma, q))
        if v < 1e-8:
            break
        sigma -= diff / v
        if not (SIGMA_LOW < sigma < SIGMA_HIGH):
            break

    def objective(s: float) -> float:
        return float(bs_price(S, K, T, r, s, option_type, q)) - price

    try:
        return float(brentq(objective, SIGMA_LOW, SIGMA_HIGH, xtol=tol, maxiter=200))
    except ValueError:  # no sign change: price unreachable within the bracket
        return float("nan")


# ---------------------------------------------------------------------------
# Option chain -> clean quotes
# ---------------------------------------------------------------------------
def add_market_price(chain: pd.DataFrame) -> pd.DataFrame:
    """Choose the price used for the inversion and flag where it comes from.

    * Market open: mid = (bid + ask) / 2 when both sides are quoted.
    * Market closed (Yahoo zeroes bid/ask outside US hours): last traded price,
      only if it traded during the most recent session. Stale prices would mix
      quotes taken at different spot levels.
    """
    out = chain.copy()
    has_quote = (out["bid"] > 0) & (out["ask"] > 0)
    last_session = out["last_trade"].dt.normalize().max()
    fresh_trade = (out["last_trade"].dt.normalize() == last_session) & (out["volume"] > 0)
    out["mid"] = np.where(has_quote, 0.5 * (out["bid"] + out["ask"]), np.nan)
    out["price"] = np.where(has_quote, out["mid"], np.where(fresh_trade, out["last"], np.nan))
    out["price_source"] = np.where(has_quote, "mid", np.where(fresh_trade, "last", "none"))
    out["rel_spread"] = np.where(has_quote, (out["ask"] - out["bid"]) / out["mid"], np.nan)
    return out


def valuation_date(chain: pd.DataFrame) -> pd.Timestamp:
    """Date at which the quotes are valid: the snapshot date, or the last session if closed."""
    if (chain["price_source"] == "mid").mean() > 0.5:
        return pd.Timestamp(chain["snapshot_date"].iloc[0]).normalize()
    return pd.Timestamp(chain["last_trade"].max()).normalize()


def implied_forward(expiry_quotes: pd.DataFrame, S: float, T: float, r: float) -> float:
    """Forward price from put-call parity, ``C - P = e^{-rT} (F - K)``.

    Using the strikes closest to the spot (where both options are liquid) and the
    median over them makes the estimate robust; it implicitly prices dividends,
    so no dividend yield has to be guessed.
    """
    calls = expiry_quotes[expiry_quotes["type"] == "call"].set_index("strike")["price"]
    puts = expiry_quotes[expiry_quotes["type"] == "put"].set_index("strike")["price"]
    both = pd.concat([calls.rename("c"), puts.rename("p")], axis=1).dropna()
    if both.empty:
        return S * np.exp(r * T)
    near = both.loc[(both.index.to_series() - S).abs().sort_values().index[:6]]
    forwards = near.index.to_numpy() + np.exp(r * T) * (near["c"] - near["p"]).to_numpy()
    return float(np.median(forwards))


def build_iv_table(chain: pd.DataFrame, rate: float, cfg: dict[str, Any]) -> pd.DataFrame:
    """Filter the option chain, then compute one implied volatility per quote.

    Filters (documented in docs/methodology.md):
        1. a usable price (see :func:`add_market_price`) of at least ``min_price``;
        2. maturity between ``min_days`` and ``max_days``;
        3. if quoted: bid >= ``min_bid``, relative spread <= ``max_rel_spread`` and
           open interest >= ``min_open_interest``;
        4. moneyness K/F within ``[moneyness_min, moneyness_max]``;
        5. out-of-the-money options only: puts for K < F, calls for K >= F. OTM
           options are the liquid ones and, SPY options being American, they carry
           almost no early-exercise premium, so European Black-Scholes applies.

    Returns:
        One row per option with ``T, forward, moneyness, log_moneyness, iv``.
    """
    o = cfg["options"]
    df = add_market_price(chain)
    val_date = valuation_date(df)
    S = float(df["spot"].iloc[0])
    df["days"] = (df["expiry"] - val_date).dt.days
    df["T"] = df["days"] / 365.0
    n0 = len(df)

    # Prices near the minimum tick ($0.01) make the implied vol meaningless.
    df = df[df["price"].notna() & (df["price"] >= o["min_price"])]
    df = df[df["days"].between(o["min_days"], o["max_days"])]
    quoted = df["price_source"] == "mid"
    liquid_quote = (
        (df["bid"] >= o["min_bid"])
        & (df["rel_spread"] <= o["max_rel_spread"])
        & (df["open_interest"] >= o["min_open_interest"])
    )
    df = df[~quoted | liquid_quote]

    rows = []
    for _, grp in df.groupby("expiry"):
        T = float(grp["T"].iloc[0])
        F = implied_forward(grp, S, T, rate)
        q = rate - np.log(F / S) / T  # dividend yield implied by the forward
        g = grp.assign(forward=F, q=q, moneyness=grp["strike"] / F)
        otm = ((g["type"] == "put") & (g["strike"] < F)) | (
            (g["type"] == "call") & (g["strike"] >= F)
        )
        g = g[otm & g["moneyness"].between(o["moneyness_min"], o["moneyness_max"])]
        g = g.assign(
            iv=[
                implied_vol(p, S, k, T, rate, t, q)
                for p, k, t in zip(g["price"], g["strike"], g["type"], strict=True)
            ]
        )
        rows.append(g)
    out = pd.concat(rows, ignore_index=True).dropna(subset=["iv"])
    out["log_moneyness"] = np.log(out["moneyness"])
    out["valuation_date"] = val_date
    logger.info(
        "IV table: %d quotes kept out of %d (%d expiries, valuation date %s)",
        len(out), n0, out["expiry"].nunique(), val_date.date(),
    )  # fmt: skip
    return out


def smooth_smile(iv_table: pd.DataFrame) -> pd.DataFrame:
    """Remove isolated outliers within each expiry (last prices are asynchronous).

    A point is dropped if it deviates by more than 3 vol points from the rolling
    median of its neighbours in moneyness.
    """
    kept = []
    for _, g in iv_table.sort_values("moneyness").groupby("expiry"):
        med = g["iv"].rolling(7, center=True, min_periods=3).median()
        kept.append(g[(g["iv"] - med).abs() <= 0.03])
    return pd.concat(kept, ignore_index=True)


def atm_term_structure(iv_table: pd.DataFrame) -> pd.DataFrame:
    """ATM implied vol per expiry: linear interpolation of the smile at K/F = 1."""
    rows = []
    for expiry, g in iv_table.sort_values("moneyness").groupby("expiry"):
        if g["moneyness"].min() <= 1 <= g["moneyness"].max():
            atm = float(np.interp(1.0, g["moneyness"], g["iv"]))
            rows.append({"expiry": expiry, "days": int(g["days"].iloc[0]), "atm_iv": atm})
    return pd.DataFrame(rows)


def surface_grid(iv_table: pd.DataFrame, moneyness_grid: list[float]) -> pd.DataFrame:
    """Interpolate implied vols on a (moneyness x maturity) grid for the 3D surface.

    Interpolation is linear in (moneyness, sqrt(T)): total variance grows roughly
    with T, so sqrt(T) spreads short maturities, where the surface bends the most.
    Grid points outside the convex hull of the data are left as NaN (no extrapolation).
    """
    pts = np.column_stack([iv_table["moneyness"], np.sqrt(iv_table["T"])])
    days = np.sort(iv_table["days"].unique())
    m, d = np.meshgrid(moneyness_grid, days)
    z = griddata(pts, iv_table["iv"], (m, np.sqrt(d / 365.0)), method="linear")
    return pd.DataFrame(z, index=pd.Index(days, name="days"), columns=moneyness_grid)
