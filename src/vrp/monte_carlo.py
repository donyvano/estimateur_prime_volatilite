"""Monte Carlo pricer under geometric Brownian motion. Step 3.

Under the risk-neutral measure the terminal price is exactly
    S_T = S_0 exp((r - q - sigma^2 / 2) T + sigma sqrt(T) Z),   Z ~ N(0, 1)
so a European option needs no time discretisation: one Gaussian draw per path.
Price = e^{-rT} * mean(payoff(S_T)). By the central limit theorem the standard
error is std(payoff) / sqrt(N): 4x more paths -> 2x smaller error.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vrp.black_scholes import OptionType, bs_price


@dataclass(frozen=True)
class MCResult:
    """Monte Carlo estimate with its standard error and 95% confidence interval."""

    price: float
    std_error: float

    @property
    def ci95(self) -> tuple[float, float]:
        return self.price - 1.96 * self.std_error, self.price + 1.96 * self.std_error


def simulate_terminal_prices(
    S: float,
    T: float,
    r: float,
    sigma: float,
    n_paths: int,
    rng: np.random.Generator,
    q: float = 0.0,
    antithetic: bool = False,
) -> np.ndarray:
    """Draw ``n_paths`` terminal prices under risk-neutral GBM.

    With ``antithetic=True`` half of the draws are ``-Z``: paths come in mirrored
    pairs, which cancels part of the noise (variance reduction).
    """
    if antithetic:
        half = rng.standard_normal((n_paths + 1) // 2)
        z = np.concatenate([half, -half])[:n_paths]
    else:
        z = rng.standard_normal(n_paths)
    drift = (r - q - 0.5 * sigma**2) * T
    return S * np.exp(drift + sigma * np.sqrt(T) * z)


def mc_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
    q: float = 0.0,
    n_paths: int = 100_000,
    rng: np.random.Generator | None = None,
    antithetic: bool = False,
) -> MCResult:
    """Monte Carlo price of a European call or put."""
    rng = rng if rng is not None else np.random.default_rng(0)
    s_t = simulate_terminal_prices(S, T, r, sigma, n_paths, rng, q, antithetic)
    payoff = np.maximum(s_t - K, 0.0) if option_type == "call" else np.maximum(K - s_t, 0.0)
    discounted = np.exp(-r * T) * payoff
    if antithetic:
        # Mirrored pairs are not independent: the error must be computed on pair means.
        n_pairs = n_paths // 2
        pairs = 0.5 * (discounted[:n_pairs] + discounted[n_pairs : 2 * n_pairs])
        return MCResult(float(pairs.mean()), float(pairs.std(ddof=1) / np.sqrt(n_pairs)))
    return MCResult(float(discounted.mean()), float(discounted.std(ddof=1) / np.sqrt(n_paths)))


def convergence_study(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
    q: float = 0.0,
    path_counts: tuple[int, ...] = (100, 300, 1_000, 3_000, 10_000, 30_000, 100_000, 300_000),
    seed: int = 42,
) -> pd.DataFrame:
    """Compare Monte Carlo to the closed form for growing numbers of paths.

    Returns one row per ``n_paths`` with the MC price, standard error, absolute
    error vs Black-Scholes and ``std_error * sqrt(n)`` (constant if error ~ 1/sqrt(N)).
    """
    exact = float(bs_price(S, K, T, r, sigma, option_type, q))
    rows = []
    for n in path_counts:
        rng = np.random.default_rng(seed)
        plain = mc_price(S, K, T, r, sigma, option_type, q, n, rng)
        anti = mc_price(S, K, T, r, sigma, option_type, q, n, np.random.default_rng(seed), True)
        rows.append(
            {
                "n_paths": n,
                "mc_price": plain.price,
                "std_error": plain.std_error,
                "abs_error": abs(plain.price - exact),
                "scaled_std_error": plain.std_error * np.sqrt(n),
                "antithetic_std_error": anti.std_error,
                "bs_price": exact,
            }
        )
    return pd.DataFrame(rows)
