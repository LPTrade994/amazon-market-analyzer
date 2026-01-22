"""
Test del flusso completo con dati reali che hanno virgole decimali
"""

import pandas as pd
import streamlit as st
from io import StringIO
from loaders import load_data, validate_schema, normalize_columns, force_numeric_conversion
from pricing import select_target_price
import config

def test_real_data_scenario():
    """
    Simula esattamente quello che succede con i tuoi dati reali
    """
    print("=== TEST FLUSSO COMPLETO CON DATI REALI ===")
    
    # Simulo i tuoi dati esatti con virgole
    csv_content = '''ASIN,Title,Buy Box 🚚: Current,Amazon: Current,New FBA: Current,New FBM: Current,Referral Fee %,FBA Pick&Pack Fee
B0CG77NW4M,Samsung Galaxy SmartTag2,57,43,89,9,56,88,58,99,0,07,3,51'''
    
    print("CSV CONTENUTO ORIGINALE:")
    print(csv_content)
    
    # Crea un file simulato 
    from io import StringIO, BytesIO
    
    # Simula upload file
    csv_bytes = csv_content.encode('utf-8')
    
    # Test step-by-step del loading
    print("\n=== STEP 1: CARICAMENTO GREZZO ===")
    df_raw = pd.read_csv(StringIO(csv_content))
    
    print("Dati grezzi:")
    print(f"  Buy Box: '{df_raw['Buy Box 🚚: Current'].iloc[0]}' (tipo: {type(df_raw['Buy Box 🚚: Current'].iloc[0])})")
    print(f"  Amazon: '{df_raw['Amazon: Current'].iloc[0]}' (tipo: {type(df_raw['Amazon: Current'].iloc[0])})")
    
    print("\n=== STEP 2: NORMALIZE COLUMNS ===")
    df_normalized = normalize_columns(df_raw.copy())
    
    print("Dopo normalizzazione:")
    print(f"  Buy Box: {df_normalized['Buy Box 🚚: Current'].iloc[0]} (tipo: {type(df_normalized['Buy Box 🚚: Current'].iloc[0])})")
    print(f"  Amazon: {df_normalized['Amazon: Current'].iloc[0]} (tipo: {type(df_normalized['Amazon: Current'].iloc[0])})")
    
    print("\n=== STEP 3: VALIDATE SCHEMA ===")
    # Attiva DEBUG per vedere i messaggi
    config.DEBUG_MODE = True
    
    df_validated = validate_schema(df_normalized.copy())
    
    print("Dopo validazione schema:")
    print(f"  Buy Box: {df_validated['Buy Box 🚚: Current'].iloc[0]} (tipo: {type(df_validated['Buy Box 🚚: Current'].iloc[0])})")
    print(f"  Amazon: {df_validated['Amazon: Current'].iloc[0]} (tipo: {type(df_validated['Amazon: Current'].iloc[0])})")
    
    print("\n=== STEP 4: TEST select_target_price ===")
    row = df_validated.iloc[0]
    
    # Debug colonne disponibili
    print("Colonne nel row:")
    for col in row.index:
        if 'Current' in col:
            print(f"  {col}: {row[col]} (tipo: {type(row[col])})")
    
    # Test select_target_price
    target_price = select_target_price(row, 'it', 'current')
    
    print(f"\nselect_target_price risultato: €{target_price:.2f}")
    
    buybox_value = row['Buy Box 🚚: Current']
    amazon_value = row['Amazon: Current']
    
    print(f"Buy Box value: {buybox_value}")
    print(f"Amazon value: {amazon_value}")
    
    # Determina quale prezzo viene usato
    if abs(target_price - buybox_value) < 0.01:
        print("✅ SUCCESS: Usa Buy Box correttamente!")
        return True
    elif abs(target_price - amazon_value) < 0.01:
        print("❌ ERROR: Usa Amazon invece di Buy Box!")
        return False
    else:
        print(f"⚠️ UNKNOWN: Usa un valore diverso: €{target_price:.2f}")
        return False

if __name__ == "__main__":
    success = test_real_data_scenario()
    if success:
        print("\n🎉 IL PROBLEMA È RISOLTO!")
    else:
        print("\n🚨 IL PROBLEMA PERSISTE - SERVE DEBUGGING AGGIUNTIVO")