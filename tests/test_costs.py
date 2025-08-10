import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd

from costs import compute_costs


def test_basic_cost_model():
    df = pd.DataFrame(
        {
            "bb_now": ["10,00 €"],
            "coupon_abs": ["1,00 €"],
            "coupon_pct": ["10%"],
            "biz_discount_pct": ["5%"],
            "referral_fee_pct": ["8%"],
            "fba_pickpack_fee": ["2,00 €"],
            "weight_kg": [1.0],
            "volume_cm3": [6000],
            "purchase_price": [5.0],
        }
    )
    cfg = {
        "sale_price_source": "bb_now",
        "apply_coupon": True,
        "apply_biz_discount": True,
        "fulfillment": "FBA",
        "extra_handling_eur": 1.0,
        "shipping_inbound_eur": 0.5,
        "dim_divisor": 5000,
        "shipping_out_per_kg": 1.0,
        "referral_pct": 15.0,
        "fba_fee": 1.0,
        "purchase_price": 5.0,
    }
    out = compute_costs(df, cfg)
    row = out.iloc[0]
    assert abs(row["sale_price_used"] - 7.6) < 1e-6
    assert abs(row["fees"] - 2.608) < 1e-6
    assert abs(row["billable_kg"] - 1.2) < 1e-6
    assert abs(row["net_eur"] + 2.708) < 1e-6
    assert abs(row["net_pct"] + 54.16) < 0.01
    assert row["referral_pct"] == 8.0
    assert row["fba_fee"] == 2.0

