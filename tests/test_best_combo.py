import pandas as pd
from analysis import best_cross_market_combo


def test_single_locale_degrades_gracefully():
    df = pd.DataFrame(
        {
            "asin": ["A1"],
            "title": ["Prod"],
            "locale": ["IT"],
            "sale_price": [30.0],
            "purchase_price": [10.0],
            "rank_now": [100.0],
            "bought_30d": [50.0],
            "offer_new_now": [5.0],
            "score_v2": [80.0],
        }
    )
    result = best_cross_market_combo(df, sell_targets=["IT"])
    assert len(result) == 1
    row = result.iloc[0]
    assert row["best_buy_locale"] == "IT"
    assert row["best_sell_locale"] == "IT"
    assert row["net_eur"] == 20.0
    assert row["net_pct"] == 200.0

