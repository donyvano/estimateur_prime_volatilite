"""Load the central YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Read the project configuration.

    Args:
        path: Path to a YAML file. Defaults to ``config/config.yaml``.

    Returns:
        The configuration as a nested dictionary.
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(relative: str | Path) -> Path:
    """Turn a path from the config (relative to the repo root) into an absolute path."""
    return PROJECT_ROOT / relative
