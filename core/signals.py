"""Derived signal calculations used within the analyzer."""

from __future__ import annotations

import math
from typing import Any, Optional

import pandas as pd


def z_score(series: pd.Series) -> pd.Series:
    """Return the z-score for ``series`` ignoring ``NaN`` values."""
    mean = series.mean()
    std = series.std(ddof=0)
    if std == 0 or math.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def delta_pct(current: pd.Series, previous: pd.Series) -> pd.Series:
    """Return the percentage change between ``current`` and ``previous``."""
    return (current - previous) / previous.replace(0, pd.NA)


def review_momentum(df: pd.DataFrame) -> pd.Series:
    """Compute review momentum from rating counts.

    The metric is defined as the z-score of the difference between the
    current rating count and the 30 day average.
    """
    diff = df.get("rating_count", pd.Series(dtype=float)) - df.get(
        "rating_count_avg_30", pd.Series(dtype=float)
    )
    return z_score(diff.fillna(0))


def amazon_hazard(df: pd.DataFrame) -> pd.Series:
    """Return a simple hazard score based on Amazon's presence.

    A value of ``1`` indicates Amazon is in the buy box now, ``0`` otherwise.
    Missing data results in ``0``.
    """
    now = df.get("amazon_now")
    if now is None:
        return pd.Series(0, index=df.index)
    return now.notna().astype(int)


def flipability_score(df: pd.DataFrame, window: str = "30") -> pd.Series:
    """Estimate how "flipable" an item is based on Buy Box standard deviation.

    The higher the standard deviation relative to the mean, the more
    opportunities there might be to flip.
    """
    std_col = f"bb_std_{window}"
    mean_col = f"bb_avg_{window}"
    std = df.get(std_col, pd.Series(dtype=float))
    mean = df.get(mean_col, pd.Series(dtype=float))
    return (std / mean.replace(0, pd.NA)).fillna(0)
