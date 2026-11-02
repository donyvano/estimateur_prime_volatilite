"""Step 4: implied volatility inversion and chain processing."""

import numpy as np
import pandas as pd
import pytest

from vrp.black_scholes import bs_price, vega
from vrp.implied_vol import build_iv_table, implied_forward, implied_vol

S, R = 100.0, 0.03


@pytest.mark.parametrize("sigma", [0.05, 0.15, 0.3, 0.8, 1.5])
@pytest.mark.parametrize("k", [60, 90, 100, 110, 150])
@pytest.mark.parametrize("kind", ["call", "put"])
def test_round_trip(sigma: float, k: float, kind: str) -> None:
    T = 0.25
    price = float(bs_price(S, k, T, R, sigma, kind))
    if vega(S, k, T, R, sigma) < 1e-3:  # ~no time value: vol not identifiable numerically
        pytest.skip("vega too small")
    assert implied_vol(price, S, k, T, R, kind) == pytest.approx(sigma, abs=1e-6)


def test_deep_otm_short_maturity_uses_fallback() -> None:
    # Vega is tiny here: Newton alone would fail, Brent must rescue it.
    price = float(bs_price(S, 130, 10 / 365, R, 0.6, "call"))
    assert implied_vol(price, S, 130, 10 / 365, R, "call") == pytest.approx(0.6, abs=1e-5)


def test_price_outside_bounds_returns_nan() -> None:
    assert np.isnan(implied_vol(150.0, S, 100, 1.0, R, "call"))  # above S
    assert np.isnan(implied_vol(0.5, S, 50, 1.0, R, "call"))  # below intrinsic
    assert np.isnan(implied_vol(5.0, S, 100, 0.0, R, "call"))  # expired


def _synthetic_chain(F: float, T: float, sigma_fn) -> pd.DataFrame:  # noqa: ANN001
    snap = pd.Timestamp("2026-01-05")
    expiry = snap + pd.Timedelta(days=round(T * 365))
    T = round(T * 365) / 365  # same day-count as build_iv_table
    q = R - np.log(F / S) / T
    rows = []
    for k in np.arange(70, 131, 2.5):
        for kind in ("call", "put"):
            p = float(bs_price(S, k, T, R, sigma_fn(k / F), kind, q))
            rows.append(
                {"snapshot_date": snap, "spot": S, "expiry": expiry, "type": kind, "strike": k,
                 "bid": p * 0.99, "ask": p * 1.01, "last": p, "volume": 10.0,
                 "open_interest": 100.0, "yahoo_iv": np.nan, "last_trade": snap}
            )  # fmt: skip
    return pd.DataFrame(rows)


def test_implied_forward_recovers_dividends() -> None:
    T, F = 182 / 365, 100.5
    chain = _synthetic_chain(F, T, lambda m: 0.2).assign(price=lambda d: d["last"])
    assert implied_forward(chain, S, T, R) == pytest.approx(F, abs=1e-6)


def test_build_iv_table_recovers_skew(cfg: dict) -> None:
    skew = lambda m: 0.18 - 0.4 * (m - 1)  # noqa: E731 - puts richer than calls
    table = build_iv_table(_synthetic_chain(100.8, 0.25, skew), R, cfg)
    assert not table.empty
    assert np.allclose(table["iv"], skew(table["moneyness"]), atol=1e-4)
    # OTM filter: puts strictly below the forward, calls at or above it
    assert (table.loc[table["type"] == "put", "moneyness"] < 1).all()
    assert (table.loc[table["type"] == "call", "moneyness"] >= 1).all()
