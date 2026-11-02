"""Step 7: variance swap P&L and strategy mechanics."""

import numpy as np
import pandas as pd
import pytest

from vrp.backtest import (
    entry_dates,
    max_drawdown,
    performance,
    run_strategy,
    short_var_swap_pnl,
)


def test_var_swap_pnl_signs_and_convexity() -> None:
    assert short_var_swap_pnl(20, 15) > 0  # realized < strike: the seller earns
    assert short_var_swap_pnl(20, 20) == pytest.approx(0.0)
    # (K^2 - RV^2) / 2K: losses grow faster than gains (short convexity)
    assert abs(short_var_swap_pnl(20, 30)) > abs(short_var_swap_pnl(20, 10))
    assert short_var_swap_pnl(20, 15) == pytest.approx((400 - 225) / 40)


def test_var_swap_cap() -> None:
    assert short_var_swap_pnl(20, 100, cap_multiple=2.5) == short_var_swap_pnl(20, 50)


@pytest.fixture
def frame() -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-01", periods=21 * 12 + 21)
    rng = np.random.default_rng(0)
    implied = 0.20 + rng.normal(0, 0.01, len(idx))
    return pd.DataFrame(
        {"implied": implied, "rv_fwd": implied - 0.03, "fc": implied - 0.01}, index=idx
    )


def test_trades_do_not_overlap(frame: pd.DataFrame, cfg: dict) -> None:
    trades = run_strategy(frame, cfg)
    assert (trades["entry"].iloc[1:].to_numpy() >= trades["exit"].iloc[:-1].to_numpy()).all()


def test_always_sell_earns_premium_minus_costs(frame: pd.DataFrame, cfg: dict) -> None:
    trades = run_strategy(frame, cfg)
    assert trades["signal"].all()
    assert (trades["net_pnl"] == trades["gross_pnl"] - cfg["backtest"]["cost_vol_points"]).all()
    assert (trades["ret"] > 0).all()


def test_signal_threshold(frame: pd.DataFrame, cfg: dict) -> None:
    # forecast VRP = 1 vol point everywhere: sells at threshold 0.5, never at 2
    assert run_strategy(frame, cfg, "fc", threshold=0.5)["signal"].all()
    flat = run_strategy(frame, cfg, "fc", threshold=2.0)
    assert not flat["signal"].any()
    assert (flat["ret"] == 0).all()


def test_decision_uses_only_entry_day_information(frame: pd.DataFrame, cfg: dict) -> None:
    trades = run_strategy(frame, cfg, "fc", threshold=0.5)
    e = trades["entry"].iloc[3]
    assert trades["strike"].iloc[3] == pytest.approx(100 * frame.loc[e, "implied"])
    assert trades["forecast"].iloc[3] == pytest.approx(100 * frame.loc[e, "fc"])


def test_entry_dates_spacing() -> None:
    idx = pd.bdate_range("2020-01-01", periods=100)
    e = entry_dates(idx, idx[3], 21)
    assert e[0] == idx[3]
    assert all(idx.get_loc(b) - idx.get_loc(a) == 21 for a, b in zip(e[:-1], e[1:], strict=True))


def test_max_drawdown() -> None:
    eq = pd.Series([1.1, 1.2, 0.9, 1.0, 1.3])
    assert max_drawdown(eq) == pytest.approx(0.9 / 1.2 - 1)
    assert max_drawdown(pd.Series([0.8, 1.0])) == pytest.approx(-0.2)  # from initial capital


def test_performance_keys(frame: pd.DataFrame, cfg: dict) -> None:
    perf = performance(run_strategy(frame, cfg))
    assert perf["pct_invested"] == 100.0
    assert perf["max_drawdown"] <= 0
    assert perf["sharpe"] > 0
