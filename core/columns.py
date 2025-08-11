"""Column utilities and canonical mapping for datasets."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict

import pandas as pd

# Mapping from raw dataset headers (regex) to canonical snake_case names
CANONICAL_MAP: Dict[str, str] = {
    r"^Locale$": "locale",
    r"^Title$": "title",
    r"^ASIN$": "asin",
    r"^Parent ASIN$": "parent_asin",
    r"^Brand$": "brand",
    r"^Categories: Root$": "category_root",
    r"^Categories: Sub$": "category_sub",
    r"^Sales Rank: Current$": "rank_cur",
    r"^Sales Rank: 30 days avg\.": "rank_avg_30",
    r"^Sales Rank: 90 days avg\.": "rank_avg_90",
    r"^Sales Rank: 180 days avg\.": "rank_avg_180",
    r"^Sales Rank: 365 days avg\.": "rank_avg_365",
    r"^Sales Rank: 30 days drop %$": "rank_drop_pct_30",
    r"^Sales Rank: 90 days drop %$": "rank_drop_pct_90",
    r"^Sales Rank: Drops last 30 days$": "rank_drops_30",
    r"^Sales Rank: Drops last 90 days$": "rank_drops_90",
    r"^Bought in past month$": "bought_month",
    r"^90 days change % monthly sold$": "sold_change_pct_90",
    r"^Return Rate$": "return_rate",
    r"^Reviews: Rating$": "rating_value",
    r"^Reviews: Rating Count$": "rating_count",
    r"^Reviews: Rating Count - 30 days avg\.": "rating_count_avg_30",
    r"^Reviews: Rating Count - 90 days avg\.": "rating_count_avg_90",
    r"^Last Price Change$": "last_price_change",
    r"^Last Update$": "last_update",
    r"^Buy Box .*: Current$": "bb_now",
    r"^Buy Box .*: 30 days avg\.": "bb_avg_30",
    r"^Buy Box .*: 90 days avg\.": "bb_avg_90",
    r"^Buy Box .*: 180 days avg\.": "bb_avg_180",
    r"^Buy Box .*: 365 days avg\.": "bb_avg_365",
    r"^Buy Box .*: 30 days drop %$": "bb_drop_pct_30",
    r"^Buy Box .*: Is Lowest$": "bb_is_lowest",
    r"^Buy Box .*: Lowest$": "bb_lowest",
    r"^Buy Box .*: Highest$": "bb_highest",
    r"^Buy Box .*: 90 days OOS$": "bb_oos_pct_90",
    r"^Buy Box: % Amazon 30 days$": "bb_amz_pct_30",
    r"^Buy Box: % Amazon 90 days$": "bb_amz_pct_90",
    r"^Buy Box: % Amazon 180 days$": "bb_amz_pct_180",
    r"^Buy Box: % Amazon 365 days$": "bb_amz_pct_365",
    r"^Buy Box: Winner Count 30 days$": "bb_winner_count_30",
    r"^Buy Box: Winner Count 90 days$": "bb_winner_count_90",
    r"^Buy Box: Standard Deviation 30 days$": "bb_std_30",
    r"^Buy Box: Standard Deviation 90 days$": "bb_std_90",
    r"^Buy Box: Standard Deviation 365 days$": "bb_std_365",
    r"^Buy Box: Flipability 30 days$": "bb_flip_30",
    r"^Buy Box: Flipability 90 days$": "bb_flip_90",
    r"^Buy Box: Flipability 365 days$": "bb_flip_365",
    r"^Buy Box: Unqualified$": "bb_unqualified",
    r"^Competitive Price Threshold$": "competitive_threshold",
    r"^Suggested Lower Price$": "suggested_lower",
    r"^Amazon: Current$": "amazon_now",
    r"^Amazon: 90 days OOS$": "amazon_oos_pct_90",
    r"^Amazon: OOS Count 30 days$": "amazon_oos_count_30",
    r"^Amazon: OOS Count 90 days$": "amazon_oos_count_90",
    r"^Amazon: Availability of the Amazon offer$": "amazon_availability",
    r"^Amazon: Amazon offer shipping delay$": "amazon_ship_delay",
    r"^New: Current$": "new_now",
    r"^New Offer Count: Current$": "new_offer_count_now",
    r"^New Offer Count: 30 days avg\.": "new_offer_count_avg_30",
    r"^Total Offer Count$": "total_offer_count",
    r"^One Time Coupon: Absolute$": "coupon_abs",
    r"^One Time Coupon: Percentage$": "coupon_pct",
    r"^Business Discount: Percentage$": "business_disc_pct",
    r"^New, 3rd Party FBA: Current$": "fba_3p_now",
    r"^New, 3rd Party FBM .*: Current$": "fbm_3p_now",
    r"^FBA Pick&Pack Fee$": "fba_pickpack_fee",
    r"^Referral Fee %$": "referral_fee_pct",
    r"^Referral Fee based on current Buy Box price$": "referral_fee_amount",
    r"^MAP restriction$": "map_restriction",
    r"^URL: Amazon$": "url_amazon",
    r"^URL: Keepa$": "url_keepa",
    r"^Package: Dimension \(cm³\)$": "pkg_cm3",
    r"^Package: Length \(cm\)$": "pkg_len_cm",
    r"^Package: Width \(cm\)$": "pkg_w_cm",
    r"^Package: Height \(cm\)$": "pkg_h_cm",
    r"^Package: Weight \(g\)$": "pkg_weight_g",
    r"^Item: Weight \(g\)$": "item_weight_g",
    r"^Prime Eligible \(Buy Box\)$": "prime_eligible_bb",
}


def normalize_header(header: str) -> str:
    """Return ``header`` with extra spaces and emojis removed."""
    if not isinstance(header, str):
        return ""
    # remove common emojis or non word characters except basic punctuation
    header = header.replace("🚚", " ")
    header = re.sub(r"[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF]+", "", header)
    # normalise whitespace and colons
    header = re.sub(r"\s*:\s*", ": ", header)
    header = re.sub(r"\s+", " ", header)
    return header.strip()


def parse_euro(value: Any) -> float:
    """Parse euro-formatted strings to ``float``.

    Handles thousand separators, euro symbols and decimal commas.
    Returns ``math.nan`` when parsing fails.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return math.nan
    cleaned = value.replace("€", "").replace(".", "").replace(",", ".")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    try:
        return float(cleaned)
    except Exception:
        return math.nan


def parse_pct(value: Any) -> float:
    """Parse percentage strings into a fraction (0-1)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    if isinstance(value, (int, float)):
        v = float(value)
        return v / 100 if abs(v) > 1 else v
    if not isinstance(value, str):
        return math.nan
    cleaned = value.replace("%", "").replace(",", ".")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned:
        return math.nan
    try:
        v = float(cleaned)
        return v / 100 if abs(v) > 1 else v
    except Exception:
        return math.nan


def parse_bool(value: Any) -> bool:
    """Parse common textual representations of booleans."""
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    if not isinstance(value, str):
        return False
    s = value.strip().lower()
    if s in {"yes", "true", "1", "y", "t"}:
        return True
    if s in {"no", "false", "0", "n", "f", "no amazon offer exists"}:
        return False
    return False


def parse_dt(value: Any) -> pd.Timestamp:
    """Parse a datetime value into ``pd.Timestamp``.

    Accepts ``datetime`` objects, pandas ``Timestamp`` or strings in
    ``YYYY-MM-DD HH:MM`` format. Returns ``pd.NaT`` on failure.
    """
    if isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, datetime):
        return pd.Timestamp(value)
    if not isinstance(value, str):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def apply_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with columns renamed to their canonical names."""
    rename_map = {}
    for col in df.columns:
        norm = normalize_header(col)
        for pattern, canonical in CANONICAL_MAP.items():
            if re.match(pattern, norm, flags=re.IGNORECASE):
                rename_map[col] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df
