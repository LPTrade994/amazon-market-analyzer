import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Amazon Market Analyzer - Multi IT + 'Bought in past month'",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi IT + Vendite (Bought in past month)")

# Altre parti di layout, CSS, etc. come preferisci

#################################
# Caricamento multiplo IT e singolo EST
#################################
with st.sidebar:
    st.subheader("Caricamento file")
    files_ita = st.file_uploader(
        "Mercato IT (CSV/XLSX) - multipli",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    file_est = st.file_uploader(
        "Mercato EST (CSV/XLSX) - singolo",
        type=["csv","xlsx"]
    )
    avvia_confronto = st.button("Confronta Prezzi")

#################################
# Funzioni di caricamento / pulizia
#################################
def load_data(uploaded_file):
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    if fname.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str)
        return df
    else:
        # csv
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def pulisci_prezzo(prezzo_raw):
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(prezzo)
    except:
        return None

#################################
# 1) Unione multipli file IT e visualizzazione ASIN
#################################
df_ita = None
if files_ita:
    df_ita_list = []
    for f in files_ita:
        dftemp = load_data(f)
        if dftemp is not None:
            df_ita_list.append(dftemp)
    if df_ita_list:
        df_ita = pd.concat(df_ita_list, ignore_index=True)
        
        if "ASIN" in df_ita.columns:
            asins = df_ita["ASIN"].dropna().unique()
            asins_text = "\n".join(asins)
            st.info("**Lista di ASIN (IT) unificati:**")
            st.text_area("Copia qui:", asins_text, height=200)
        else:
            st.warning("Nei file IT non è presente la colonna 'ASIN'. Impossibile mostrare la lista.")

#################################
# 2) Confronto prezzi al click
#################################
if avvia_confronto:
    if not files_ita:
        st.warning("Devi prima caricare i file IT.")
        st.stop()
    if not file_est:
        st.warning("Devi caricare il file EST.")
        st.stop()
    if df_ita is None or df_ita.empty:
        st.error("L'elenco IT sembra vuoto o non caricato correttamente.")
        st.stop()

    df_est = load_data(file_est)
    if df_est is None or df_est.empty:
        st.error("Il file EST è vuoto o non caricato correttamente.")
        st.stop()

    # Definizione colonne
    col_asin = "ASIN"
    col_title_it = "Title"
    col_price_it = "Buy Box: Current"
    col_bought_it = "Bought in past month"  # <--- nuova colonna per vendite
    col_price_est = "Amazon: Current"

    # Verifica che esistano
    for c in [col_asin, col_title_it, col_price_it, col_bought_it]:
        if c not in df_ita.columns:
            st.error(f"Nel Mercato IT manca la colonna '{c}'.")
            st.stop()
    if col_asin not in df_est.columns or col_price_est not in df_est.columns:
        st.error(f"Nel Mercato EST manca '{col_asin}' o '{col_price_est}'.")
        st.stop()

    # Pulizia prezzi
    df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
    df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

    # Seleziona le colonne IT: includiamo "Bought in past month"
    df_ita = df_ita[[col_asin, col_title_it, col_bought_it, "Prezzo_IT"]]

    # Seleziona le colonne EST
    df_est = df_est[[col_asin, "Prezzo_Est"]]

    # Merge
    df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

    # Calcolo differenza
    df_merged["Risparmio_%"] = (
        (df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"]) / df_merged["Prezzo_IT"] * 100
    )

    # Filtra con prezzo est < IT
    df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

    # Ordina decrescente
    df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

    # Seleziona le colonne finali: includiamo "Bought in past month"
    df_finale = df_filtered[
        [col_asin, col_title_it, col_bought_it, "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]
    ]

    st.subheader("Risultati di Confronto")
    st.dataframe(df_finale, height=600)

    # Scarica CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV",
        data=csv_data,
        file_name="risultato_convenienza.csv",
        mime="text/csv"
    )
