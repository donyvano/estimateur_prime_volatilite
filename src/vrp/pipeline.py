"""End-to-end pipeline: data -> volatility -> options -> VRP -> forecasts -> backtest -> JSON.

Usage::

    python -m vrp.pipeline                    # use cached data
    python -m vrp.pipeline --refresh          # re-download prices
    python -m vrp.pipeline --refresh-options  # new option chain snapshot (run in US hours)
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from vrp import backtest as bt
from vrp import forecast as fc
from vrp import implied_vol as iv
from vrp.config import load_config, resolve_path
from vrp.data import load_market_data, load_option_chain
from vrp.export import records, series_payload, write_json
from vrp.figures import save_readme_figures
from vrp.monte_carlo import convergence_study
from vrp.premium import build_vrp_frame, crisis_table, vrp_by_regime, vrp_summary
from vrp.utils import set_seed, setup_logging

logger = logging.getLogger(__name__)

STRATEGIES = {
    "always": ("Always sell", None),
    "har_x": ("Sell if HAR-RV + VIX forecast VRP > threshold", "har_x"),
    "lightgbm": ("Sell if LightGBM forecast VRP > threshold", "lightgbm"),
}


# ---------------------------------------------------------------------------
# Section builders: each returns the JSON payload of one website section
# ---------------------------------------------------------------------------
def volatility_section(vrp: pd.DataFrame, crises: list[dict[str, str]]) -> dict[str, Any]:
    annotations = []
    for c in crises:
        window = vrp.loc[c["start"] : c["end"], "rv"].dropna()
        if not window.empty:
            annotations.append(
                {**c, "peak_date": window.idxmax(), "peak_rv": 100 * float(window.max())}
            )
    d = vrp.dropna(subset=["rv"])
    return {
        "series": series_payload(d, ["rv", "rv_park", "implied"], scale=100),
        "crises": annotations,
        "stats": {
            "mean_rv": 100 * float(d["rv"].mean()),
            "median_rv": 100 * float(d["rv"].median()),
            "max_rv": 100 * float(d["rv"].max()),
            "max_rv_date": d["rv"].idxmax(),
            "min_rv": 100 * float(d["rv"].min()),
            "parkinson_ratio": float((d["rv_park"] / d["rv"]).median()),
            "autocorr_21": float(d["rv"].autocorr(21)),
        },
    }


def premium_section(vrp: pd.DataFrame, crises: list[dict[str, str]]) -> dict[str, Any]:
    d = vrp.dropna(subset=["vrp"]).copy()
    d["vrp_1y"] = d["vrp"].rolling(252, min_periods=126).mean()
    counts, edges = np.histogram(100 * d["vrp"], bins=np.arange(-30, 21, 1.0))
    return {
        "summary": vrp_summary(vrp),
        "series": series_payload(d, ["implied", "rv_fwd", "vrp", "vrp_1y"], scale=100),
        "histogram": {
            "edges": edges.tolist(),
            "counts": counts.tolist(),
            "below_min": int((100 * d["vrp"] < -30).sum()),
        },
        "regimes": records(vrp_by_regime(vrp)),
        "crises": records(crisis_table(vrp, crises)),
    }


def options_section(
    chain: pd.DataFrame, rate: float, cfg: dict[str, Any], vix_last: float
) -> dict[str, Any]:
    table = iv.smooth_smile(iv.build_iv_table(chain, rate, cfg))
    val_date = table["valuation_date"].iloc[0]
    spot = float(chain["spot"].iloc[0])

    # Display uses standard monthly expiries only (third Friday, or Thursday before a
    # holiday): the most traded contracts, hence the least noisy last prices.
    exp = table["expiry"]
    monthly = table[exp.dt.day.between(15, 21) & exp.dt.weekday.isin([3, 4])]
    smiles = []
    days_available = np.sort(monthly["days"].unique())
    for target in (30, 60, 120, 240, 365):
        days = int(days_available[np.abs(days_available - target).argmin()])
        if any(s["days"] == days for s in smiles):
            continue
        g = monthly[monthly["days"] == days].sort_values("moneyness")
        smiles.append(
            {
                "days": days,
                "expiry": g["expiry"].iloc[0],
                "moneyness": g["moneyness"].tolist(),
                "iv": (100 * g["iv"]).tolist(),
                "type": g["type"].tolist(),
            }
        )

    term_all = iv.atm_term_structure(table)
    term = iv.atm_term_structure(monthly)
    grid = iv.surface_grid(monthly, cfg["options"]["surface_moneyness_grid"])
    # "1-month" headline numbers: median over expiries of 21-45 days, more robust
    # than a single expiry (month-end and weekly expiries can be off by 1-2 points).
    one_month = term_all[term_all["days"].between(21, 45)]
    atm_1m = float(one_month["atm_iv"].median())
    wings = []
    for expiry in one_month["expiry"]:
        g = table[table["expiry"] == expiry].sort_values("moneyness")
        wings.append([float(np.interp(m, g["moneyness"], g["iv"])) for m in (0.90, 1.10)])
    iv_90, iv_110 = np.median(np.array(wings), axis=0)
    mc = convergence_study(spot, spot, 30 / 365, rate, atm_1m, "call")

    src = table["price_source"].value_counts().to_dict()
    return {
        "valuation_date": val_date,
        "spot": spot,
        "rate": 100 * rate,
        "n_quotes": int(len(table)),
        "n_expiries": int(table["expiry"].nunique()),
        "price_source": src,
        "smiles": smiles,
        "term_structure": {
            "days": term["days"].tolist(),
            "atm_iv": (100 * term["atm_iv"]).tolist(),
        },
        "surface": {
            "days": grid.index.tolist(),
            "moneyness": [float(m) for m in grid.columns],
            "iv": (100 * grid).to_numpy().tolist(),
        },
        "headline": {
            "atm_1m": 100 * atm_1m,
            "one_month_expiries": int(len(one_month)),
            "put_90": 100 * iv_90,
            "call_110": 100 * iv_110,
            "skew_90_110": 100 * (iv_90 - iv_110),
            "vix": vix_last,
        },
        "monte_carlo": {
            "params": {"S": spot, "K": spot, "T_days": 30, "r": rate, "sigma": atm_1m},
            **{k: mc[k].tolist() for k in mc.columns},
        },
    }


def forecast_section(
    preds: pd.DataFrame, info: dict[str, Any], metrics: pd.DataFrame
) -> dict[str, Any]:
    weekly = preds.dropna(subset=["rv_fwd"]).iloc[::5]
    models = ["rv_fwd", "naive", "har", "har_x", "garch", "lightgbm", "implied"]
    har_labels = ["const", "RV_d^2", "RV_w^2", "RV_m^2"]
    return {
        "metrics": records(metrics),
        "sample": metrics.attrs,
        "series": series_payload(weekly, models, scale=100),
        "importance": [
            {"feature": k, "gain": float(v)} for k, v in info["lgbm_importance"].items()
        ],
        "har_beta": dict(zip(har_labels, info["har_beta"].tolist(), strict=True)),
        "har_x_beta": dict(zip([*har_labels, "VIX^2"], info["har_x_beta"].tolist(), strict=True)),
    }


def backtest_section(preds: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    h = cfg["premium"]["horizon"]
    crises = cfg["premium"]["crises"]
    out: dict[str, Any] = {"config": cfg["backtest"], "strategies": {}}
    for key, (label, col) in STRATEGIES.items():
        trades = bt.run_strategy(preds, cfg, col)
        eq = trades.set_index("exit")["equity"]
        peak = np.maximum.accumulate(np.concatenate([[1.0], eq.to_numpy()]))[1:]
        dd = eq / peak - 1
        rolls = bt.roll_date_sensitivity(preds, cfg, col)
        out["strategies"][key] = {
            "label": label,
            "metrics": bt.performance(trades, h),
            "curve": {
                "dates": [str(d.date()) for d in eq.index],
                "equity": eq.tolist(),
                "drawdown": (100 * dd).tolist(),
                "ret": (100 * trades["ret"]).tolist(),
                "signal": trades["signal"].tolist(),
            },
            "tails": records(bt.tail_events(trades, crises)),
            "roll_dates": {
                "sharpe": rolls["sharpe"].tolist(),
                "max_drawdown": rolls["max_drawdown"].tolist(),
                "ann_return": rolls["ann_return"].tolist(),
            },
        }
    out["threshold_sensitivity"] = records(
        bt.threshold_sensitivity(
            preds, cfg, cfg["backtest"]["model"], cfg["backtest"]["sensitivity_thresholds"]
        )
    )
    return out


# ---------------------------------------------------------------------------
def run(refresh: bool = False, refresh_options: bool = False) -> dict[str, Any]:
    """Run every step and write ``web/data/*.json``. Returns the summary payload."""
    cfg = load_config()
    setup_logging(cfg["logging"]["level"])
    set_seed(cfg["seed"])
    crises = cfg["premium"]["crises"]
    out_dir = resolve_path(cfg["web"]["export_dir"])
    processed = resolve_path(cfg["data"]["processed_dir"])
    processed.mkdir(parents=True, exist_ok=True)

    # Steps 1-2: data and realized volatility
    market = load_market_data(cfg, refresh)
    vrp = build_vrp_frame(market, cfg)
    vrp.to_parquet(processed / "vrp.parquet")
    vol = volatility_section(vrp, crises)
    write_json(vol, out_dir / "volatility.json")

    # Steps 3-4: options
    chain = load_option_chain(cfg, refresh_options)
    rate = float(market["rate"].iloc[-1])
    opts = options_section(chain, rate, cfg, float(market["vix"].iloc[-1]))
    write_json(opts, out_dir / "options.json")

    # Step 5: the premium
    prem = premium_section(vrp, crises)
    write_json(prem, out_dir / "premium.json")

    # Step 6: forecasts
    features = fc.build_features(vrp, cfg)
    preds, info = fc.run_walk_forward(features, cfg)
    preds.to_parquet(processed / "forecasts.parquet")
    metrics = fc.evaluate(preds)
    fcs = forecast_section(preds, info, metrics)
    write_json(fcs, out_dir / "forecast.json")

    # Step 7: backtest
    bts = backtest_section(preds, cfg)
    write_json(bts, out_dir / "backtest.json")

    best = metrics.drop(index="implied")["rmse"].idxmin()
    summary = {
        "generated": str(date.today()),
        "data_start": prem["summary"]["start"],
        "data_end": str(market.index[-1].date()),
        "vix_last": float(market["vix"].iloc[-1]),
        "rv_last": 100 * float(vrp["rv"].dropna().iloc[-1]),
        "premium": prem["summary"],
        "options": {"valuation_date": opts["valuation_date"], **opts["headline"]},
        "forecast": {
            "best_model": best,
            "best_label": fc.MODEL_NAMES[best],
            "best_rmse_vs_naive": float(metrics.loc[best, "rmse_vs_naive"]),
            "lightgbm_rmse_vs_naive": float(metrics.loc["lightgbm", "rmse_vs_naive"]),
        },
        "backtest": {k: v["metrics"] for k, v in bts["strategies"].items()},
        "backtest_rolls": {
            k: {
                "sharpe_mean": float(np.mean(v["roll_dates"]["sharpe"])),
                "sharpe_min": float(np.min(v["roll_dates"]["sharpe"])),
                "sharpe_max": float(np.max(v["roll_dates"]["sharpe"])),
                "dd_mean": float(np.mean(v["roll_dates"]["max_drawdown"])),
            }
            for k, v in bts["strategies"].items()
        },
    }
    write_json(summary, out_dir / "summary.json")
    save_readme_figures(vrp, preds, bts, resolve_path("docs/figures"))
    logger.info("Pipeline done: mean VRP %.2f vol points", summary["premium"]["mean_vrp"])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--refresh", action="store_true", help="re-download daily prices")
    parser.add_argument("--refresh-options", action="store_true", help="new option chain snapshot")
    args = parser.parse_args()
    run(args.refresh, args.refresh_options)


if __name__ == "__main__":
    main()
