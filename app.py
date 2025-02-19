import streamlit as st
import pandas as pd

#################################
# Impostazioni pagina
#################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Sales Rank + 30 days",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Con Sales Rank (Corrente e Media 30 giorni)")

st.write("""
Carica più file di **Origine** (con colonna `Locale`, `ASIN`, `Title`, `Sales Rank: Current`, `Sales Rank: 30 days avg.`, 
`Bought in past month`, `Buy Box: Current`, ecc.) e **1 file** di Confronto, 
poi clicca "Confronta Prezzi" per vedere le differenze e includere nel risultato il rank attuale e medio 30 giorni.
""")

#################################
# Sidebar: multi-file Origine + singolo Confronto
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
        type=["csv","xlsx"]
    )
    
    go_button = st.button("Confronta Prezzi")

#################################
# Funzioni di caricamento e pulizia
#################################
def load_data(uploaded_file):
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    try:
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
    except:
        return None

def pulisci_prezzo(value):
    if not isinstance(value, str):
        return None
    tmp = value.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(tmp)
    except:
        return None

#################################
# 1) Unione multipli file Origine
#################################
df_origin = None
if files_origin:
    df_list = []
    for f in files_origin:
        dftemp = load_data(f)
        if dftemp is not None and not dftemp.empty:
            df_list.append(dftemp)
    if df_list:
        df_origin = pd.concat(df_list, ignore_index=True)
        
        # Mostriamo la lista di ASIN se presente
        if "ASIN" in df_origin.columns:
            asins = df_origin["ASIN"].dropna().unique()
            asins_text = "\n".join(asins)
            st.info("**Lista di ASIN (Origine) unificati:**")
            st.text_area("Copia qui:", asins_text, height=150)
        else:
            st.warning("Nei file di Origine non c'è la colonna 'ASIN'. Impossibile mostrare la lista.")
    else:
        st.warning("Nessuno dei file di Origine è stato caricato correttamente.")

#################################
# 2) Confronto prezzi
#################################
if go_button:
    # Verifiche
    if not files_origin:
        st.warning("Devi caricare file di Origine.")
        st.stop()
    if not file_comp:
        st.warning("Devi caricare il file di Confronto.")
        st.stop()
    if df_origin is None or df_origin.empty:
        st.error("I file di Origine sembrano vuoti o non corretti.")
        st.stop()
    
    df_comp = load_data(file_comp)
    if df_comp is None or df_comp.empty:
        st.error("Il file di Confronto è vuoto o non corretto.")
        st.stop()

    # Definizione colonne
    col_locale   = "Locale"
    col_asin     = "ASIN"
    col_title    = "Title"
    col_srank_cur  = "Sales Rank: Current"
    col_srank_30   = "Sales Rank: 30 days avg."
    col_bought   = "Bought in past month"
    col_price_orig = "Buy Box: Current"
    col_price_comp = "Amazon: Current"

    # Verifica che esistano nei file di Origine
    needed_cols_orig = [
        col_locale, col_asin, col_title, 
        col_srank_cur, col_srank_30, 
        col_bought, col_price_orig
    ]
    for c in needed_cols_orig:
        if c not in df_origin.columns:
            st.error(f"Nei file di Origine manca la colonna '{c}'.")
            st.stop()

    # Verifica in Confronto
    if col_asin not in df_comp.columns or col_price_comp not in df_comp.columns:
        st.error(f"Nella tabella di Confronto manca '{col_asin}' o '{col_price_comp}'.")
        st.stop()

    # Pulizia prezzo
    df_origin["Prezzo_Orig"] = df_origin[col_price_orig].apply(pulisci_prezzo)
    df_comp["Prezzo_Comp"]   = df_comp[col_price_comp].apply(pulisci_prezzo)

    # Riduciamo i df
    # Includiamo le 2 colonne rank
    df_origin = df_origin[
        [col_locale, col_asin, col_title, 
         col_srank_cur, col_srank_30,
         col_bought, "Prezzo_Orig"]
    ]
    df_comp = df_comp[[col_asin, "Prezzo_Comp"]]

    # Merge su ASIN
    df_merged = pd.merge(df_origin, df_comp, on=col_asin, how="inner")

    # Calcolo differenza
    df_merged["Risparmio_%"] = (
        (df_merged["Prezzo_Orig"] - df_merged["Prezzo_Comp"]) 
        / df_merged["Prezzo_Orig"] * 100
    )
    # Filtra
    df_filtered = df_merged[df_merged["Prezzo_Comp"] < df_merged["Prezzo_Orig"]]
    # Ordina
    df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

    # Costruiamo la tabella finale con i rank
    df_finale = df_filtered[
        [
            col_locale, col_asin, col_title,
            col_srank_cur, col_srank_30,
            col_bought, "Prezzo_Orig", "Prezzo_Comp", "Risparmio_%"
        ]
    ]

    st.subheader("Risultati di Confronto con Sales Rank")
    st.dataframe(df_finale, height=600)

    # Bottone download
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV",
        data=csv_data,
        file_name="risultato_convenienza.csv",
        mime="text/csv"
    )
