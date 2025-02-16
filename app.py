import streamlit as st
import pandas as pd
from typing import Dict

########################################
# Configurazione base Streamlit
########################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Paesi & Vendite",
    page_icon="🔎",
    layout="wide"
)

########################################
# (Opzionale) un po' di CSS
########################################
st.markdown("""
<style>
.block-container {
    padding: 1rem 2rem;
}
/* Bottone rosso */
.stButton button {
    background-color: #FF4B4B !important;
    color: #ffffff !important;
    border-radius: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

########################################
# Titolo & istruzioni
########################################
st.title("Amazon Market Analyzer - Multi Paesi con Dettagli Prodotti e ASIN IT unificati")
st.write("""
Caricamento:
1. **Mercato IT** (più file): Colonne minime: `ASIN`, `Title`, `Bought in past month`, `Buy Box: Current`.
2. **Paesi Esteri** (quanti vuoi): per ognuno, fornisci una sigla (ES, DE, FR, …) e carica il file (colonne: `ASIN`, `Amazon: Current`, `Delivery date`, ecc.).

Poi clicca "**Unisci & Mostra**" per ottenere:
- Tabella finale con i prezzi di tutti i paesi
- Dettagli di un singolo prodotto
- Elenco di ASIN dal mercato IT.
""")

########################################
# Sidebar: file IT + definizione paesi
########################################
with st.sidebar:
    st.subheader("Caricamento Mercato IT")
    files_it = st.file_uploader(
        "Mercato IT (CSV/XLSX) - multipli",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    
    st.subheader("Configura Paesi Esteri")
    num_countries = st.number_input(
        "Quanti paesi esteri?",
        min_value=0, max_value=10, value=2, step=1
    )
    
    # Dizionario: { "ES": <file>, "DE": <file>, ... }
    # NIENTE annotazione st.uploaded_file_manager (evita errori)
    country_files = {}
    
    for i in range(num_countries):
        st.write(f"**Paese #{i+1}**")
        country_code = st.text_input(
            f"Codice Paese (es: ES, DE, FR) n.{i+1}",
            value=f"ES{i}" if i>0 else "ES",
            key=f"country_code_{i}"
        )
        file_est = st.file_uploader(
            f"File Estero {country_code}",
            type=["csv","xlsx"],
            key=f"file_est_{i}"
        )
        if file_est and country_code.strip():
            country_files[country_code.strip()] = file_est
    
    unify_button = st.button("Unisci & Mostra")

########################################
# Funzioni di caricamento e pulizia
########################################
def load_data(uploaded_file):
    """Carica un CSV/XLSX in un DataFrame con tutte le colonne come string."""
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    if fname.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str)
        return df
    else:
        # CSV
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def pulisci_prezzo(prezzo_raw):
    """Rimuove simboli €, spazi, virgole e converte in float."""
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(prezzo)
    except:
        return None

########################################
# Se clic su Unisci & Mostra
########################################
if unify_button:
    # 1) Carichiamo e uniamo i file IT
    if not files_it:
        st.error("Devi caricare almeno un file per il Mercato IT.")
        st.stop()
    
    df_list_it = []
    for f in files_it:
        dft = load_data(f)
        if dft is not None and not dft.empty:
            df_list_it.append(dft)
    
    if not df_list_it:
        st.error("Nessuno dei file IT è stato caricato correttamente.")
        st.stop()
    
    df_it = pd.concat(df_list_it, ignore_index=True)
    
    # Colonne richieste in IT
    it_cols_needed = ["ASIN", "Title", "Bought in past month", "Buy Box: Current"]
    for c in it_cols_needed:
        if c not in df_it.columns:
            st.error(f"Nei file IT manca la colonna '{c}'.")
            st.stop()
    
    # Pulizia prezzo IT
    df_it["Price_IT"] = df_it["Buy Box: Current"].apply(pulisci_prezzo)
    
    # Riduciamo df_it
    df_it = df_it[["ASIN", "Title", "Bought in past month", "Price_IT"]]

    ########################################
    # 2) Mostriamo subitola LISTA di ASIN unificati (IT)
    ########################################
    if "ASIN" in df_it.columns:
        asins = df_it["ASIN"].dropna().unique()
        asins_text = "\n".join(asins)
        st.info("**Lista di ASIN (IT) unificati:**")
        st.text_area("Copia qui:", asins_text, height=150)
    else:
        st.warning("Nei file IT non è presente la colonna 'ASIN'. Impossibile mostrare la lista.")
    
    ########################################
    # 3) Creiamo il df_master partendo da df_it
    ########################################
    df_master = df_it.copy()

    # 4) Per ogni paese estero, uniamo
    for code, f_est in country_files.items():
        df_est = load_data(f_est)
        if df_est is None or df_est.empty:
            st.warning(f"Il file del paese {code} risulta vuoto o non caricato correttamente.")
            continue
        
        # Servono almeno "ASIN" e "Amazon: Current"
        if "ASIN" not in df_est.columns or "Amazon: Current" not in df_est.columns:
            st.warning(f"Nel file del paese {code} manca 'ASIN' o 'Amazon: Current'.")
            continue
        
        # Pulizia prezzo
        df_est[f"Price_{code}"] = df_est["Amazon: Current"].apply(pulisci_prezzo)
        
        # Se c'è "Delivery date", la rinominiamo
        if "Delivery date" in df_est.columns:
            df_est.rename(columns={"Delivery date": f"Delivery_{code}"}, inplace=True)
        
        # Teniamo le colonne significative
        keep_cols = ["ASIN", f"Price_{code}"]
        if f"Delivery_{code}" in df_est.columns:
            keep_cols.append(f"Delivery_{code}")
        
        df_est = df_est[keep_cols]
        
        # Merge sul df_master
        df_master = pd.merge(df_master, df_est, on="ASIN", how="left")
    
    # 5) Mostriamo la tabella unificata
    st.subheader("Tabella Unificata - Confronto Multi-Paesi")
    st.dataframe(df_master, height=600)
    
    # 6) Seleziona un prodotto per evidenziare i dettagli
    st.subheader("Dettagli Prodotto Selezionato")
    asins_all = df_master["ASIN"].dropna().unique()
    if len(asins_all) == 0:
        st.warning("Nessun ASIN trovato nel DF master.")
    else:
        selected_asin = st.selectbox("Scegli un ASIN da visualizzare", asins_all)
        if selected_asin:
            detail_df = df_master[df_master["ASIN"] == selected_asin]
            if not detail_df.empty:
                with st.expander("Dettagli del Prodotto", expanded=True):
                    st.table(detail_df.T)  # trasposto per visualizzare attributi in righe
            else:
                st.info("Nessun dettaglio per l'ASIN selezionato.")
    
    # 7) Download CSV
    csv_data = df_master.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica Tabella (CSV)",
        data=csv_data,
        file_name="confronto_multipaesi.csv",
        mime="text/csv"
    )
