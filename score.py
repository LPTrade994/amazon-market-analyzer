"""Core scoring utilities used by the dashboard."""

from __future__ import annotations

import math
import re
from typing import Any, Dict

# Default shipping price table (Italy)
SHIPPING_COSTS: Dict[int, float] = {
    3: 5.14,    # up to 3 kg
    4: 6.41,    # up to 4 kg
    5: 6.95,    # up to 5 kg
    10: 8.54,   # up to 10 kg
    25: 12.51,  # up to 25 kg
    50: 21.66,  # up to 50 kg
    100: 34.16, # up to 100 kg
}

# VAT rates for supported marketplaces
VAT_RATES: Dict[str, int] = {
    "IT": 22,
    "DE": 19,
    "FR": 20,
    "ES": 21,
    "UK": 20,
}


def normalize_locale(locale_str: Any) -> str:
    """Return a two letter country code from a locale string."""
    if not isinstance(locale_str, str):
        return ""
    s = locale_str.strip().upper()
    matches = re.findall(r"[A-Z]{2}", s)
    code = matches[-1] if matches else ""
    if code == "GB":
        code = "UK"
    return code


def calculate_shipping_cost(weight_kg: Any) -> float:
    """Compute shipping cost from the ``SHIPPING_COSTS`` table."""
    if weight_kg is None or (isinstance(weight_kg, float) and math.isnan(weight_kg)) or weight_kg <= 0:
        return 0.0
    for limit, cost in sorted(SHIPPING_COSTS.items()):
        if weight_kg <= limit:
            return cost
    return SHIPPING_COSTS[100]


def calc_final_purchase_price(row: Dict[str, Any], discount: float) -> float:
    """Return the net purchase price for a row of data."""
    gross = row.get("Price_Base")
    if gross is None or (isinstance(gross, float) and math.isnan(gross)):
        return math.nan
    locale = normalize_locale(row.get("Locale (base)", ""))
    vat_rate = VAT_RATES.get(locale, 0) / 100.0
    net_price = gross / (1 + vat_rate)
    if locale == "IT":
        discount_amount = gross * discount
        final_price = net_price - discount_amount
    else:
        final_price = net_price * (1 - discount)
    return max(final_price, 0)


def format_trend(trend: Any) -> str:
    """Return a textual representation for a trend value."""
    if trend is None or (isinstance(trend, float) and math.isnan(trend)):
        return "N/D"
    if trend > 0.1:
        return "🔼 Crescente"
    if trend < -0.1:
        return "🔽 Decrescente"
    return "➖ Stabile"


def classify_opportunity(score: float):
    """Return a textual class and tag for a given opportunity score."""
    if score > 100:
        return "Eccellente", "success-tag"
    if score > 50:
        return "Buona", "success-tag"
    if score > 20:
        return "Discreta", "warning-tag"
    return "Bassa", "danger-tag"
