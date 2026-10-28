"""Smoke tests: the config is valid and the helpers are reproducible."""

import numpy as np

from vrp.config import PROJECT_ROOT, load_config, resolve_path
from vrp.utils import set_seed


def test_config_has_required_sections() -> None:
    cfg = load_config()
    for key in ("seed", "data", "volatility", "web", "logging"):
        assert key in cfg


def test_volatility_parameters_are_sane() -> None:
    vol = load_config()["volatility"]
    assert vol["window"] > 1
    assert vol["trading_days"] == 252


def test_resolve_path_is_inside_repo() -> None:
    assert resolve_path("data/raw").is_relative_to(PROJECT_ROOT)


def test_set_seed_is_reproducible() -> None:
    a = set_seed(42).normal(size=5)
    b = set_seed(42).normal(size=5)
    np.testing.assert_array_equal(a, b)
