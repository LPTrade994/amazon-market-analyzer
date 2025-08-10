from __future__ import annotations

import math
from typing import Any, Dict

import pandas as pd

from schema import parse_eu_price, parse_percent


PRICE_SOURCES = {
    "bb_now": "bb_now",
    "new_now": "new_now",
    "amz_now": "amz_now",
}


def _pick_price(row: pd.Series, source: str) -> float:
    col = PRICE_SOURCES.get(source, "bb_now")
    return parse_eu_price(row.get(col))


def _safe_number(x: Any) -> float:
    if x is None:
        return math.nan
    try:
        return float(x)
    except Exception:
        return parse_eu_price(x)


def compute_row_costs(row: pd.Series, cfg: Dict[str, Any]) -> Dict[str, float]:
    sale_price = _pick_price(row, cfg.get("sale_price_source", "bb_now"))
    if cfg.get("apply_coupon"):
        cp = parse_percent(row.get("coupon_pct"))
        if math.isfinite(cp) and cp > 0:
            sale_price *= 1.0 - cp / 100.0
        ca = parse_eu_price(row.get("coupon_abs"))
        if math.isfinite(ca) and ca > 0:
            sale_price -= ca
    if cfg.get("apply_biz_discount"):
        bp = parse_percent(row.get("biz_discount_pct"))
        if math.isfinite(bp) and bp > 0:
            sale_price *= 1.0 - bp / 100.0

    referral_pct = cfg.get("referral_pct", 15.0)
    rp = parse_percent(row.get("referral_fee_pct"))
    if math.isfinite(rp) and rp > 0:
        referral_pct = rp

    fba_fee = 0.0
    if cfg.get("fulfillment", "FBA") == "FBA":
        f = parse_eu_price(row.get("fba_pickpack_fee"))
        if math.isfinite(f) and f > 0:
            fba_fee = f
        else:
            fba_fee = cfg.get("fba_fee", 0.0)

    weight_kg = _safe_number(row.get("weight_kg"))
    volume_cm3 = _safe_number(row.get("volume_cm3"))
    volumetric_kg = (
        volume_cm3 / cfg.get("dim_divisor", 5000)
        if math.isfinite(volume_cm3)
        else math.nan
    )
    billable_kg = math.nan
    if math.isfinite(weight_kg) and math.isfinite(volumetric_kg):
        billable_kg = max(weight_kg, volumetric_kg)
    elif math.isfinite(weight_kg):
        billable_kg = weight_kg
    elif math.isfinite(volumetric_kg):
        billable_kg = volumetric_kg

    shipping_out_eur = (
        cfg.get("shipping_out_per_kg", 0.0) * billable_kg
        if math.isfinite(billable_kg)
        else 0.0
    )

    gross_revenue = sale_price
    fees = gross_revenue * (referral_pct / 100.0)
    if cfg.get("fulfillment", "FBA") == "FBA":
        fees += fba_fee

    cost_basis = _safe_number(
        row.get("purchase_price")
        or row.get("Acquisto_Netto")
        or cfg.get("purchase_price")
    )
    if not math.isfinite(cost_basis):
        cost_basis = 0.0

    other_costs = (
        cfg.get("extra_handling_eur", 0.0)
        + cfg.get("shipping_inbound_eur", 0.0)
        + shipping_out_eur
    )

    net_eur = gross_revenue - fees - cost_basis - other_costs
    net_pct = (100.0 * net_eur / cost_basis) if cost_basis > 0 else math.nan

    return {
        "sale_price_used": sale_price,
        "referral_pct": referral_pct,
        "fba_fee": fba_fee,
        "billable_kg": billable_kg,
        "fees": fees,
        "net_eur": net_eur,
        "net_pct": net_pct,
    }


def compute_costs(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    add = df.apply(lambda r: pd.Series(compute_row_costs(r, cfg)), axis=1)
    return pd.concat([df, add], axis=1)

