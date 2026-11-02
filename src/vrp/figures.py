"""Static PNG figures for the README (the website draws its own interactive charts)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # no display needed (CI, scripts)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

logger = logging.getLogger(__name__)

INK, MUTED, ACCENT, ORANGE = "#1D1D1F", "#86868B", "#0071E3", "#FF9F0A"


def _style(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#D2D2D7")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color="#F0F0F2", linewidth=0.8)
    ax.set_axisbelow(True)


def save_readme_figures(
    vrp: pd.DataFrame, preds: pd.DataFrame, backtest: dict[str, Any], out_dir: Path
) -> None:
    """Write ``vix_vs_realized.png`` and ``equity.png`` into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"]

    d = vrp.dropna(subset=["rv_fwd"])
    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    ax.plot(d.index, 100 * d["implied"], color=ACCENT, lw=0.9, label="VIX at t (implied)")
    ax.plot(d.index, 100 * d["rv_fwd"], color=ORANGE, lw=0.9, alpha=0.9,
            label="Realized vol over t+1..t+21")  # fmt: skip
    ax.set_ylabel("Annualised volatility (%)", color=MUTED, fontsize=9)
    ax.set_title("The market's forecast vs what happened next", loc="left", color=INK,
                 fontsize=12, fontweight="bold")  # fmt: skip
    ax.legend(frameon=False, fontsize=9, labelcolor=INK)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_dir / "vix_vs_realized.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    colors = {"always": MUTED, "har_x": ACCENT, "lightgbm": ORANGE}
    for key, strat in backtest["strategies"].items():
        c = strat["curve"]
        ax.plot(pd.to_datetime(c["dates"]), c["equity"], color=colors[key], lw=1.4,
                label=strat["label"])  # fmt: skip
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}x"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_ylabel("Equity (log scale, start = 1)", color=MUTED, fontsize=9)
    ax.set_title("Selling 1-month S&P 500 variance, 2010-2026", loc="left", color=INK,
                 fontsize=12, fontweight="bold")  # fmt: skip
    ax.legend(frameon=False, fontsize=9, labelcolor=INK)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_dir / "equity.png")
    plt.close(fig)
    logger.info("Saved README figures in %s", out_dir)
