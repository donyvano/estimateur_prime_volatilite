"""Shared helpers: logging setup and reproducibility."""

from __future__ import annotations

import logging
import random

import numpy as np

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger once for scripts and notebooks."""
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt="%H:%M:%S", force=True)


def set_seed(seed: int) -> np.random.Generator:
    """Fix Python and NumPy seeds and return a dedicated NumPy generator."""
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)
