import pandas as pd

def amazon_dominance_flag(row: pd.Series) -> bool:
    """Return True if Amazon is likely dominating the listing.

    Conditions:
    - bb_amz_pct_30d >= 50
    - amz_availability contains 'in stock'
    - amz_now is not NA
    """
    amz_pct = pd.to_numeric(row.get("bb_amz_pct_30d"), errors="coerce")
    availability = str(row.get("amz_availability", "")).lower()
    amz_now = row.get("amz_now")
    return bool(
        (pd.notna(amz_pct) and amz_pct >= 50)
        or ("in stock" in availability)
        or pd.notna(amz_now)
    )


def competition_score(row: pd.Series) -> float:
    """Calculate a simple competition score based on offers and buy box winners.

    Both metrics are normalised to [0,1] with a cap at 50 to avoid
    extreme influence.
    """
    offers = pd.to_numeric(row.get("offer_new_now"), errors="coerce")
    winners = pd.to_numeric(row.get("bb_winners_30d"), errors="coerce")
    offers_norm = min(max(offers, 0), 50) / 50 if pd.notna(offers) else 0.0
    winners_norm = min(max(winners, 0), 50) / 50 if pd.notna(winners) else 0.0
    return float((offers_norm + winners_norm) / 2)
