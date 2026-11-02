"""Step 6: features, walk-forward splits and metrics."""

import numpy as np
import pandas as pd
import pytest

from vrp.forecast import (
    LGBM_FEATURES,
    build_features,
    evaluate,
    fit_predict_har,
    qlike,
    walk_forward_splits,
)
from vrp.premium import build_vrp_frame


@pytest.fixture
def features(market: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    return build_features(build_vrp_frame(market, cfg), cfg)


def test_features_have_no_look_ahead(market: pd.DataFrame, cfg: dict) -> None:
    t = 500
    base = build_features(build_vrp_frame(market, cfg), cfg)
    shocked_mkt = market.copy()
    shocked_mkt.iloc[t + 1 :, :4] *= 0.7
    shocked_mkt.iloc[t + 1 :, 4] *= 2
    shocked = build_features(build_vrp_frame(shocked_mkt, cfg), cfg)
    pd.testing.assert_frame_equal(
        base[LGBM_FEATURES].iloc[: t + 1], shocked[LGBM_FEATURES].iloc[: t + 1]
    )


def test_splits_are_purged_and_ordered(features: pd.DataFrame) -> None:
    idx = features.index
    splits = list(walk_forward_splits(idx, 2016, horizon=21))
    assert [s.year for s in splits] == sorted({y for y in idx.year if y >= 2016})
    for s in splits:
        # the target of the last training row ends strictly before the test year
        last_target_day = idx[idx.get_loc(s.train_end) + 21]
        assert last_target_day < s.test_start
        assert s.test_start.year == s.year == s.test_end.year


def test_har_predictions_are_out_of_sample_and_positive(features: pd.DataFrame) -> None:
    split = next(walk_forward_splits(features.index, 2017, 21))
    pred, beta = fit_predict_har(features, split)
    assert pred.index.min() == split.test_start
    assert (pred > 0).all()
    assert len(beta) == 4


def test_har_ignores_training_targets_after_train_end(features: pd.DataFrame) -> None:
    split = next(walk_forward_splits(features.index, 2017, 21))
    pred, _ = fit_predict_har(features, split)
    leaked = features.copy()
    leaked.loc[leaked.index > split.train_end, "rv_fwd"] = 5.0  # absurd future targets
    pred2, _ = fit_predict_har(leaked, split)
    pd.testing.assert_series_equal(pred, pred2)


def test_qlike_properties() -> None:
    rv = np.array([0.04, 0.09])
    assert qlike(rv, rv) == pytest.approx(0.0)
    assert qlike(rv, rv * 1.2) > 0
    # under-prediction is penalised more than over-prediction of the same size
    assert qlike(rv, rv * 0.8) > qlike(rv, rv * 1.2)


def test_evaluate_ranks_perfect_model_first() -> None:
    idx = pd.bdate_range("2020-01-01", periods=50)
    y = pd.Series(np.linspace(0.1, 0.3, 50), index=idx)
    preds = pd.DataFrame({"rv_fwd": y, "naive": y * 1.3, "har": y, "implied": y + 0.03})
    m = evaluate(preds)
    assert m.loc["har", "rmse"] == pytest.approx(0.0)
    assert m.loc["har", "rmse_vs_naive"] == pytest.approx(-100.0)
