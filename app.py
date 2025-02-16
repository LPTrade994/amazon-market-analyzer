import streamlit as st
import pandas as pd

#################################
# Impostazioni pagina Streamlit
#################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Origine con Paese",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi Origine (Paesi Vari) + Vendite")

st.write("""
Carica più file di **origine** (ognuno può essere Italia, Germania, Spagna, ecc., con colonna `Locale` che indica il paese, 
oltre a `ASIN`, `Title`, `Bought in past month`, `Buy Box: Current`).  
Poi carica **1 file** di confronto (Competitor), con almeno `ASIN`, `Amazon: Current`.  
Clicca su "Confronta Prezzi" per ottenere i risultati, includendo vendite (`Bought in past month`) e prezzo competitor.
""")

#################################
# Sidebar: multi-file origine + singolo competitor
#################################
with st.sidebar:
    st.subheader("Caricamento file")
    files_origin = st.file_uploader(
        "File di Origine (CSV/XLSX) - multipli",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    file_comp = st.file_uploader(
        "File di Confronto (CSV/XLSX) - singolo",
        type=["csv","xlsx"],
        accept_multiple_files=False
    )
    avvia_confronto = st.button("Confronta Prezzi")

#################################
# Funzioni di caricamento / pulizia
#################################
def load_data(uploaded_file):
    """Carica un singolo CSV/XLSX e restituisce un DataFrame (tutte stringhe)."""
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
    """Rimuove simboli, spazi e converte virgole in punti, restituendo float."""
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(prezzo)
    except:
        return None

#################################
# 1) Unione multipli file Origine
#    e Visualizzazione ASIN
#################################
df_origin = None
if files_origin:
    df_list_origin = []
    for f in files_origin:
        dftemp = load_data(f)
        if dftemp is not None and not dftemp.empty:
            df_list_origin.append(dftemp)
    if df_list_origin:
        df_origin = pd.concat(df_list_origin, ignore_index=True)
        
        # Se troviamo la colonna "ASIN", mostriamo la lista unificata
        if "ASIN" in df_origin.columns:
            asins = df_origin["ASIN"].dropna().unique()
            asins_text = "\n".join(asins)
            st.info("**Lista di ASIN (Origine) unificati:**")
            st.text_area("Copia qui:", asins_text, height=200)
        else:
            st.warning("Nei file di Origine non è presente la colonna 'ASIN'. Impossibile mostrare la lista.")

#################################
# 2) Confronto prezzi al click
#################################
if avvia_confronto:
    # Controlli base
    if not files_origin:
        st.warning("Devi prima caricare i file di Origine (multipli).")
        st.stop()
    if not file_comp:
        st.warning("Devi caricare il file di Confronto (singolo).")
        st.stop()
    if df_origin is None or df_origin.empty:
        st.error("L'elenco di Origine sembra vuoto o non caricato correttamente.")
        st.stop()

    df_comp = load_data(file_comp)
    if df_comp is None or df_comp.empty:
        st.error("Il file di Confronto è vuoto o non caricato correttamente.")
        st.stop()

    # Definizione colonne
    col_locale = "Locale"          # indica il paese di riferimento nel file di origine
    col_asin = "ASIN"
    col_title = "Title"
    col_bought = "Bought in past month"
    col_price_orig = "Buy Box: Current"
    col_price_comp = "Amazon: Current"

    # Verifica che esistano nelle Origine
    for c in [col_locale, col_asin, col_title, col_bought, col_price_orig]:
        if c not in df_origin.columns:
            st.error(f"Nei file di Origine manca la colonna '{c}'.")
            st.stop()

    # Verifica che esistano nel Confronto
    if col_asin not in df_comp.columns or col_price_comp not in df_comp.columns:
        st.error(f"Nella tabella di Confronto manca '{col_asin}' o '{col_price_comp}'.")
        st.stop()

    # Pulizia prezzi
    df_origin["Prezzo_Orig"] = df_origin[col_price_orig].apply(pulisci_prezzo)
    df_comp["Prezzo_Comp"] = df_comp[col_price_comp].apply(pulisci_prezzo)

    # Riduciamo i df
    df_origin = df_origin[[col_locale, col_asin, col_title, col_bought, "Prezzo_Orig"]]
    df_comp = df_comp[[col_asin, "Prezzo_Comp"]]

    # Merge su ASIN
    df_merged = pd.merge(df_origin, df_comp, on=col_asin, how="inner")

    # Calcolo differenza in percentuale
    df_merged["Risparmio_%"] = (
        (df_merged["Prezzo_Orig"] - df_merged["Prezzo_Comp"]) 
        / df_merged["Prezzo_Orig"] * 100
    )

    # Filtriamo i soli prodotti dove il competitor è < Origine
    df_filtered = df_merged[df_merged["Prezzo_Comp"] < df_merged["Prezzo_Orig"]]

    # Ordiniamo in decrescente per la % di risparmio
    df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

    # Selezioniamo le colonne finali
    df_finale = df_filtered[
        [col_locale, col_asin, col_title, col_bought, 
         "Prezzo_Orig", "Prezzo_Comp", "Risparmio_%"]
    ]

    st.subheader("Risultati di Confronto")

    # Mostra la tabella
    st.dataframe(df_finale, height=600)

    # Download CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV",
        data=csv_data,
        file_name="risultato_convenienza.csv",
        mime="text/csv"
    )
