import sys
sys.path.append('.')
from profit_model import compute_route_metrics
from config import VAT_RATES
import pandas as pd

# Test con PlayStation 5 example
test_ps5 = pd.Series({
    'ASIN': 'B0BS1MLFML',
    'Title': 'Playstation 5 Standard Console',
    'Buy Box 🚚: Current': 589.00,
    'detected_locale': 'it',
    'source_market': 'it',
    'Referral Fee based on current Buy Box price': 57.12,
    'FBA Pick&Pack Fee': 3.0
})

params = {
    'purchase_strategy': 'Buy Box Current',
    'discount': 0.21,
    'scenario': 'current',
    'mode': 'FBA',
    'inbound_logistics_high': 15.0  # Come nel tuo esempio
}

# Test route IT->ES con prezzo target €704.99
result = compute_route_metrics(
    test_ps5, 
    target_locale='es',
    params=params,
    custom_target_price=704.99
)

print("="*60)
print("TEST PLAYSTATION 5: IT->ES")
print("="*60)
print(f"Purchase Price: €{result['purchase_price']:.2f}")
print(f"Net Cost: €{result['net_cost']:.2f}")
print(f"Target Price (Gross): €{result['target_price_gross']:.2f}")
print(f"Target Price (Net): €{result['target_price_net']:.2f}")
print(f"VAT Amount: €{result['target_vat_amount']:.2f}")
print(f"VAT Rate ES: {result['target_vat_rate']*100:.0f}%")
print()
print("COST BREAKDOWN:")
for cost_type, amount in result['cost_breakdown'].items():
    print(f"  {cost_type}: €{amount:.2f}")
print()
print("PROFIT RESULTS:")
print(f"Gross Margin (Amazon): €{result['gross_margin_eur']:.2f}")
print(f"Gross Margin %: {result['gross_margin_pct']:.1f}%")
print(f"ROI: {result['roi']:.1f}%")
print()
print("EXPECTED VALUES (from Revenue Calculator):")
print("  Net Revenue: €582.64")
print("  Net Cost: €359.10")
print("  Total Costs: €431.22")
print("  Expected Profit: €151.42")
print("  Expected Margin: 26.0%")
print()
if abs(result['gross_margin_eur'] - 151.42) < 5:
    print("✅ PROFIT CALCULATION CORRECT!")
else:
    print(f"❌ PROFIT MISMATCH: Got €{result['gross_margin_eur']:.2f}, Expected €151.42")