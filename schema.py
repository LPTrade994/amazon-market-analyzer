"""Data schema utilities for normalizing Keepa/price exports."""

from __future__ import annotations

import math
import re
from typing import Any, Dict

import pandas as pd


EURO_SYMBOLS = {"€"}


def parse_eu_price(x: Any) -> float:
    """Parse an European-formatted price into ``float``.

    Removes currency symbols and spaces, drops thousand separators ``.`` and
    converts decimal commas to dots. Returns ``math.nan`` on failure.
    """
    if x is None:
        return math.nan
    if isinstance(x, (int, float)):
        return float(x)
    try:
        s = str(x)
        for sym in EURO_SYMBOLS:
            s = s.replace(sym, "")
        s = s.replace("\u202f", "").replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        s = s.strip()
        if not s:
            return math.nan
        return float(s)
    except Exception:
        return math.nan


def parse_percent(x: Any) -> float:
    """Parse percentages like ``"7,00 %"`` into ``float`` (7.0)."""
    if x is None:
        return math.nan
    if isinstance(x, (int, float)):
        return float(x)
    try:
        s = str(x)
        s = s.replace("%", "")
        s = s.replace("\u202f", "").replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        s = s.strip()
        if not s:
            return math.nan
        return float(s)
    except Exception:
        return math.nan


def parse_bool(x: Any) -> bool:
    """Parse various textual representations into ``bool``.

    Accepts ``yes/no``, ``si/no``, ``true/false`` (case-insensitive). Empty
    strings are treated as ``False``.
    """
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if not s:
        return False
    if s in {"yes", "si", "true", "1", "y", "t"}:
        return True
    if s in {"no", "false", "0", "n", "f"}:
        return False
    return False


# Helper to normalise column names for mapping
_normalise_re = re.compile(r"\s+")

def _norm(col: str) -> str:
    col = col.replace("🚚", "")
    col = _normalise_re.sub(" ", col).strip().casefold()
    return col


COLUMN_MAP: Dict[str, str] = {
    # Base fields
    "locale": "locale",
    "title": "title",
    "asin": "asin",
    "parent asin": "parent_asin",
    "brand": "brand",
    "url: amazon": "url_amazon",
    "url: keepa": "url_keepa",
    "categories: root": "cat_root",
    "categories: sub": "cat_sub",
    # Rank & volume
    "sales rank: current": "rank_now",
    "sales rank: 30 days avg.": "rank_30d",
    "sales rank: 90 days avg.": "rank_90d",
    "sales rank: 180 days avg.": "rank_180d",
    "sales rank: 365 days avg.": "rank_365d",
    "sales rank: 30 days drop %": "rank_drop_30d_pct",
    "sales rank: 90 days drop %": "rank_drop_90d_pct",
    "sales rank: drops last 30 days": "rank_drops_30d",
    "sales rank: drops last 90 days": "rank_drops_90d",
    "bought in past month": "bought_30d",
    # Buy Box 🚚 prices
    "buy box : current": "bb_now",
    "buy box : 30 days avg.": "bb_30d",
    "buy box : 90 days avg.": "bb_90d",
    "buy box : 180 days avg.": "bb_180d",
    "buy box : 365 days avg.": "bb_365d",
    "buy box : 30 days drop %": "bb_drop_30d_pct",
    "buy box : is lowest": "bb_is_lowest",
    "buy box : lowest": "bb_lowest",
    "buy box : highest": "bb_highest",
    "buy box : 90 days oos": "bb_oos_90d",
    # Amazon dominance / competition
    "buy box: % amazon 30 days": "bb_amz_pct_30d",
    "buy box: % amazon 90 days": "bb_amz_pct_90d",
    "buy box: % amazon 180 days": "bb_amz_pct_180d",
    "buy box: % amazon 365 days": "bb_amz_pct_365d",
    "buy box: winner count 30 days": "bb_winners_30d",
    "buy box: winner count 90 days": "bb_winners_90d",
    "buy box: standard deviation 30 days": "bb_std_30d",
    "buy box: standard deviation 90 days": "bb_std_90d",
    "buy box: standard deviation 365 days": "bb_std_365d",
    "buy box: flipability 30 days": "bb_flip_30d",
    "buy box: flipability 90 days": "bb_flip_90d",
    "buy box: flipability 365 days": "bb_flip_365d",
    "buy box: unqualified": "bb_unqualified",
    # Amazon & New prices
    "amazon: current": "amz_now",
    "amazon: 30 days avg.": "amz_30d",
    "amazon: 90 days avg.": "amz_90d",
    "amazon: 180 days avg.": "amz_180d",
    "amazon: 365 days avg.": "amz_365d",
    "amazon: is lowest": "amz_is_lowest",
    "amazon: lowest": "amz_lowest",
    "amazon: highest": "amz_highest",
    "amazon: 90 days oos": "amz_oos_90d",
    "amazon: oos count 30 days": "amz_oos_30d",
    "amazon: oos count 90 days": "amz_oos_90d",
    "amazon: availability of the amazon offer": "amz_availability",
    "amazon: amazon offer shipping delay": "amz_ship_delay",
    "new: current": "new_now",
    "new: 30 days avg.": "new_30d",
    "new: 90 days avg.": "new_90d",
    "new: 180 days avg.": "new_180d",
    "new: 365 days avg.": "new_365d",
    "new: is lowest": "new_is_lowest",
    "new: lowest": "new_lowest",
    "new: highest": "new_highest",
    "new, 3rd party fba: current": "fba_3p_now",
    "new, 3rd party fbm : current": "fbm_3p_now",
    # Fees & offers
    "fba pick&pack fee": "fba_pickpack_fee",
    "referral fee %": "referral_fee_pct",
    "referral fee based on current buy box price": "referral_fee_on_bb",
    "new offer count: current": "offer_new_now",
    "new offer count: 30 days avg.": "offer_new_30d",
    "used offer count: current": "offer_used_now",
    "total offer count": "offer_count_total",
    # Quality & coupons
    "return rate": "return_rate_pct",
    "reviews: rating": "rating",
    "reviews: rating count": "rating_count",
    "one time coupon: absolute": "coupon_abs",
    "one time coupon: percentage": "coupon_pct",
    "business discount: percentage": "biz_discount_pct",
    "prime eligible (buy box)": "prime_bb",
    # Dimensions / weight
    "package: dimension (cm³)": "pack_cm3",
    "package: length (cm)": "pack_l_cm",
    "package: width (cm)": "pack_w_cm",
    "package: height (cm)": "pack_h_cm",
    "package: weight (g)": "pack_g",
    "item: weight (g)": "item_g",
    # Dates
    "last update": "last_update",
    "last price change": "last_price_change",
}


STRING_COLS = {
    "locale",
    "title",
    "asin",
    "parent_asin",
    "brand",
    "url_amazon",
    "url_keepa",
    "cat_root",
    "cat_sub",
    "amz_availability",
    "amz_ship_delay",
}

BOOLEAN_COLS = {"bb_is_lowest", "amz_is_lowest", "new_is_lowest", "bb_unqualified", "prime_bb"}

DATE_COLS = {"last_update", "last_price_change"}


def validate_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, parse values and derive helper metrics."""
    if df is None:
        return df
    df = df.copy()

    rename_map = {}
    for col in df.columns:
        norm = _norm(col)
        if norm in COLUMN_MAP:
            rename_map[col] = COLUMN_MAP[norm]
    df = df.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]

    # Ensure all expected columns exist
    for col in set(COLUMN_MAP.values()):
        if col not in df.columns:
            df[col] = pd.NA

    percent_cols = [c for c in df.columns if c.endswith("_pct")]

    # Parse values
    for col in percent_cols:
        df[col] = df[col].map(parse_percent)

    for col in BOOLEAN_COLS:
        if col in df:
            df[col] = df[col].map(parse_bool)

    for col in DATE_COLS:
        if col in df:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        c
        for c in df.columns
        if c not in STRING_COLS
        and c not in BOOLEAN_COLS
        and c not in percent_cols
        and c not in DATE_COLS
    ]
    for col in numeric_cols:
        df[col] = df[col].map(parse_eu_price)

    # Derived metrics
    if "pack_cm3" in df.columns:
        df["volume_cm3"] = df["pack_cm3"]
    else:
        df["volume_cm3"] = pd.NA
    if {"pack_l_cm", "pack_w_cm", "pack_h_cm"}.issubset(df.columns):
        prod = df["pack_l_cm"] * df["pack_w_cm"] * df["pack_h_cm"]
        df["volume_cm3"] = df["volume_cm3"].fillna(prod)

    weights = []
    if "item_g" in df.columns:
        weights.append(df["item_g"])
    if "pack_g" in df.columns:
        weights.append(df["pack_g"])
    if weights:
        df["weight_kg"] = pd.concat(weights, axis=1).max(axis=1) / 1000.0
    else:
        df["weight_kg"] = pd.NA

    if "locale" in df.columns:
        df["locale"] = (
            df["locale"].astype(str).str.extract(r"([A-Za-z]{2})", expand=False).str.upper()
        )

    return df
