"""Black-Scholes prices and greeks for European options. Step 3.

Notation (all functions are vectorised with NumPy broadcasting):
    S      spot price of the underlying
    K      strike
    T      time to maturity, in years
    r      continuously compounded risk-free rate
    sigma  volatility (annualised, decimals)
    q      continuous dividend yield

d1 = [ln(S/K) + (r - q + sigma^2/2) T] / (sigma sqrt(T)),   d2 = d1 - sigma sqrt(T)
Call = S e^{-qT} N(d1) - K e^{-rT} N(d2)
Put  = K e^{-rT} N(-d2) - S e^{-qT} N(-d1)
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.stats import norm

OptionType = Literal["call", "put"]

# sigma * sqrt(T) below this is treated as "no uncertainty left" (expiry or zero vol).
_EPS = 1e-12


def _check_type(option_type: str) -> None:
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type!r}")


def d1_d2(
    S: ArrayLike, K: ArrayLike, T: ArrayLike, r: ArrayLike, sigma: ArrayLike, q: ArrayLike = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(d1, d2)``. Requires ``sigma * sqrt(T) > 0``."""
    S, K, T, r, sigma, q = map(np.asarray, (S, K, T, r, sigma, q))
    vol_sqrt_t = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def bs_price(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    r: ArrayLike,
    sigma: ArrayLike,
    option_type: OptionType = "call",
    q: ArrayLike = 0.0,
) -> np.ndarray | float:
    """Black-Scholes price of a European call or put.

    Limit cases are handled explicitly: when ``sigma * sqrt(T) -> 0`` the option
    is worth its discounted intrinsic value on the forward,
    ``e^{-rT} max(F - K, 0)`` for a call, with ``F = S e^{(r-q)T}``.
    """
    _check_type(option_type)
    S, K, T, r, sigma, q = (np.asarray(x, dtype=float) for x in (S, K, T, r, sigma, q))
    df_r, df_q = np.exp(-r * T), np.exp(-q * T)
    vol_sqrt_t = sigma * np.sqrt(T)
    safe = vol_sqrt_t > _EPS
    with np.errstate(divide="ignore", invalid="ignore"):
        d1, d2 = d1_d2(S, K, T, r, np.where(safe, sigma, 1.0), q)
        d1 = np.where(safe, d1, 0.0)
        d2 = np.where(safe, d2, 0.0)
    if option_type == "call":
        price = S * df_q * norm.cdf(d1) - K * df_r * norm.cdf(d2)
        intrinsic = np.maximum(S * df_q - K * df_r, 0.0)
    else:
        price = K * df_r * norm.cdf(-d2) - S * df_q * norm.cdf(-d1)
        intrinsic = np.maximum(K * df_r - S * df_q, 0.0)
    out = np.where(safe, price, intrinsic)
    return out.item() if out.ndim == 0 else out


def call_price(
    S: ArrayLike, K: ArrayLike, T: ArrayLike, r: ArrayLike, sigma: ArrayLike, q: ArrayLike = 0.0
) -> np.ndarray | float:
    """European call price. See :func:`bs_price`."""
    return bs_price(S, K, T, r, sigma, "call", q)


def put_price(
    S: ArrayLike, K: ArrayLike, T: ArrayLike, r: ArrayLike, sigma: ArrayLike, q: ArrayLike = 0.0
) -> np.ndarray | float:
    """European put price. See :func:`bs_price`."""
    return bs_price(S, K, T, r, sigma, "put", q)


# ---------------------------------------------------------------------------
# Greeks. Trader reading of each one is in GLOSSARY.md.
# ---------------------------------------------------------------------------
def _scalar(x: np.ndarray) -> np.ndarray | float:
    return x.item() if np.ndim(x) == 0 else x


def delta(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    r: ArrayLike,
    sigma: ArrayLike,
    option_type: OptionType = "call",
    q: ArrayLike = 0.0,
) -> np.ndarray | float:
    """dPrice/dS. Call in [0, 1], put in [-1, 0]."""
    _check_type(option_type)
    d1, _ = d1_d2(S, K, T, r, sigma, q)
    df_q = np.exp(-np.asarray(q) * np.asarray(T))
    out = df_q * norm.cdf(d1) if option_type == "call" else df_q * (norm.cdf(d1) - 1.0)
    return _scalar(out)


def gamma(
    S: ArrayLike, K: ArrayLike, T: ArrayLike, r: ArrayLike, sigma: ArrayLike, q: ArrayLike = 0.0
) -> np.ndarray | float:
    """d2Price/dS2, identical for calls and puts, always >= 0."""
    S, T, sigma, q = map(np.asarray, (S, T, sigma, q))
    d1, _ = d1_d2(S, K, T, r, sigma, q)
    return _scalar(np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T)))


def vega(
    S: ArrayLike, K: ArrayLike, T: ArrayLike, r: ArrayLike, sigma: ArrayLike, q: ArrayLike = 0.0
) -> np.ndarray | float:
    """dPrice/dsigma for a change of 1.00 in sigma (divide by 100 for one vol point)."""
    S, T, q = map(np.asarray, (S, T, q))
    d1, _ = d1_d2(S, K, T, r, sigma, q)
    return _scalar(S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T))


def theta(
    S: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    r: ArrayLike,
    sigma: ArrayLike,
    option_type: OptionType = "call",
    q: ArrayLike = 0.0,
) -> np.ndarray | float:
    """dPrice/dt per year (calendar time passing). Divide by 365 for a daily theta.

    Note the sign convention: this is the derivative with respect to the passage
    of time, i.e. ``-dPrice/dT``; it is usually negative for a long option.
    """
    _check_type(option_type)
    S, K, T, r, sigma, q = map(np.asarray, (S, K, T, r, sigma, q))
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    decay = -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
    if option_type == "call":
        out = decay + q * S * np.exp(-q * T) * norm.cdf(d1) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        out = (
            decay - q * S * np.exp(-q * T) * norm.cdf(-d1) + r * K * np.exp(-r * T) * norm.cdf(-d2)
        )
    return _scalar(out)
