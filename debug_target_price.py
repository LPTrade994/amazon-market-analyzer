import pandas as pd
from pricing import select_target_price, select_purchase_price

def test_target_price_logic():
    """Test per capire perché viene mostrato Amazon Current invece di Buy Box"""
    
    print("=== DEBUG TARGET PRICE LOGIC ===")
    
    # Test data che simula il tuo caso
    test_row = pd.Series({
        'Buy Box 🚚: Current': 45.99,  # Buy Box più basso
        'Amazon: Current': 52.50,      # Amazon più alto  
        'New FBA: Current': 49.00,
        'New FBM: Current': 48.00,
        'Referral Fee %': 0.15,
        'FBA Pick&Pack Fee': 2.5
    })
    
    print("DATI TEST:")
    print(f"  Buy Box: €{test_row['Buy Box 🚚: Current']:.2f}")
    print(f"  Amazon: €{test_row['Amazon: Current']:.2f}")
    print(f"  FBA: €{test_row['New FBA: Current']:.2f}")
    print()
    
    print("PURCHASE STRATEGIES:")
    strategies = ['Buy Box Current', 'Amazon Current', 'New FBA Current']
    
    for strategy in strategies:
        purchase_price = select_purchase_price(test_row, strategy)
        target_price = select_target_price(test_row, 'it', 'current')
        
        print(f"  {strategy}:")
        print(f"    Purchase: €{purchase_price:.2f}")
        print(f"    Target:   €{target_price:.2f}")
        
        # Verifica se target price è sempre Buy Box
        if abs(target_price - 45.99) < 0.01:
            print("    ✓ Target usa Buy Box (CORRETTO)")
        else:
            print("    ❌ Target NON usa Buy Box (PROBLEMA!)")
        print()
    
    # Test con Buy Box mancante
    print("TEST SENZA BUY BOX:")
    test_row_no_buybox = test_row.copy()
    test_row_no_buybox = test_row_no_buybox.drop('Buy Box 🚚: Current')
    
    target_fallback = select_target_price(test_row_no_buybox, 'it', 'current')
    print(f"  Target senza Buy Box: €{target_fallback:.2f}")
    
    if abs(target_fallback - 52.50) < 0.01:
        print("  ✓ Usa Amazon come fallback (CORRETTO)")
    else:
        print("  ❌ Fallback non funziona (PROBLEMA)")

if __name__ == "__main__":
    test_target_price_logic()