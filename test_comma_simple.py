import pandas as pd
from loaders import force_numeric_conversion
from pricing import select_target_price

# Simula i tuoi dati con virgole come separatori decimali
raw_data = {
    'ASIN': ['B0CG77NW4M'],
    'Buy Box Current': ['57,43'],      # Virgola come nel tuo CSV
    'Amazon: Current': ['89,9'],       # Virgola come nel tuo CSV  
    'New FBA: Current': ['56,88'],
    'New FBM: Current': ['58,99']
}

print("=== TEST CONVERSIONE DECIMALI CON VIRGOLA ===")
print("DATI ORIGINALI (con virgole):")
for col, val in raw_data.items():
    if col != 'ASIN':
        print(f"  {col}: {val[0]}")

# Crea DataFrame
df = pd.DataFrame(raw_data)

print("\nTIPI DATI PRIMA DELLA CONVERSIONE:")
for col in df.columns:
    if col != 'ASIN':
        print(f"  {col}: {df[col].dtype} - Valore: '{df[col].iloc[0]}'")

# Applica la conversione come nel codice reale
print("\nAPPLICO force_numeric_conversion...")

# Aggiungo colonna con nome corretto per il test
df['Buy Box Current'] = force_numeric_conversion(df['Buy Box Current'])
df['Amazon: Current'] = force_numeric_conversion(df['Amazon: Current'])

print("\nTIPI DATI DOPO LA CONVERSIONE:")
print(f"  Buy Box Current: {df['Buy Box Current'].dtype} - Valore: {df['Buy Box Current'].iloc[0]}")
print(f"  Amazon: Current: {df['Amazon: Current'].dtype} - Valore: {df['Amazon: Current'].iloc[0]}")

# Verifica che la conversione sia corretta
buybox_value = df['Buy Box Current'].iloc[0]
amazon_value = df['Amazon: Current'].iloc[0]

print(f"\nVERIFICA CONVERSIONE:")
print(f"  57,43 -> {buybox_value} {'OK' if buybox_value == 57.43 else 'ERROR'}")
print(f"  89,9 -> {amazon_value} {'OK' if amazon_value == 89.9 else 'ERROR'}")

# Test del problema: rinomina la colonna per matchare il codice reale
df['Buy Box 🚚: Current'] = df['Buy Box Current']

print(f"\nTEST select_target_price con nome colonna corretto:")
row = df.iloc[0]

try:
    target_price = select_target_price(row, 'it', 'current')
    print(f"  select_target_price risultato: EUR{target_price:.2f}")
    
    if abs(target_price - 57.43) < 0.01:
        print("  SUCCESS: Usa Buy Box correttamente!")
    elif abs(target_price - 89.9) < 0.01:
        print("  ERROR: Usa Amazon invece di Buy Box!")
    else:
        print(f"  UNKNOWN: Usa un valore diverso: EUR{target_price:.2f}")
        
except Exception as e:
    print(f"  ERROR in select_target_price: {e}")