"""
Test per verificare la conversione dei decimali con virgola
"""

import pandas as pd
from loaders import force_numeric_conversion
from pricing import select_target_price

def test_comma_decimal_conversion():
    """Test conversione virgola -> punto nei prezzi"""
    
    print("=== TEST CONVERSIONE DECIMALI CON VIRGOLA ===")
    
    # Simula i tuoi dati con virgole come separatori decimali
    raw_data = {
        'ASIN': ['B0CG77NW4M'],
        'Buy Box 🚚: Current': ['57,43'],      # Virgola come nel tuo CSV
        'Amazon: Current': ['89,9'],           # Virgola come nel tuo CSV  
        'New FBA: Current': ['56,88'],
        'New FBM: Current': ['58,99']
    }
    
    print("DATI ORIGINALI (con virgole):")
    for col, val in raw_data.items():
        if col != 'ASIN':
            print(f"  {col}: {val[0]}")
    
    # Crea DataFrame
    df = pd.DataFrame(raw_data)
    
    print("\nTIPI DATI PRIMA DELLA CONVERSIONE:")
    for col in df.columns:
        if col != 'ASIN':
            print(f"  {col}: {df[col].dtype} - Valore: {df[col].iloc[0]} (tipo: {type(df[col].iloc[0])})")
    
    # Applica la conversione come nel codice reale
    print("\nAPPLICO force_numeric_conversion...")
    
    price_columns = ['Buy Box 🚚: Current', 'Amazon: Current', 'New FBA: Current', 'New FBM: Current']
    for col in price_columns:
        if col in df.columns:
            df[col] = force_numeric_conversion(df[col])
    
    print("\nTIPI DATI DOPO LA CONVERSIONE:")
    for col in price_columns:
        if col in df.columns:
            print(f"  {col}: {df[col].dtype} - Valore: {df[col].iloc[0]} (tipo: {type(df[col].iloc[0])})")
    
    # Test select_target_price
    print("\nTEST select_target_price:")
    row = df.iloc[0]
    target_price = select_target_price(row, 'it', 'current')
    
    print(f"select_target_price risultato: €{target_price:.2f}")
    
    # Verifica quale prezzo sta usando
    buybox_value = row['Buy Box 🚚: Current']
    amazon_value = row['Amazon: Current']
    
    print(f"Buy Box value: {buybox_value} (€{buybox_value:.2f})")
    print(f"Amazon value: {amazon_value} (€{amazon_value:.2f})")
    
    if abs(target_price - buybox_value) < 0.01:
        print("✅ SUCCESS: Usa Buy Box correttamente!")
    elif abs(target_price - amazon_value) < 0.01:
        print("❌ ERROR: Usa Amazon invece di Buy Box!")
    else:
        print(f"⚠️ UNKNOWN: Usa un valore diverso: €{target_price:.2f}")
    
    return df

if __name__ == "__main__":
    result_df = test_comma_decimal_conversion()