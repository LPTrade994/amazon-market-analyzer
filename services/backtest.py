"""Backtesting utilities for historical arbitrage analysis."""
from __future__ import annotations

from typing import Iterable, List, Tuple, Dict, Any

import pandas as pd

from settings import VAT_RATES

# Simplified shipping cost per locale (flat cost in EUR)
SHIPPING_COSTS: Dict[str, float] = {
    "IT": 0.0,
    "FR": 0.0,
    "DE": 0.0,
    "ES": 0.0,
    "UK": 0.0,
}


def backtest_opportunities(
    df_all: pd.DataFrame,
    base_locale: str,
    target_locales: Iterable[str],
    discount_pct: float,
    min_profit_eur: float,
    min_margin_pct: float,
    max_sales_rank: int,
    start_date: Any | None = None,
    end_date: Any | None = None,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Evaluate historical arbitrage opportunities.

    Parameters
    ----------
    df_all:
        DataFrame containing concatenated historical exports. Must include the
        columns ``snapshot_date``, ``ASIN``, ``Locale`` and price/rank fields.
    base_locale:
        Locale from which the product would be purchased.
    target_locales:
        Locales in which the product would be resold.
    discount_pct:
        Discount applied to the purchase price (percentage).
    min_profit_eur:
        Minimum absolute profit to keep a row.
    min_margin_pct:
        Minimum profit margin percentage to keep a row.
    max_sales_rank:
        Maximum allowed sales rank for both base and target markets.
    start_date, end_date:
        Optional date range filters.

    Returns
    -------
    Tuple[pd.DataFrame, List[Dict[str, Any]]]
        Detailed results and aggregate statistics.
    """

    if df_all is None or df_all.empty:
        return pd.DataFrame(), []

    df = df_all.copy()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])

    if start_date is not None:
        df = df[df["snapshot_date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df["snapshot_date"] <= pd.to_datetime(end_date)]

    locs = {base_locale.lower()} | {loc.lower() for loc in target_locales}
    df = df[df["Locale"].str.lower().isin(locs)]

    price_col = "Price_BuyBox_New" if "Price_BuyBox_New" in df.columns else "Price_Amazon_New"
    df["price"] = pd.to_numeric(df[price_col], errors="coerce")
    df["sales_rank"] = pd.to_numeric(df["Sales_Rank_Current"], errors="coerce")

    results: List[pd.DataFrame] = []
    base_code = base_locale.upper()
    discount_factor = 1 - (discount_pct / 100.0)
    shipping_cost = SHIPPING_COSTS.get(base_code, 0.0)
    vat_rate = VAT_RATES.get(base_code, 0) / 100.0

    df_base = df[df["Locale"].str.lower() == base_locale.lower()][
        ["snapshot_date", "ASIN", "price", "sales_rank"]
    ].rename(columns={"price": "price_buy_base", "sales_rank": "sales_rank_base"})

    for tgt in target_locales:
        df_tgt = df[df["Locale"].str.lower() == tgt.lower()][
            ["snapshot_date", "ASIN", "price", "sales_rank"]
        ].rename(columns={"price": "sell_price_target", "sales_rank": "sales_rank_target"})

        merged = pd.merge(df_base, df_tgt, on=["snapshot_date", "ASIN"], how="inner")
        if merged.empty:
            continue
        merged["target_locale"] = tgt.lower()
        merged["base_locale"] = base_locale.lower()

        landed = merged["price_buy_base"] * discount_factor
        landed *= 1 + vat_rate
        landed += shipping_cost
        merged["landed_cost_base"] = landed

        merged["potential_profit_eur"] = merged["sell_price_target"] - merged["landed_cost_base"]
        merged["margin_pct"] = (
            merged["potential_profit_eur"] / merged["landed_cost_base"] * 100
        )

        cond = (
            (merged["potential_profit_eur"] >= min_profit_eur)
            & (merged["margin_pct"] >= min_margin_pct)
            & (merged["sales_rank_base"] <= max_sales_rank)
            & (merged["sales_rank_target"] <= max_sales_rank)
        )
        merged = merged[cond]
        results.append(merged)

    if results:
        df_results = pd.concat(results, ignore_index=True)
    else:
        df_results = pd.DataFrame(
            columns=[
                "snapshot_date",
                "ASIN",
                "base_locale",
                "target_locale",
                "price_buy_base",
                "landed_cost_base",
                "sell_price_target",
                "potential_profit_eur",
                "margin_pct",
                "sales_rank_base",
                "sales_rank_target",
            ]
        )

    stats_df = (
        df_results.groupby(["ASIN", "target_locale"])
        .agg(
            occurrences=("snapshot_date", "count"),
            avg_profit_eur=("potential_profit_eur", "mean"),
            avg_margin_pct=("margin_pct", "mean"),
            first_seen=("snapshot_date", "min"),
            last_seen=("snapshot_date", "max"),
        )
        .reset_index()
    )

    stats = stats_df.to_dict(orient="records")
    return df_results, stats
