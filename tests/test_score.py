import pandas as pd
from score import compute_score_v2


def _base_df():
    return pd.DataFrame(
        {
            "net_pct": [20.0],
            "net_eur": [10.0],
            "bought_30d": [100.0],
            "rank_now": [1000.0],
            "offer_new_now": [5.0],
            "bb_now": [100.0],
            "bb_90d": [100.0],
            "bb_std_30d": [0.0],
            "amz_dominant": [False],
        }
    )


def test_score_decreases_with_more_offers():
    base = compute_score_v2(_base_df())
    more_offers = _base_df()
    more_offers["offer_new_now"] *= 2
    res = compute_score_v2(more_offers)
    assert res.loc[0, "score_v2"] < base.loc[0, "score_v2"]


def test_buybox_divergence_increases_penalty():
    base = compute_score_v2(_base_df())
    deviated = _base_df()
    deviated["bb_now"] = 200.0
    res = compute_score_v2(deviated)
    assert res.loc[0, "p_volatility"] > base.loc[0, "p_volatility"]
    assert res.loc[0, "score_v2"] < base.loc[0, "score_v2"]

