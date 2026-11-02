"""Realized volatility forecasting models (naive, HAR-RV, GARCH, LightGBM). Step 6.

Target: ``rv_fwd`` at t, the realized vol over t+1..t+21 (the life of VIX_t).
Every feature at t uses information available at the close of t.

Validation is walk-forward with an expanding window, refitted every calendar
year. Training rows whose target window overlaps the test year are purged:
their target is only known after the test year has started (label leakage).
A random train/test split would leak the future in two ways: overlapping
targets, and volatility clustering (yesterday's vol tells you about today's).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from vrp.realized_vol import close_to_close_vol, log_returns

logger = logging.getLogger(__name__)

LGBM_FEATURES = [
    "rv_d", "rv_w", "rv_m", "rv_q", "rv_park", "implied", "vix_chg_5",
    "ret_1", "ret_5", "ret_21", "vrp_past", "vix_rv_ratio",
]  # fmt: skip


# ---------------------------------------------------------------------------
# Features (all known at the close of t)
# ---------------------------------------------------------------------------
def build_features(vrp: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Feature matrix indexed like ``vrp``. Adds the target column ``rv_fwd``.

    * ``rv_d, rv_w, rv_m``: realized vol over 1, 5 and 22 days (HAR components).
    * ``rv_q``: 63-day realized vol (slow regime).
    * ``rv_park``: 21-day Parkinson vol (intraday range information).
    * ``implied``: VIX, the market's own forecast.
    * ``vix_chg_5``: 5-day change of the VIX (stress building up).
    * ``ret_1, ret_5, ret_21``: past S&P 500 log-returns (leverage effect:
      vol rises after a fall).
    * ``vrp_past``: VIX quoted 21 days ago minus the vol realised since then.
      This is the *last fully observed* premium, so it is known at t.
    """
    n = cfg["volatility"]["trading_days"]
    d_lag, w_lag, m_lag = cfg["forecast"]["har_lags"]
    close = vrp["spx_close"]
    r = log_returns(close)
    f = pd.DataFrame(index=vrp.index)
    f["rv_d"] = np.sqrt(n) * r.abs() if d_lag == 1 else close_to_close_vol(close, d_lag, n)
    f["rv_w"] = close_to_close_vol(close, w_lag, n)
    f["rv_m"] = close_to_close_vol(close, m_lag, n)
    f["rv_q"] = close_to_close_vol(close, 63, n)
    f["rv_park"] = vrp["rv_park"]
    f["implied"] = vrp["implied"]
    f["vix_chg_5"] = vrp["implied"] - vrp["implied"].shift(5)
    f["ret_1"] = r
    f["ret_5"] = r.rolling(5).sum()
    f["ret_21"] = r.rolling(21).sum()
    f["vrp_past"] = vrp["implied"].shift(21) - vrp["rv"]
    f["vix_rv_ratio"] = vrp["implied"] / vrp["rv"]
    f["rv"] = vrp["rv"]  # 21-day trailing vol: the naive forecast
    f["spx_close"] = close  # needed by GARCH, which works on raw returns
    f["rv_fwd"] = vrp["rv_fwd"]
    return f


# ---------------------------------------------------------------------------
# Walk-forward splits
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Split:
    year: int
    train_end: pd.Timestamp  # last date whose target is fully known before test_start
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def walk_forward_splits(
    index: pd.DatetimeIndex, first_test_year: int, horizon: int
) -> Iterator[Split]:
    """Yearly expanding-window splits with a ``horizon``-day purge before each test year."""
    years = sorted({y for y in index.year if y >= first_test_year})
    for year in years:
        in_year = index[index.year == year]
        test_start = in_year[0]
        pos = index.get_loc(test_start)
        # Target of row i uses returns up to i + horizon: keep i + horizon < pos.
        train_end_pos = pos - horizon - 1
        if train_end_pos < 0:
            continue
        yield Split(year, index[train_end_pos], test_start, in_year[-1])


# ---------------------------------------------------------------------------
# Models: each returns out-of-sample predictions (annualised vol) on the test year
# ---------------------------------------------------------------------------
def _har_design(f: pd.DataFrame, with_vix: bool) -> pd.DataFrame:
    """HAR regressors in variance: [1, RV_d^2, RV_w^2, RV_m^2 (, VIX^2)]."""
    x = pd.DataFrame({"const": 1.0, "d": f["rv_d"] ** 2, "w": f["rv_w"] ** 2, "m": f["rv_m"] ** 2})
    if with_vix:
        x["vix"] = f["implied"] ** 2
    return x


def fit_predict_har(
    f: pd.DataFrame, split: Split, with_vix: bool = False
) -> tuple[pd.Series, np.ndarray]:
    """HAR-RV (Corsi, 2009) by OLS on variances; optional VIX^2 regressor (HAR-X).

    ``RV_fwd^2 = b0 + b_d RV_d^2 + b_w RV_w^2 + b_m RV_m^2 (+ b_v VIX^2)``
    The daily/weekly/monthly cascade mimics traders acting at different horizons.
    """
    x = _har_design(f, with_vix)
    y = f["rv_fwd"] ** 2
    train = x.loc[: split.train_end].join(y).dropna()
    beta, *_ = np.linalg.lstsq(train[x.columns].to_numpy(), train["rv_fwd"].to_numpy(), rcond=None)
    x_test = x.loc[split.test_start : split.test_end]
    var_hat = x_test.to_numpy() @ beta
    # OLS on variances can go (rarely) negative: floor at a 5% vol.
    pred = np.sqrt(np.maximum(var_hat, 0.05**2))
    return pd.Series(pred, index=x_test.index), beta


def fit_predict_lightgbm(
    f: pd.DataFrame, split: Split, params: dict[str, Any], seed: int
) -> tuple[pd.Series, Any]:
    """Gradient boosting on ``log(rv_fwd)``: the log tames the crisis outliers.

    ``exp(E[log y])`` underestimates ``E[y]`` (Jensen), so predictions are scaled by
    Duan's smearing factor ``mean(exp(residuals))``, computed on training data only.
    """
    import lightgbm as lgb

    train = f.loc[: split.train_end, [*LGBM_FEATURES, "rv_fwd"]].dropna()
    model = lgb.LGBMRegressor(**params, random_state=seed, n_jobs=1, verbose=-1)
    y_log = np.log(train["rv_fwd"])
    model.fit(train[LGBM_FEATURES], y_log)
    smearing = float(np.mean(np.exp(y_log - model.predict(train[LGBM_FEATURES]))))
    x_test = f.loc[split.test_start : split.test_end, LGBM_FEATURES]
    pred = smearing * np.exp(model.predict(x_test))
    return pd.Series(pred, index=x_test.index), model


def garch_forecasts(
    close: pd.Series, splits: list[Split], horizon: int, trading_days: int
) -> pd.Series:
    """GARCH(1,1) with Student-t innovations, refitted each year on past data only.

    ``sigma2_{t+1} = omega + alpha r_t^2 + beta sigma2_t``. Parameters are fitted
    on returns strictly before ``test_start`` (``last_obs``); inside the test year
    the filter runs with frozen parameters, each forecast using returns up to t.
    The 21-day forecast is the sum of the 1..21-step-ahead variances.
    """
    from arch import arch_model

    r = 100 * log_returns(close).dropna()  # percent returns: better numerical scaling
    am = arch_model(r, mean="Constant", vol="GARCH", p=1, q=1, dist="t")
    out = []
    for s in splits:
        res = am.fit(last_obs=s.test_start, disp="off")
        fc = res.forecast(horizon=horizon, start=s.test_start, reindex=False)
        var_h = fc.variance.loc[s.test_start : s.test_end].sum(axis=1)
        out.append(np.sqrt(var_h / horizon * trading_days) / 100)
    return pd.concat(out)


def run_walk_forward(f: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Out-of-sample forecasts of every model on every test year.

    Returns:
        ``(predictions, info)``: predictions has one column per model plus
        ``rv_fwd`` (target) and ``implied`` (VIX, for reference); ``info`` holds
        the last fitted HAR coefficients and LightGBM feature importances.
    """
    fc = cfg["forecast"]
    h = cfg["premium"]["horizon"]
    n = cfg["volatility"]["trading_days"]
    splits = list(walk_forward_splits(f.index, fc["first_test_year"], h))
    preds: dict[str, list[pd.Series]] = {"har": [], "har_x": [], "lightgbm": []}
    info: dict[str, Any] = {}
    for s in splits:
        logger.info("Walk-forward %d: train <= %s", s.year, s.train_end.date())
        p, beta = fit_predict_har(f, s)
        preds["har"].append(p)
        info["har_beta"] = beta
        p, beta_x = fit_predict_har(f, s, with_vix=True)
        preds["har_x"].append(p)
        info["har_x_beta"] = beta_x
        p, model = fit_predict_lightgbm(f, s, fc["lightgbm"], cfg["seed"])
        preds["lightgbm"].append(p)
        info["lgbm_model"] = model

    test = f.loc[splits[0].test_start :]
    out = pd.DataFrame(index=test.index)
    out["rv_fwd"] = test["rv_fwd"]
    out["implied"] = test["implied"]
    out["naive"] = test["rv"]
    for name, parts in preds.items():
        out[name] = pd.concat(parts)
    out["garch"] = garch_forecasts(f["spx_close"], splits, h, n)
    imp = info["lgbm_model"].booster_.feature_importance(importance_type="gain")
    info["lgbm_importance"] = pd.Series(imp / imp.sum(), index=LGBM_FEATURES).sort_values(
        ascending=False
    )
    return out, info


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def qlike(realized_var: np.ndarray, forecast_var: np.ndarray) -> float:
    """QLIKE loss ``mean(RV/h - ln(RV/h) - 1)``: 0 for a perfect forecast.

    Robust to noise in the realized proxy (Patton, 2011) and it penalises
    under-prediction more than over-prediction, which is what a risk manager wants.
    """
    ratio = realized_var / forecast_var
    return float(np.mean(ratio - np.log(ratio) - 1.0))


MODEL_NAMES = {
    "naive": "Naive (last 21 days)",
    "har": "HAR-RV",
    "garch": "GARCH(1,1)",
    "har_x": "HAR-RV + VIX",
    "lightgbm": "LightGBM",
    "implied": "VIX (market)",
}


def evaluate(preds: pd.DataFrame) -> pd.DataFrame:
    """RMSE / MAE (vol points) and QLIKE of each model on a common sample."""
    models = [m for m in MODEL_NAMES if m in preds.columns]
    d = preds.dropna(subset=["rv_fwd", *models])
    y = d["rv_fwd"].to_numpy()
    rows = []
    for m in models:
        p = d[m].to_numpy()
        err = 100 * (p - y)
        rows.append(
            {
                "model": m,
                "label": MODEL_NAMES[m],
                "rmse": float(np.sqrt(np.mean(err**2))),
                "mae": float(np.mean(np.abs(err))),
                "bias": float(np.mean(err)),
                "qlike": qlike(y**2, p**2),
            }
        )
    out = pd.DataFrame(rows).set_index("model")
    out["rmse_vs_naive"] = 100 * (out["rmse"] / out.loc["naive", "rmse"] - 1)
    out["qlike_vs_naive"] = 100 * (out["qlike"] / out.loc["naive", "qlike"] - 1)
    out.attrs["n_obs"] = len(d)
    out.attrs["start"] = str(d.index[0].date())
    out.attrs["end"] = str(d.index[-1].date())
    return out
