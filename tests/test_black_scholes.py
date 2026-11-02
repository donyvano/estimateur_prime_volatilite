"""Step 3: Black-Scholes prices and greeks."""

import numpy as np
import pytest

from vrp.black_scholes import bs_price, call_price, delta, gamma, put_price, theta, vega

S, K, T, R, SIG = 100.0, 100.0, 1.0, 0.05, 0.2


def test_textbook_values() -> None:
    # Hull, Options Futures and Other Derivatives.
    assert call_price(S, K, T, R, SIG) == pytest.approx(10.4506, abs=1e-4)
    assert put_price(S, K, T, R, SIG) == pytest.approx(5.5735, abs=1e-4)


@pytest.mark.parametrize("k", [70, 90, 100, 110, 140])
@pytest.mark.parametrize("q", [0.0, 0.02])
def test_put_call_parity(k: float, q: float) -> None:
    c = call_price(S, k, T, R, SIG, q)
    p = put_price(S, k, T, R, SIG, q)
    assert c - p == pytest.approx(S * np.exp(-q * T) - k * np.exp(-R * T), abs=1e-10)


def test_price_bounds() -> None:
    c = call_price(S, K, T, R, SIG)
    assert max(S - K * np.exp(-R * T), 0) <= c <= S


def test_zero_maturity_is_intrinsic() -> None:
    assert call_price(110, 100, 0.0, R, SIG) == pytest.approx(10.0)
    assert put_price(110, 100, 0.0, R, SIG) == pytest.approx(0.0)
    assert put_price(90, 100, 0.0, R, SIG) == pytest.approx(10.0)


def test_zero_vol_is_discounted_forward_intrinsic() -> None:
    expected = S - K * np.exp(-R * T)
    assert call_price(S, K, T, R, 0.0) == pytest.approx(expected)


def test_price_increases_with_vol() -> None:
    prices = bs_price(S, K, T, R, np.array([0.1, 0.2, 0.4]))
    assert np.all(np.diff(prices) > 0)


def test_vectorised_matches_scalar() -> None:
    ks = np.array([90.0, 100.0, 110.0])
    vec = call_price(S, ks, T, R, SIG)
    assert vec == pytest.approx([call_price(S, k, T, R, SIG) for k in ks])


def test_invalid_option_type() -> None:
    with pytest.raises(ValueError):
        bs_price(S, K, T, R, SIG, "straddle")  # type: ignore[arg-type]


def test_greek_signs_and_ranges() -> None:
    assert 0 < delta(S, K, T, R, SIG, "call") < 1
    assert -1 < delta(S, K, T, R, SIG, "put") < 0
    assert gamma(S, K, T, R, SIG) > 0
    assert vega(S, K, T, R, SIG) > 0
    assert theta(S, K, T, R, SIG, "call") < 0


def test_call_minus_put_delta_is_one() -> None:
    assert delta(S, K, T, R, SIG, "call") - delta(S, K, T, R, SIG, "put") == pytest.approx(1.0)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_greeks_match_finite_differences(kind: str) -> None:
    h = 1e-4
    p = lambda s=S, sig=SIG, t=T: bs_price(s, K, t, R, sig, kind, 0.01)  # noqa: E731
    assert delta(S, K, T, R, SIG, kind, 0.01) == pytest.approx(
        (p(s=S + h) - p(s=S - h)) / (2 * h), rel=1e-5
    )
    assert gamma(S, K, T, R, SIG, 0.01) == pytest.approx(
        (p(s=S + 1e-2) - 2 * p() + p(s=S - 1e-2)) / 1e-4, rel=1e-4
    )
    assert vega(S, K, T, R, SIG, 0.01) == pytest.approx(
        (p(sig=SIG + h) - p(sig=SIG - h)) / (2 * h), rel=1e-5
    )
    # theta = derivative w.r.t. calendar time = -dPrice/dT
    assert theta(S, K, T, R, SIG, kind, 0.01) == pytest.approx(
        -(p(t=T + h) - p(t=T - h)) / (2 * h), rel=1e-5
    )
