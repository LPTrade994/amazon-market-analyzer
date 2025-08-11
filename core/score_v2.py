"""Second generation scoring model with granular sub-scores."""

from __future__ import annotations

from typing import Dict

import pandas as pd

SUBSCORES = ["P", "L", "E", "C", "A", "Q", "X"]

def _scale(series: pd.Series) -> pd.Series:
    """Normalize ``series`` to a 0-100 range."""
    min_val = series.min()
    max_val = series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val) * 100

def compute_subscores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute placeholder P/L/E/C/A/Q/X subscores."""
    df = df.copy()
    df["P"] = _scale(df.get("profit", pd.Series(0, index=df.index)))
    df["L"] = _scale(df.get("liquidity", pd.Series(0, index=df.index)))
    df["E"] = _scale(df.get("efficiency", pd.Series(0, index=df.index)))
    df["C"] = _scale(df.get("competition", pd.Series(0, index=df.index)))
    df["A"] = _scale(df.get("availability", pd.Series(0, index=df.index)))
    df["Q"] = _scale(df.get("quality", pd.Series(0, index=df.index)))
    df["X"] = _scale(df.get("extra", pd.Series(0, index=df.index)))
    return df

def combine_opportunity(df: pd.DataFrame, weights: Dict[str, float] | None = None) -> pd.DataFrame:
    """Combine subscores into a single Opp2 score."""
    df = compute_subscores(df)
    weights = weights or {k: 1.0 for k in SUBSCORES}
    score = sum(df[k] * weights.get(k, 1.0) for k in SUBSCORES)
    df["Opp2"] = score / sum(weights.get(k, 1.0) for k in SUBSCORES)
    return df
