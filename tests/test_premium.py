"""Step 5: forward realized vol alignment and explicit look-ahead bias tests."""

import numpy as np
import pandas as pd
import pytest

from vrp.premium import build_vrp_frame, crisis_table, forward_realized_vol, vrp_summary
from vrp.realized_vol import log_returns

H = 21


def test_forward_vol_uses_exactly_next_h_returns(prices: pd.Series) -> None:
    fwd = forward_realized_vol(prices, horizon=H)
    r = log_returns(prices).to_numpy()
    t = 300
    expected = np.sqrt(252 * np.mean(r[t + 1 : t + 1 + H] ** 2))
    assert fwd.iloc[t] == pytest.approx(expected)


def test_last_h_values_are_unknown(prices: pd.Series) -> None:
    fwd = forward_realized_vol(prices, horizon=H)
    assert fwd.iloc[-H:].isna().all()
    assert fwd.iloc[:-H].iloc[H:].notna().all()


def test_forward_vol_ignores_data_after_t_plus_h(prices: pd.Series) -> None:
    t = 400
    shocked = prices.copy()
    shocked.iloc[t + H + 1 :] *= 2.0
    assert forward_realized_vol(shocked, H).iloc[t] == forward_realized_vol(prices, H).iloc[t]


def test_forward_vol_depends_on_future(prices: pd.Series) -> None:
    """Sanity: the target *must* move when t+1..t+h moves (otherwise it is not forward)."""
    t = 400
    shocked = prices.copy()
    shocked.iloc[t + 5 :] *= 1.1  # one 10% jump inside the window
    assert forward_realized_vol(shocked, H).iloc[t] > forward_realized_vol(prices, H).iloc[t]


def test_known_at_t_columns_have_no_look_ahead(market: pd.DataFrame, cfg: dict) -> None:
    """Every column used as information at t must be unchanged if the future changes."""
    t = 600
    base = build_vrp_frame(market, cfg)
    shocked_mkt = market.copy()
    shocked_mkt.iloc[t + 1 :, :4] *= 1.3
    shocked_mkt.iloc[t + 1 :, 4] += 15
    shocked = build_vrp_frame(shocked_mkt, cfg)
    for col in ("implied", "rv", "rv_park"):
        pd.testing.assert_series_equal(base[col].iloc[: t + 1], shocked[col].iloc[: t + 1])
    # ...whereas the ex-post columns do change: they are targets, not features.
    assert not base["rv_fwd"].iloc[: t + 1].equals(shocked["rv_fwd"].iloc[: t + 1])


def test_vrp_definition(market: pd.DataFrame, cfg: dict) -> None:
    v = build_vrp_frame(market, cfg).dropna()
    np.testing.assert_allclose(v["vrp"], v["implied"] - v["rv_fwd"])
    np.testing.assert_allclose(v["vrp_var"], v["implied"] ** 2 - v["rv_fwd"] ** 2)


def test_summary_and_crisis_table(market: pd.DataFrame, cfg: dict) -> None:
    v = build_vrp_frame(market, cfg)
    s = vrp_summary(v)
    assert 0 <= s["pct_positive"] <= 100
    # synthetic: VIX ~22%, realized ~20% -> premium ~ +2 vol points
    assert s["mean_vrp"] == pytest.approx(2.0, abs=1.5)
    table = crisis_table(v, [{"name": "x", "start": "2016-01-01", "end": "2016-06-30"}])
    assert list(table["name"]) == ["x"]
