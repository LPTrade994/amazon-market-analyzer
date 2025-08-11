"""Filtering utilities for Deal Radar and Value Radar."""

from __future__ import annotations

from typing import Optional

import pandas as pd


def deal_radar(df: pd.DataFrame, min_flip: float = 0.0) -> pd.DataFrame:
    """Return rows matching hard gating for Deal Radar.

    Parameters
    ----------
    df:
        Input DataFrame.
    min_flip:
        Minimum flipability score required to pass the filter.
    """
    mask = df.get("bb_flip_30", pd.Series(0, index=df.index)) > min_flip
    return df[mask].copy()


def value_radar(
    df: pd.DataFrame, min_margin: float = 0.0, max_rank: Optional[float] = None
) -> pd.DataFrame:
    """Return rows passing Value Radar hard gates."""
    mask = df.get("margin", pd.Series(0, index=df.index)) > min_margin
    if max_rank is not None:
        mask &= df.get("rank_cur", pd.Series(float("inf"), index=df.index)) < max_rank
    return df[mask].copy()
