"""Core scoring utilities used by the dashboard."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict

import numpy as np
import pandas as pd
import streamlit as st

from settings import SHIPPING_TABLE as SHIPPING_COSTS, VAT_RATES


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
    if (
        weight_kg is None
        or (isinstance(weight_kg, float) and math.isnan(weight_kg))
        or weight_kg <= 0
    ):
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


def _minmax(series: pd.Series) -> pd.Series:
    min_val = series.min()
    max_val = series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)


def margin_score(df: pd.DataFrame) -> pd.Series:
    return _minmax(df["Margine_Netto_%"].fillna(0))


def demand_score(df: pd.DataFrame) -> pd.Series:
    return 1 - _minmax(df["SalesRank_Comp"].fillna(df["SalesRank_Comp"].max()))


def competition_score(df: pd.DataFrame) -> pd.Series:
    return 1 - _minmax(df["NewOffer_Comp"].fillna(df["NewOffer_Comp"].max()))


def volatility_score(df: pd.DataFrame) -> pd.Series:
    return _minmax(df["Trend_Bonus"].fillna(0))


def risk_score(df: pd.DataFrame) -> pd.Series:
    return _minmax(df["ROI_Factor"].fillna(0))


@st.cache_data(show_spinner=False)
def compute_scores(df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    """Return ``df`` with a normalized opportunity score."""
    df = df.copy()
    subs = {
        "margin": margin_score(df),
        "demand": demand_score(df),
        "competition": competition_score(df),
        "volatility": volatility_score(df),
        "risk": risk_score(df),
    }
    score = sum(weights.get(k, 1.0) * subs[k] for k in subs)
    df["final_score"] = _minmax(score) * 100
    return df


def aggregate_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per ASIN with the best market and score."""
    if df is None or df.empty or "ASIN" not in df.columns:
        return pd.DataFrame(columns=["ASIN", "Best_Market", "Opportunity_Score"])

    if "Opportunity_Score" not in df.columns:
        return pd.DataFrame(columns=["ASIN", "Best_Market", "Opportunity_Score"])

    idx = df.groupby("ASIN") ["Opportunity_Score"].idxmax()
    best = df.loc[idx].copy()
    best = best.rename(columns={"Locale (comp)": "Best_Market"})

    cols = ["ASIN"]
    if "Title (base)" in best.columns:
        cols.append("Title (base)")
    cols += ["Best_Market", "Opportunity_Score"]

    return best[cols].sort_values("Opportunity_Score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
#  New interpretable scoring utilities
# ---------------------------------------------------------------------------


def sigmoid(series: pd.Series, mid: float, k: float) -> pd.Series:
    """Standard logistic sigmoid centred around ``mid``.

    Parameters
    ----------
    series:
        Input values.
    mid:
        Midpoint (value yielding 0.5).
    k:
        Steepness of the curve.
    """

    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    return 1.0 / (1.0 + np.exp(-k * (s - mid)))


def minmax(series: pd.Series, cap_p95: bool = False) -> pd.Series:
    """Scale a series between 0 and 1.

    If ``cap_p95`` is True the upper range is capped at the 95th percentile
    before scaling which reduces the impact of strong outliers.
    """

    s = pd.to_numeric(series, errors="coerce")
    if cap_p95 and not s.dropna().empty:
        cap = s.quantile(0.95)
        s = s.clip(upper=cap)
    min_val = s.min()
    max_val = s.max()
    if not np.isfinite(min_val) or not np.isfinite(max_val) or max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (s - min_val) / (max_val - min_val)


def pct_rank(series: pd.Series) -> pd.Series:
    """Return the percentage rank of each element.

    Values are ranked using ``method='max'`` so that the best value receives 1.0
    and the worst 0.0.
    """

    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return pd.Series(0.0, index=series.index)
    return s.rank(pct=True, method="max")


def compute_score_v2(df: pd.DataFrame) -> pd.DataFrame:
    """Compute interpretable, robust score for each row in ``df``.

    The function adds ``score_v2`` (0-100 scale), ``score_class`` and
    ``score_explain`` columns to the returned frame.
    """

    if df is None or df.empty:
        return df

    out = df.copy()

    # --- base features -------------------------------------------------
    out["s_margin_pct"] = sigmoid(out.get("net_pct", 0), mid=15, k=0.25)
    out["s_margin_eur"] = minmax(out.get("net_eur", 0).clip(lower=0), cap_p95=True)
    out["s_speed"] = sigmoid(np.log1p(out.get("bought_30d", 0)), mid=np.log(30), k=1)
    out["s_rank"] = 1.0 - pct_rank(out.get("rank_now", 0))
    offers_comp = pd.to_numeric(out.get("offer_new_now", 0), errors="coerce").fillna(0)
    out["offers_competition_norm"] = (offers_comp / 50.0).clip(0.0, 1.0)

    # --- penalties -----------------------------------------------------
    bb_now = pd.to_numeric(out.get("bb_now", 0), errors="coerce")
    bb_90d = pd.to_numeric(out.get("bb_90d", np.nan), errors="coerce")
    bb_std_30d = pd.to_numeric(out.get("bb_std_30d", 0), errors="coerce")

    delta = pd.Series(0.0, index=out.index)
    mask = bb_90d.notna() & (bb_90d != 0)
    delta[mask] = (bb_now[mask] - bb_90d[mask]).abs() / bb_90d[mask]
    # precision bonus: higher std => higher penalty (relative to current price)
    std_factor = pd.Series(0.0, index=out.index)
    good = mask & bb_now.notna() & (bb_now != 0)
    std_factor[good] = bb_std_30d[good].fillna(0) / bb_now[good]
    out["p_volatility"] = (delta + std_factor).clip(0.0, 0.5)

    out["p_competition"] = (offers_comp / 50.0).clip(0.0, 0.4)
    amz_dom = out.get("amz_dominant", False)
    out["p_amz_dom"] = pd.Series(amz_dom).fillna(False).astype(float).apply(lambda x: 0.15 if x else 0.0)

    # --- final score ---------------------------------------------------
    raw = (
        0.35 * out["s_margin_pct"]
        + 0.20 * out["s_margin_eur"]
        + 0.25 * out["s_speed"]
        + 0.15 * out["s_rank"]
        + 0.05 * (1 - out["offers_competition_norm"])
    )

    out["score_v2"] = 100 * (
        raw - out["p_volatility"] - out["p_competition"] - out["p_amz_dom"]
    )

    def _classify(x: float) -> str:
        if x >= 75:
            return "A"
        if x >= 55:
            return "B"
        return "C"

    out["score_class"] = out["score_v2"].apply(_classify)

    def _explain(row: pd.Series) -> str:
        data = {
            "margin_pct": round(0.35 * row["s_margin_pct"], 3),
            "margin_eur": round(0.20 * row["s_margin_eur"], 3),
            "speed": round(0.25 * row["s_speed"], 3),
            "rank": round(0.15 * row["s_rank"], 3),
            "volatility_pen": round(row["p_volatility"], 3),
            "competition_pen": round(row["p_competition"], 3),
            "amz_dom_pen": round(row["p_amz_dom"], 3),
        }
        return json.dumps(data, ensure_ascii=False)

    out["score_explain"] = out.apply(_explain, axis=1)

    return out

