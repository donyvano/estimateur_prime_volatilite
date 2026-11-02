"""Step 3: Monte Carlo pricer vs closed form."""

import numpy as np
import pytest

from vrp.black_scholes import bs_price
from vrp.monte_carlo import convergence_study, mc_price

S, K, T, R, SIG = 100.0, 105.0, 0.5, 0.03, 0.25


@pytest.mark.parametrize("kind", ["call", "put"])
def test_mc_within_confidence_interval(kind: str) -> None:
    res = mc_price(S, K, T, R, SIG, kind, n_paths=200_000, rng=np.random.default_rng(7))
    exact = bs_price(S, K, T, R, SIG, kind)
    assert abs(res.price - exact) < 4 * res.std_error


def test_reproducible_with_seed() -> None:
    a = mc_price(S, K, T, R, SIG, rng=np.random.default_rng(3), n_paths=1000)
    b = mc_price(S, K, T, R, SIG, rng=np.random.default_rng(3), n_paths=1000)
    assert a == b


def test_error_shrinks_like_one_over_sqrt_n() -> None:
    df = convergence_study(S, K, T, R, SIG, path_counts=(1_000, 100_000))
    ratio = df["std_error"].iloc[0] / df["std_error"].iloc[1]
    assert ratio == pytest.approx(10.0, rel=0.1)  # 100x paths -> 10x smaller error


def test_antithetic_reduces_error() -> None:
    plain = mc_price(S, K, T, R, SIG, n_paths=50_000, rng=np.random.default_rng(1))
    anti = mc_price(S, K, T, R, SIG, n_paths=50_000, rng=np.random.default_rng(1), antithetic=True)
    assert anti.std_error < plain.std_error


def test_ci95_contains_price() -> None:
    res = mc_price(S, K, T, R, SIG, n_paths=10_000)
    lo, hi = res.ci95
    assert lo < res.price < hi
