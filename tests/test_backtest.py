import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from services.backtest import backtest_opportunities


def test_backtest_single_opportunity():
    data = {
        "snapshot_date": ["2024-01-01", "2024-01-01"],
        "ASIN": ["A1", "A1"],
        "Locale": ["it", "fr"],
        "Price_BuyBox_New": ["10", "20"],
        "Sales_Rank_Current": ["100", "100"],
        "Offer_Count_Current": ["1", "1"],
    }
    df_all = pd.DataFrame(data)
    df_res, stats = backtest_opportunities(
        df_all,
        base_locale="it",
        target_locales=["fr"],
        discount_pct=0.0,
        min_profit_eur=1.0,
        min_margin_pct=10.0,
        max_sales_rank=1000,
    )
    assert not df_res.empty
    row = df_res.iloc[0]
    assert abs(row["potential_profit_eur"] - 7.8) < 1e-6
    assert stats[0]["occurrences"] == 1
