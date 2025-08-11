"""Helpers for computing profit and cost structures."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .columns import parse_euro


def fbm_profit(price: float, cost: float, shipping: float = 0.0) -> float:
    """Compute profit for a Fulfilled By Merchant (FBM) item."""
    return float(price) - float(cost) - float(shipping)


def fba_profit(price: float, cost: float, fees: float = 0.0) -> float:
    """Placeholder for Fulfilled By Amazon (FBA) profit calculation."""
    return float(price) - float(cost) - float(fees)


def compute_profit(row: Dict[str, Any], method: str = "FBM") -> float:
    """Compute profit for ``row`` using ``method``.

    ``row`` is expected to contain at least ``bb_now`` and ``cost`` columns.
    ``method`` can be ``FBM`` (default) or ``FBA``.
    """
    price = parse_euro(row.get("bb_now"))
    cost = parse_euro(row.get("cost", 0))
    shipping = parse_euro(row.get("shipping", 0))
    fees = parse_euro(row.get("fba_pickpack_fee", 0)) + parse_euro(
        row.get("referral_fee_amount", 0)
    )
    if method.upper() == "FBA":
        return fba_profit(price, cost, fees)
    return fbm_profit(price, cost, shipping)


def profit_series(df: pd.DataFrame, method: str = "FBM") -> pd.Series:
    """Return a series with profit for each row in ``df``."""
    return df.apply(lambda r: compute_profit(r, method=method), axis=1)
