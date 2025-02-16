import streamlit as st
import pandas as pd
from typing import Dict

########################################
# Configurazione base
########################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Paesi",
    page_icon="🔎",
    layout="wide"
)

# (Opzionale) un po' di CSS
st.markdown("""
<style>
.block-container {
    padding: 1rem 2rem;
}
.stButton button {
    background-color: #FF4B4B !important;
    color: #ffffff !important;
    border-radius: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

########################################
# Titolo
########################################
st.title("Amazon Market Analyzer - Confronto Multipli Paesi")
st.write("""
Carica i file:
- **Mercato Italiano**: multipli (ogni file con: ASIN, Title, Bought in past month, Buy Box: Current).
- **Paesi Esteri**: per ognuno, fornisci una **sigla** (ES, DE, FR...) e carica il file corrispondente (colonne: ASIN, Amazon: Current, Delivery date, ...).
Poi clicca "Unisci & Mostra" per vedere la tabella finale.
""")

########################################
# Sidebar - Caricamento
########################################
with st.sidebar:
    st.subheader("Caricamento File - Mercato IT")
    files_it = st.file_uploader(
        "Mercato IT (multipli)",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    
    st.subheader("Configura Paesi Esteri")
    # Numero di paesi
    num_countries = st.number_input(
        "Quanti paesi esteri vuoi confrontare?",
        min_value=0, max_value=10, value=2, step=1
    )
    
    # Creiamo una struttura per caricare i file di ogni paese
    country_files: Dict[str, st.uploaded_file_manager.UploadedFile] = {}
    for i in range(num_countries):
        st.write(f"**Paese # {i+1}**")
        country_code = st.text_input(
            f"Codice Paese (es: ES, DE, FR) n.{i+1}",
            key=f"country_code_{i}",
            value=f"ES{i}" if i>0 else "ES"  # default
        )
        file_est = st.file_uploader(
            f"File Estero {country_code}",
            type=["csv","xlsx"],
            key=f"file_est_{i}"
        )
        if file_est and country_code.strip():
            country_files[country_code.strip()] = file_est
    
    # Bottone per unire e mostrare
    unify_button = st.button("Unisci & Mostra")

########################################
# Funzioni di caricamento / pulizia
########################################
def load_data(uploaded_file):
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    try:
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
    except:
        return None

def pulisci_prezzo(raw):
    if not isinstance(raw, str):
        return None
    x = raw.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(x)
    except:
        return None

########################################
# Se l'utente clicca "Unisci & Mostra"
########################################
if unify_button:
    # 1) Carichiamo e uniamo i file IT
    if not files_it:
        st.error("Devi caricare almeno un file per il Mercato Italiano.")
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
    
    # Controllo colonne base IT
    it_cols_needed = ["ASIN", "Title", "Bought in past month", "Buy Box: Current"]
    for c in it_cols_needed:
        if c not in df_it.columns:
            st.error(f"Nei file IT manca la colonna '{c}'.")
            st.stop()
    # Pulizia prezzo IT
    df_it["Price_IT"] = df_it["Buy Box: Current"].apply(pulisci_prezzo)
    
    # Riduciamo df_it a quelle colonne
    df_it = df_it[["ASIN", "Title", "Bought in past month", "Price_IT"]]
    
    # 2) Per ogni Paese estero, carichiamo e uniamo
    df_master = df_it.copy()  # partiamo da qui
    for code, f_est in country_files.items():
        df_est = load_data(f_est)
        if df_est is None or df_est.empty:
            st.warning(f"Il file per il paese {code} non è stato caricato correttamente.")
            continue
        
        # ipotizziamo contenga almeno: ASIN, Amazon: Current, Delivery date
        # ma potrebbe contenere altre colonne... che potresti voler gestire
        if "ASIN" not in df_est.columns or "Amazon: Current" not in df_est.columns:
            st.warning(f"Nel file del paese {code} manca ASIN o Amazon: Current.")
            continue
        
        # Pulizia prezzo
        df_est[f"Price_{code}"] = df_est["Amazon: Current"].apply(pulisci_prezzo)
        
        # Se c'è la colonna "Delivery date", la rinominiamo in f"Delivery_{code}"
        # Se non c'è, pazienza
        if "Delivery date" in df_est.columns:
            df_est.rename(columns={"Delivery date": f"Delivery_{code}"}, inplace=True)
        
        # Riduciamo df_est
        keep_cols = ["ASIN", f"Price_{code}"]
        if f"Delivery_{code}" in df_est.columns:
            keep_cols.append(f"Delivery_{code}")
        
        # Potresti voler includere altre eventuali colonne (es. "Risparmio" ECC),
        # ma per ora ci limitiamo a price + delivery.
        df_est = df_est[keep_cols]
        
        # Merge con df_master su ASIN
        df_master = pd.merge(df_master, df_est, on="ASIN", how="left")
    
    # A questo punto df_master contiene IT e tutti i paesi (con col Price_ES, Delivery_ES, etc.)
    # Ad esempio, potresti calcolare risparmio per ogni paese, ma ciò richiede definire una logica.
    
    # 3) Mostra la tabella unificata
    st.subheader("Tabella Unificata")
    st.dataframe(df_master, height=600)
    
    # 4) Creiamo un selectbox per evidenziare un prodotto
    all_asins = df_master["ASIN"].dropna().unique()
    selected_asin = st.selectbox("Seleziona un prodotto per i dettagli", all_asins)
    if selected_asin:
        df_product = df_master[df_master["ASIN"] == selected_asin]
        if not df_product.empty:
            st.markdown("**Dettagli Prodotto Selezionato**:")
            # Mostriamo in una tabella orizzontale (o potresti farlo con st.write)
            st.table(df_product.T)  # trasposta per vedere righe come attributi
        else:
            st.info("Nessun dettaglio per l'ASIN selezionato.")
    
    # 5) Bottone per scaricare CSV
    csv_data = df_master.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        "Scarica Tabella (CSV)",
        data=csv_data,
        file_name="confronto_multipaesi.csv",
        mime="text/csv"
    )
