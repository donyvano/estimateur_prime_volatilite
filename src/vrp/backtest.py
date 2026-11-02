"""Short volatility strategy backtest (variance swap proxy). Step 7.

Instrument: a 1-month variance swap on the S&P 500, sold at the close of t.
    * strike  K = VIX_t (the VIX is, by construction, the 30-day variance swap rate)
    * payoff for the seller at t+21:  N_var * (K^2 - RV^2),  RV = realized vol t+1..t+21
    * with a vega notional N_vega, N_var = N_vega / (2K), so the P&L in vol points is
          (K^2 - RV^2) / (2K)   ~ K - RV when RV is close to K, but convex: losses
                                   grow with RV^2 when volatility explodes.
    * RV is capped at ``cap_multiple * K`` (2.5x is the market standard on index swaps).

Approximations (see docs/methodology.md): the VIX is not directly tradable, real
swap strikes sit slightly above the VIX (convexity, bid-ask), the 21 trading days
match the VIX's 30 calendar days only approximately, and collateral interest is ignored.

Trades are non-overlapping: one swap per 21-day period, the decision at t uses only
the VIX and the volatility forecast known at the close of t.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def short_var_swap_pnl(
    strike_vol: np.ndarray | float, realized_vol: np.ndarray | float, cap_multiple: float = 2.5
) -> np.ndarray | float:
    """P&L of a short variance swap per unit of vega notional, in vol points.

    Args:
        strike_vol: Strike K in vol points (e.g. 20 for a VIX of 20).
        realized_vol: Realized vol over the swap's life, in vol points.
        cap_multiple: Realized vol is capped at ``cap_multiple * K``.
    """
    k = np.asarray(strike_vol, dtype=float)
    rv = np.minimum(np.asarray(realized_vol, dtype=float), cap_multiple * k)
    out = (k**2 - rv**2) / (2 * k)
    return out.item() if out.ndim == 0 else out


def entry_dates(index: pd.DatetimeIndex, start: pd.Timestamp, horizon: int) -> pd.DatetimeIndex:
    """Non-overlapping roll dates: every ``horizon`` trading days from ``start``."""
    pos0 = index.get_indexer([start], method="bfill")[0]
    return index[pos0::horizon]


def run_strategy(
    frame: pd.DataFrame,
    cfg: dict[str, Any],
    forecast_col: str | None = None,
    threshold: float | None = None,
    offset: int = 0,
) -> pd.DataFrame:
    """Backtest one strategy. Returns one row per 21-day period.

    Args:
        frame: Daily frame with ``implied``, ``rv_fwd`` and the forecast columns.
        cfg: Project configuration (``backtest`` and ``premium`` sections).
        forecast_col: Column with the RV forecast. ``None`` -> always sell.
        threshold: Sell only if ``VIX - forecast > threshold`` (vol points).
            Defaults to ``cfg["backtest"]["threshold_vol_points"]``.
        offset: Shift of the first roll date, in trading days (0..horizon-1).

    Each row: entry/exit dates, strike, realized vol, forecast, signal (0/1),
    gross and net P&L (vol points) and the period return on capital.
    """
    bt = cfg["backtest"]
    h = cfg["premium"]["horizon"]
    threshold = bt["threshold_vol_points"] if threshold is None else threshold
    d = frame.dropna(subset=["implied", "rv_fwd"])
    if forecast_col is not None:
        d = d.dropna(subset=[forecast_col])
    entries = entry_dates(d.index, d.index[offset], h)
    full_index = frame.index

    k = 100 * d.loc[entries, "implied"].to_numpy()
    rv = 100 * d.loc[entries, "rv_fwd"].to_numpy()
    if forecast_col is None:
        fc = np.full(len(entries), np.nan)
        signal = np.ones(len(entries), dtype=bool)
    else:
        fc = 100 * d.loc[entries, forecast_col].to_numpy()
        signal = (k - fc) > threshold

    gross = np.where(signal, short_var_swap_pnl(k, rv, bt["cap_multiple"]), 0.0)
    cost = np.where(signal, bt["cost_vol_points"], 0.0)
    net = gross - cost
    exit_pos = full_index.get_indexer(entries) + h
    trades = pd.DataFrame(
        {
            "entry": entries,
            "exit": full_index[np.minimum(exit_pos, len(full_index) - 1)],
            "strike": k,
            "realized": rv,
            "forecast": fc,
            "signal": signal.astype(int),
            "gross_pnl": gross,
            "net_pnl": net,
            "ret": bt["vega_pct"] / 100 * net,
        }
    )
    trades["equity"] = (1 + trades["ret"]).cumprod()
    return trades


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough fall of an equity curve, as a negative fraction."""
    peak = np.maximum.accumulate(np.concatenate([[1.0], equity.to_numpy()]))[1:]
    return float((equity.to_numpy() / peak - 1).min())


def performance(trades: pd.DataFrame, horizon: int = 21, trading_days: int = 252) -> dict[str, Any]:
    """Annualised performance and tail-risk metrics of a strategy (returns in %).

    The swap is unfunded (only margin is posted), so its returns are already
    excess returns: the Sharpe ratio is ``mean / std * sqrt(periods per year)``.
    """
    ppy = trading_days / horizon
    r = trades["ret"]
    years = len(r) / ppy
    worst = r.idxmin()
    sorted_r = np.sort(r.to_numpy())
    n_tail = max(1, int(np.ceil(0.05 * len(r))))
    return {
        "ann_return": 100 * float(trades["equity"].iloc[-1] ** (1 / years) - 1),
        "ann_vol": 100 * float(r.std(ddof=1) * np.sqrt(ppy)),
        "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(ppy)),
        "max_drawdown": 100 * max_drawdown(trades["equity"]),
        "worst_period": 100 * float(r.min()),
        "worst_period_date": str(trades.loc[worst, "entry"].date()),
        "best_period": 100 * float(r.max()),
        "hit_rate": 100 * float((r[trades["signal"] == 1] > 0).mean()),
        "pct_invested": 100 * float(trades["signal"].mean()),
        "skew": float(r.skew()),
        "excess_kurtosis": float(r.kurt()),
        "cvar_5": 100 * float(sorted_r[:n_tail].mean()),
        "n_periods": int(len(r)),
        "final_equity": float(trades["equity"].iloc[-1]),
    }


def tail_events(trades: pd.DataFrame, crises: list[dict[str, str]]) -> pd.DataFrame:
    """Worst period return of a strategy during each crisis window."""
    rows = []
    for c in crises:
        start, end = pd.Timestamp(c["start"]), pd.Timestamp(c["end"])
        hit = trades[(trades["exit"] >= start) & (trades["entry"] <= end)]
        if hit.empty:
            continue
        w = hit.loc[hit["ret"].idxmin()]
        rows.append(
            {
                "name": c["name"],
                "entry": str(w["entry"].date()),
                "strike": float(w["strike"]),
                "realized": float(w["realized"]),
                "invested": bool(w["signal"]),
                "ret": 100 * float(w["ret"]),
            }
        )
    return pd.DataFrame(rows)


def threshold_sensitivity(
    frame: pd.DataFrame, cfg: dict[str, Any], forecast_col: str, thresholds: list[float]
) -> pd.DataFrame:
    """Sharpe / drawdown for several thresholds. In-sample by nature: shown for
    robustness only, the reported strategy uses the threshold fixed in the config."""
    h = cfg["premium"]["horizon"]
    rows = []
    for th in thresholds:
        perf = performance(run_strategy(frame, cfg, forecast_col, th), h)
        rows.append(
            {
                "threshold": th,
                **{k: perf[k] for k in ("ann_return", "sharpe", "max_drawdown", "pct_invested")},
            }
        )
    return pd.DataFrame(rows)


def roll_date_sensitivity(
    frame: pd.DataFrame, cfg: dict[str, Any], forecast_col: str | None
) -> pd.DataFrame:
    """Performance for each of the ``horizon`` possible roll dates.

    With monthly non-overlapping trades, the result depends on *which* day of the
    month the swap is rolled (a crash just after a roll hurts more). Reporting the
    distribution across all offsets shows how much of the result is luck.
    """
    h = cfg["premium"]["horizon"]
    rows = []
    for offset in range(h):
        perf = performance(run_strategy(frame, cfg, forecast_col, offset=offset), h)
        rows.append({"offset": offset, **perf})
    return pd.DataFrame(rows)
