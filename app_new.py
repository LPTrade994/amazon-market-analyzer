import streamlit as st
import pandas as pd

# Impostazioni di pagina
st.set_page_config(
    page_title="Amazon Market Analyzer",
    page_icon="🔎",
    layout="wide"
)

# Un po' di CSS personalizzato
st.markdown("""
<style>
/* Riduci i margini e i padding */
.block-container {
    padding: 1rem 2rem 1rem 2rem;
}

/* Forza un colore personalizzato sui pulsanti (override del config theme) */
.stButton button {
    background-color: #FF4B4B !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Amazon Market Analyzer")
st.write("Confronto prezzi tra mercato italiano ed estero")

###################################
# Sidebar con i file uploader
###################################
with st.sidebar:
    st.subheader("Carica i file")
    file_ita = st.file_uploader("Mercato ITA (CSV/XLSX)", type=["csv","xlsx"])
    file_est = st.file_uploader("Mercato EST (CSV/XLSX)", type=["csv","xlsx"])
    avvia_confronto = st.button("Confronta Prezzi")

###################################
# Funzione di caricamento
###################################
def load_data(uploaded_file):
    if not uploaded_file:
        return None
    filename = uploaded_file.name.lower()
    # Se .xlsx, usa pd.read_excel
    if filename.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str)
        return df
    else:
        # CSV, prova ; altrimenti ,
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

###################################
# Funzione di pulizia prezzi
###################################
def pulisci_prezzo(prezzo_raw):
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(prezzo)
    except:
        return None

###################################
# Se l'utente ha cliccato "Confronta Prezzi"
###################################
if avvia_confronto:
    if file_ita and file_est:
        # Carica i dati
        df_ita = load_data(file_ita)
        df_est = load_data(file_est)

        # Verifica di averli caricati correttamente
        if df_ita is None or df_est is None:
            st.error("Errore nel caricamento dei file.")
            st.stop()

        # Definizione colonne
        col_asin = "ASIN"
        col_title_it = "Title"
        col_price_it = "Buy Box: Current"
        col_price_est = "Amazon: Current"

        # Controlla che le colonne esistano
        for c in [col_asin, col_title_it, col_price_it]:
            if c not in df_ita.columns:
                st.error(f"Colonna '{c}' non trovata nel file ITA.")
                st.stop()

        for c in [col_asin, col_price_est]:
            if c not in df_est.columns:
                st.error(f"Colonna '{c}' non trovata nel file EST.")
                st.stop()

        # Pulizia prezzi
        df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
        df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

        df_ita = df_ita[[col_asin, col_title_it, "Prezzo_IT"]]
        df_est = df_est[[col_asin, "Prezzo_Est"]]

        # Merge su ASIN
        df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

        # Calcolo risparmio
        df_merged["Risparmio_%"] = ((df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"])
                                    / df_merged["Prezzo_IT"] * 100)

        # Prodotti convenienti (Prezzo_Est < Prezzo_IT)
        df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

        # Ordine decrescente
        df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

        df_finale = df_filtered[[col_asin, col_title_it, "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]]

        # Mostra tabella
        st.subheader("Risultati di confronto")
        st.dataframe(df_finale, height=500)

        # Bottone download CSV
        csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("Scarica CSV", data=csv_data,
                           file_name="risultato_convenienza.csv",
                           mime="text/csv")
    else:
        st.warning("Devi caricare entrambi i file per procedere al confronto.")

