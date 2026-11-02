"""Export helpers produce valid, compact JSON."""

import json

import numpy as np
import pandas as pd

from vrp.export import _clean, series_payload, write_json


def test_clean_handles_nan_numpy_and_dates() -> None:
    out = _clean({"a": np.float64(1.234567), "b": float("nan"), "c": pd.Timestamp("2024-01-02"),
                  "d": np.int64(3), "e": [np.inf]})  # fmt: skip
    assert out == {"a": 1.2346, "b": None, "c": "2024-01-02", "d": 3, "e": [None]}


def test_series_payload_and_write(tmp_path) -> None:  # noqa: ANN001
    df = pd.DataFrame({"x": [0.1, np.nan]}, index=pd.bdate_range("2024-01-01", periods=2))
    path = tmp_path / "s.json"
    write_json(series_payload(df, ["x"], scale=100), path)
    data = json.loads(path.read_text())
    assert data == {"dates": ["2024-01-01", "2024-01-02"], "x": [10.0, None]}
