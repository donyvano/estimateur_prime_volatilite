"""Download and cache market data (S&P 500, SPY, VIX, T-bill rate, SPY option chain). Step 1.

Every download is cached as parquet in ``data/raw`` so that the analysis is
reproducible offline and Yahoo Finance is not hammered at each run.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from vrp.config import resolve_path

logger = logging.getLogger(__name__)

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


# ---------------------------------------------------------------------------
# Daily prices
# ---------------------------------------------------------------------------
def _cache_name(ticker: str) -> str:
    """'^GSPC' -> 'GSPC' (carets are awkward in file names)."""
    return ticker.replace("^", "").replace("/", "_")


def download_prices(ticker: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Download daily OHLCV prices from Yahoo Finance.

    Args:
        ticker: Yahoo ticker, e.g. ``"^GSPC"``.
        start: First date (inclusive), ``"YYYY-MM-DD"``.
        end: Last date (exclusive). ``None`` means today.

    Returns:
        DataFrame indexed by date with lowercase columns ``PRICE_COLUMNS``.
    """
    import yfinance as yf  # imported lazily: tests never hit the network

    logger.info("Downloading %s from %s", ticker, start)
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        multi_level_index=False,
    )
    if raw.empty:
        raise RuntimeError(f"No data returned by Yahoo Finance for {ticker}")
    df = raw.rename(columns=lambda c: str(c).lower().replace(" ", "_"))
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    return df[[c for c in PRICE_COLUMNS if c in df.columns]]


def clean_prices(df: pd.DataFrame, is_rate: bool = False) -> pd.DataFrame:
    """Sort, drop duplicated dates, rows without a close and non-positive prices.

    Interest rates (``is_rate=True``) can legitimately be zero or negative: they are kept.
    """
    out = df.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out.dropna(subset=["close"])
    price_cols = [c for c in ("open", "high", "low", "close", "adj_close") if c in out.columns]
    bad = (out[price_cols] <= 0).any(axis=1)
    if bad.any() and not is_rate:
        logger.warning("Dropping %d rows with non-positive prices", int(bad.sum()))
        out = out[~bad]
    return out


def validate_prices(
    df: pd.DataFrame, name: str, max_gap_days: int = 5, is_rate: bool = False
) -> None:
    """Sanity checks on a cleaned price frame. Raises ``ValueError`` if one fails.

    Checks: strictly increasing dates, positive prices, ``low <= close <= high``
    and no gap longer than ``max_gap_days`` calendar days between two trading days
    (the longest legitimate one since 2005 is Hurricane Sandy: Fri -> Wed, 5 days).
    """
    if df.empty:
        raise ValueError(f"{name}: empty price frame")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError(f"{name}: dates are not strictly increasing")
    if not is_rate and (df["close"] <= 0).any():
        raise ValueError(f"{name}: non-positive close prices")
    if not is_rate and {"high", "low"} <= set(df.columns):
        # Yahoo rounds a few OHLC values: tolerate 0.5% before failing.
        tol = 5e-3 * df["close"]
        inconsistent = (df["low"] > df["close"] + tol) | (df["high"] < df["close"] - tol)
        if inconsistent.any():
            n_bad = int(inconsistent.sum())
            raise ValueError(f"{name}: {n_bad} rows with close outside [low, high]")
    gaps = df.index.to_series().diff().dt.days.dropna()
    if (gaps > max_gap_days).any():
        worst = gaps.idxmax()
        raise ValueError(f"{name}: {int(gaps.max())}-day gap in the data ending {worst.date()}")


def load_prices(
    ticker: str, cfg: dict[str, Any], refresh: bool = False, is_rate: bool = False
) -> pd.DataFrame:
    """Return clean, validated daily prices, from the parquet cache when available."""
    data_cfg = cfg["data"]
    path = resolve_path(data_cfg["raw_dir"]) / f"{_cache_name(ticker)}.parquet"
    if path.exists() and not refresh:
        logger.info("Loading %s from cache %s", ticker, path.name)
        df = pd.read_parquet(path)
    else:
        df = download_prices(ticker, data_cfg["start_date"], data_cfg["end_date"])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
    df = clean_prices(df, is_rate)
    validate_prices(df, ticker, data_cfg["max_gap_days"], is_rate)
    return df


def load_market_data(cfg: dict[str, Any], refresh: bool = False) -> pd.DataFrame:
    """Daily frame with S&P 500 OHLC, VIX close and risk-free rate on common dates.

    Columns: ``spx_open, spx_high, spx_low, spx_close, vix, rate`` (rate in decimals).
    """
    d = cfg["data"]
    spx = load_prices(d["index_ticker"], cfg, refresh)
    vix = load_prices(d["vix_ticker"], cfg, refresh)
    rate = load_prices(d["rate_ticker"], cfg, refresh, is_rate=True)

    df = spx[["open", "high", "low", "close"]].add_prefix("spx_")
    df = df.join(vix["close"].rename("vix"), how="inner")
    # T-bill yields are missing on a few bond-market holidays: carry the last value
    # forward (past information only, no look-ahead).
    df = df.join((rate["close"] / 100).rename("rate"), how="left")
    df["rate"] = df["rate"].ffill()
    logger.info(
        "Market data: %d days from %s to %s", len(df), df.index[0].date(), df.index[-1].date()
    )
    return df


# ---------------------------------------------------------------------------
# Option chain snapshot
# ---------------------------------------------------------------------------
def download_option_chain(ticker: str, max_days: int) -> pd.DataFrame:
    """Download today's full option chain (calls and puts) up to ``max_days`` maturity."""
    import yfinance as yf

    tk = yf.Ticker(ticker)
    today = pd.Timestamp(date.today())
    spot = float(tk.history(period="5d")["Close"].iloc[-1])
    frames = []
    for expiry in tk.options:
        exp = pd.Timestamp(expiry)
        if (exp - today).days > max_days:
            break
        chain = tk.option_chain(expiry)
        for option_type, table in (("call", chain.calls), ("put", chain.puts)):
            t = table.copy()
            t["type"] = option_type
            t["expiry"] = exp
            frames.append(t)
    logger.info("Downloaded %d expiries for %s (spot %.2f)", len(frames) // 2, ticker, spot)
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(
        columns={
            "lastPrice": "last",
            "openInterest": "open_interest",
            "impliedVolatility": "yahoo_iv",
            "lastTradeDate": "last_trade",
        }
    )
    df["snapshot_date"] = today
    df["spot"] = spot
    cols = ["snapshot_date", "spot", "expiry", "type", "strike", "bid", "ask", "last",
            "volume", "open_interest", "yahoo_iv", "last_trade"]  # fmt: skip
    df = df[cols]
    df["last_trade"] = pd.to_datetime(df["last_trade"], utc=True).dt.tz_localize(None)
    return df


def _latest_snapshot(raw_dir: Path, ticker: str) -> Path | None:
    files = sorted(raw_dir.glob(f"options_{_cache_name(ticker)}_*.parquet"))
    return files[-1] if files else None


def load_option_chain(cfg: dict[str, Any], refresh: bool = False) -> pd.DataFrame:
    """Return the most recent cached option chain snapshot, downloading one if needed.

    Snapshots are stored as ``options_SPY_YYYY-MM-DD.parquet`` and never overwritten,
    so the surface shown on the website is always tied to a dated file.
    """
    d = cfg["data"]
    raw_dir = resolve_path(d["raw_dir"])
    path = _latest_snapshot(raw_dir, d["options_ticker"])
    if path is None or refresh:
        df = download_option_chain(d["options_ticker"], d["options_max_days"])
        stamp = datetime.now().strftime("%Y-%m-%d")
        path = raw_dir / f"options_{_cache_name(d['options_ticker'])}_{stamp}.parquet"
        raw_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
    else:
        logger.info("Loading option chain from cache %s", path.name)
        df = pd.read_parquet(path)
    for col in ("bid", "ask", "last", "volume", "open_interest"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df["volume"] = df["volume"].fillna(0.0)
    df["open_interest"] = df["open_interest"].fillna(0.0)
    if (df["strike"] <= 0).any() or not np.isfinite(df["spot"]).all():
        raise ValueError("Option chain: invalid strikes or spot")
    return df
