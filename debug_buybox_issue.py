"""
Debug script per identificare perché viene mostrato Amazon Current invece di Buy Box
"""

import pandas as pd
import streamlit as st
from pricing import select_target_price, select_purchase_price

def debug_buybox_data(df):
    """Debug dei dati reali per capire il problema Buy Box"""
    
    st.write("### 🔍 DEBUG BUY BOX ISSUE")
    st.write("Analizzando i tuoi dati per capire perché viene mostrato Amazon Current...")
    
    if df.empty:
        st.error("DataFrame vuoto!")
        return
    
    # Identifica le colonne disponibili
    price_columns = [col for col in df.columns if 'Current' in col]
    st.write("**Colonne prezzo trovate:**")
    for col in price_columns:
        st.write(f"  - {col}")
    
    # Controlla alcuni prodotti
    st.write("**Analisi primi 5 prodotti:**")
    
    for i, (idx, row) in enumerate(df.head(5).iterrows()):
        st.write(f"**Prodotto {i+1} - ASIN: {row.get('ASIN', 'N/A')}**")
        
        # Mostra tutti i prezzi disponibili
        st.write("  Prezzi disponibili:")
        for col in price_columns:
            if col in row.index:
                value = row[col]
                if pd.notna(value) and value > 0:
                    st.write(f"    ✓ {col}: €{value:.2f}")
                else:
                    st.write(f"    ❌ {col}: {value} (mancante/zero)")
        
        # Test select_target_price
        try:
            target_price = select_target_price(row, 'it', 'current')
            st.write(f"  **select_target_price risultato: €{target_price:.2f}**")
            
            # Identifica quale prezzo sta usando
            buybox_col = 'Buy Box 🚚: Current'
            if buybox_col in row.index and pd.notna(row[buybox_col]) and row[buybox_col] > 0:
                if abs(target_price - row[buybox_col]) < 0.01:
                    st.success(f"  ✅ Sta usando Buy Box: €{row[buybox_col]:.2f}")
                else:
                    st.error(f"  ❌ NON sta usando Buy Box! Buy Box=€{row[buybox_col]:.2f}, Target=€{target_price:.2f}")
            else:
                st.warning(f"  ⚠️ Buy Box mancante, usando fallback: €{target_price:.2f}")
                
                # Identifica quale fallback sta usando
                fallback_columns = ['Amazon: Current', 'New FBA: Current', 'New FBM: Current']
                for fcol in fallback_columns:
                    if fcol in row.index and pd.notna(row[fcol]) and abs(target_price - row[fcol]) < 0.01:
                        st.write(f"    → Fallback usato: {fcol}")
                        break
                        
        except Exception as e:
            st.error(f"  ❌ Errore in select_target_price: {e}")
        
        st.write("---")

def main():
    st.title("🔍 Buy Box Debug Tool")
    st.write("Upload del tuo CSV per debuggare il problema Buy Box vs Amazon Current")
    
    uploaded_file = st.file_uploader("Carica il tuo file CSV", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"File caricato: {len(df)} righe, {len(df.columns)} colonne")
            
            debug_buybox_data(df)
            
        except Exception as e:
            st.error(f"Errore nel caricamento: {e}")
    else:
        st.info("Carica un file CSV per iniziare il debug")

if __name__ == "__main__":
    main()