import streamlit as st
import pandas as pd

##################################
# Configura la pagina e layout
##################################
st.set_page_config(
    page_title="Amazon Market Analyzer (Multi-file IT)",
    page_icon="🔎",
    layout="wide"
)

##################################
# Eventuale CSS o config TOML per dark mode (opzionale)
##################################
st.markdown("""
<style>
.block-container {
    padding: 1rem 2rem;
}
.stButton button {
    background-color: #FF4B4B !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

##################################
# Titolo
##################################
st.title("Amazon Market Analyzer - Caricamento multiplo Mercato IT")

st.write("""
- **Mercato Italiano**: puoi caricare **più file** (CSV o XLSX). Saranno **uniti** in un unico elenco.  
- **Mercato Estero**: carica un **solo file** (CSV o XLSX).  
- L’app confronterà i prezzi (colonne `Buy Box: Current` vs `Amazon: Current`) e mostrerà i prodotti più convenienti all’estero.
""")

##################################
# Sidebar: multi-file per IT, singolo file per EST
##################################
with st.sidebar:
    st.subheader("Carica i file")
    # accettiamo più file per il mercato IT
    files_ita = st.file_uploader(
        "Mercato IT (CSV/XLSX) - multipli",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    # un solo file per il mercato EST
    file_est = st.file_uploader(
        "Mercato EST (CSV/XLSX) - singolo",
        type=["csv","xlsx"],
        accept_multiple_files=False
    )

    avvia_confronto = st.button("Confronta Prezzi")

##################################
# Funzione generica di caricamento
##################################
def load_data(uploaded_file):
    """
    Carica un singolo file CSV/XLSX e restituisce un DataFrame con dtype str.
    Gestisce ; e , per i CSV, e openpyxl per XLSX.
    """
    if not uploaded_file:
        return None
    filename = uploaded_file.name.lower()

    # Se .xlsx
    if filename.endswith(".xlsx"):
        # richiede openpyxl installato
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

##################################
# Funzione pulizia prezzo
##################################
def pulisci_prezzo(prezzo_raw):
    """
    Rimuove simboli € e spazi, converte virgole in punti, infine float.
    """
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(prezzo)
    except:
        return None

##################################
# Logica eseguita dopo click
##################################
if avvia_confronto:
    # Controlliamo se abbiamo almeno 1 file in IT e 1 file in EST
    if len(files_ita) == 0:
        st.warning("Devi caricare almeno un file per il Mercato IT.")
        st.stop()

    if not file_est:
        st.warning("Devi caricare il file per il Mercato EST.")
        st.stop()

    # Carichiamo TUTTI i file IT in una lista di DataFrame
    df_ita_list = []
    for f in files_ita:
        df_temp = load_data(f)
        if df_temp is not None:
            df_ita_list.append(df_temp)

    # Se la lista è vuota, probabilmente c'è un errore
    if len(df_ita_list) == 0:
        st.error("Non sono riuscito a caricare alcun file IT.")
        st.stop()

    # Concatenazione di tutti i DF IT in uno solo
    df_ita = pd.concat(df_ita_list, ignore_index=True)

    # Carichiamo il file EST
    df_est = load_data(file_est)
    if df_est is None:
        st.error("Non riesco a caricare il file EST.")
        st.stop()

    # Colonne attese
    col_asin = "ASIN"
    col_title_it = "Title"
    col_price_it = "Buy Box: Current"
    col_price_est = "Amazon: Current"

    # Verifica colonne essenziali in df_ita
    for c in [col_asin, col_title_it, col_price_it]:
        if c not in df_ita.columns:
            st.error(f"Nel Mercato IT manca la colonna '{c}'.")
            st.stop()
    # Verifica in df_est
    for c in [col_asin, col_price_est]:
        if c not in df_est.columns:
            st.error(f"Nel Mercato EST manca la colonna '{c}'.")
            st.stop()

    # Pulizia prezzi
    df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
    df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

    df_ita = df_ita[[col_asin, col_title_it, "Prezzo_IT"]]
    df_est = df_est[[col_asin, "Prezzo_Est"]]

    # Merge su ASIN
    df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

    # Calcolo differenza percentuale
    df_merged["Risparmio_%"] = (
        (df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"]) 
        / df_merged["Prezzo_IT"] * 100
    )

    # Filtra prodotti con Prezzo_Est < Prezzo_IT
    df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

    # Ordina in ordine decrescente
    df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

    # Seleziona colonne finali
    df_finale = df_filtered[[col_asin, col_title_it, "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]]

    # Output
    st.subheader("Risultati di Confronto")
    st.dataframe(df_finale, height=600)

    # Bottone per scaricare CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica Risultati (CSV)",
        data=csv_data,
        file_name="risultato_convenienza.csv",
        mime="text/csv"
    )
