"""Export results as JSON for the static website in web/data/. Step 5+.

The website never computes anything: it only reads these files. Floats are
rounded to keep the payload small (the full daily history is ~300 kB).
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _clean(value: Any, digits: int = 4) -> Any:
    """Recursively make a value JSON-safe: NaN -> None, numpy -> Python, rounding."""
    if isinstance(value, dict):
        return {str(k): _clean(v, digits) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_clean(v, digits) for v in value]
    if isinstance(value, np.ndarray):
        return _clean(value.tolist(), digits)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    if isinstance(value, np.integer | bool | np.bool_):
        return value.item() if hasattr(value, "item") else value
    if isinstance(value, float | np.floating):
        v = float(value)
        return None if math.isnan(v) or math.isinf(v) else round(v, digits)
    return value


def series_payload(df: pd.DataFrame, columns: list[str], scale: float = 1.0) -> dict[str, Any]:
    """Column-oriented payload ``{"dates": [...], col: [...]}`` (compact for charts)."""
    out: dict[str, Any] = {"dates": [str(d.date()) for d in df.index]}
    for c in columns:
        out[c] = (scale * df[c]).tolist()
    return out


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Row-oriented payload for tables."""
    return (
        df.reset_index().to_dict(orient="records")
        if df.index.name
        else df.to_dict(orient="records")
    )


def write_json(payload: dict[str, Any], path: Path, digits: int = 4) -> None:
    """Write a JSON file (UTF-8, no spaces) and log its size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_clean(payload, digits), ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    logger.info("Wrote %s (%.0f kB)", path.name, len(text) / 1024)
