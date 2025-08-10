import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from loaders import load_keepa
import pandas as pd
from score import (
    margin_score,
    demand_score,
    competition_score,
    volatility_score,
    risk_score,
    aggregate_opportunities,
    compute_score_v2,
)


def test_subscores_range():
    df = load_keepa("sample_data/keepa_sample.xlsx")
    # minimal columns needed for subscore functions
    df = df.rename(columns={
        "Sales Rank: Current": "SalesRank_Comp",
        "New Offer Count: Current": "NewOffer_Comp",
    })
    df["SalesRank_Comp"] = pd.to_numeric(df["SalesRank_Comp"], errors="coerce")
    df["NewOffer_Comp"] = pd.to_numeric(df["NewOffer_Comp"], errors="coerce")
    df["Margine_Netto_%"] = 0.0
    df["Trend_Bonus"] = 0.0
    df["ROI_Factor"] = 0.0

    for func in [margin_score, demand_score, competition_score, volatility_score, risk_score]:
        scores = func(df)
        assert ((0.0 <= scores) & (scores <= 1.0)).all()


def test_aggregate_opportunities():
    df = pd.DataFrame(
        {
            "ASIN": ["A1", "A1", "A2"],
            "Opportunity_Score": [10, 20, 15],
            "Locale (comp)": ["DE", "FR", "IT"],
        }
    )
    agg = aggregate_opportunities(df)
    assert len(agg) == 2
    a1 = agg[agg["ASIN"] == "A1"].iloc[0]
    assert a1["Opportunity_Score"] == 20
    assert a1["Best_Market"] == "FR"


def test_compute_score_v2_basic():
    df = pd.DataFrame(
        {
            "net_pct": [20, 10],
            "net_eur": [5, 1],
            "bought_30d": [50, 5],
            "rank_now": [1000, 50000],
            "offer_new_now": [10, 80],
            "bb_now": [10, 15],
            "bb_90d": [9, 15],
            "bb_std_30d": [0.5, 2.0],
            "amz_dominant": [False, True],
        }
    )
    res = compute_score_v2(df)
    assert "score_v2" in res.columns
    assert "score_class" in res.columns
    assert ((res["score_v2"].notna()) & (res["score_v2"].abs() <= 1000)).all()
