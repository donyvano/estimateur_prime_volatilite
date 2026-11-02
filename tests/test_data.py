"""Step 1: cleaning and sanity checks (offline, synthetic frames)."""

import pandas as pd
import pytest

from vrp.data import clean_prices, validate_prices


def _frame(closes: list[float], dates: list[str] | None = None) -> pd.DataFrame:
    idx = pd.to_datetime(dates) if dates else pd.bdate_range("2024-01-01", periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c})


def test_clean_drops_non_positive_and_duplicates() -> None:
    df = _frame([100, 0, 101, 102], ["2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04"])
    out = clean_prices(df)
    assert (out["close"] > 0).all()
    assert not out.index.has_duplicates


def test_clean_keeps_zero_rates() -> None:
    df = _frame([0.0, 0.01, 0.02])
    assert len(clean_prices(df, is_rate=True)) == 3


def test_clean_sorts_dates() -> None:
    df = _frame([1, 2, 3], ["2024-01-04", "2024-01-02", "2024-01-03"])
    assert clean_prices(df).index.is_monotonic_increasing


def test_validate_accepts_clean_data() -> None:
    validate_prices(_frame([100, 101, 99, 102]), "ok")


def test_validate_rejects_negative_prices() -> None:
    with pytest.raises(ValueError, match="non-positive"):
        validate_prices(_frame([100, -1, 101]), "neg")


def test_validate_rejects_large_gap() -> None:
    df = _frame([100, 101, 102], ["2024-01-02", "2024-01-03", "2024-01-20"])
    with pytest.raises(ValueError, match="gap"):
        validate_prices(df, "gap", max_gap_days=5)


def test_validate_rejects_close_outside_range() -> None:
    df = _frame([100, 101, 102])
    df.loc[df.index[1], "high"] = 90
    with pytest.raises(ValueError, match="outside"):
        validate_prices(df, "ohlc")
