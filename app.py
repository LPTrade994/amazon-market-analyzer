import streamlit as st
import pandas as pd

########################################
# Configurazione base
########################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Paesi (Locale) con Diff%",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi Paesi con Diff% e lista ASIN IT")
st.write("""
Carica qui i file (CSV/XLSX). Ogni file deve contenere:
- **Locale** (es. "it", "es", "de" ecc.)
- **ASIN**
- **Title**
- **Buy Box: Current** (prezzo principale)
- **Amazon: Current** (prezzo secondario)
- [Facoltativo] **Bought in past month**

Il programma:
1. Unifica tutti i file caricati in un unico elenco.
2. **Estraggo** subito gli ASIN di `Locale == "it"` (bottone).
3. **Confronto** i prezzi calcolando la differenza percentuale per ogni riga.
4. Mostro l'elenco globale, comprensivo di tutti i Paesi, con la colonna `Diff%`.
""")

########################################
# Sidebar per caricamento
########################################
with st.sidebar:
    st.subheader("Carica i file (CSV/XLSX)")
    uploaded_files = st.file_uploader(
        "Puoi selezionare uno o più file",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    estrai_asin_button = st.button("Estrai ASIN (Locale=it)")
    confronta_button = st.button("Confronta Prezzi (Calcolo Diff%)")

########################################
# Funzioni di caricamento e pulizia
########################################
def load_file(file):
    if file is None:
        return None
    fname = file.name.lower()
    try:
        # Togliamo spazi dal nome delle colonne
        if fname.endswith(".xlsx"):
            df = pd.read_excel(file, dtype=str)
        else:  # csv
            try:
                df = pd.read_csv(file, sep=";", dtype=str)
            except:
                file.seek(0)
                df = pd.read_csv(file, sep=",", dtype=str)

        # Rimuoviamo eventuali spazi dai nomi di colonna
        df.columns = df.columns.str.strip()

        return df
    except:
        return None

def parse_price(s):
    """Converte la stringa prezzo in float, rimuovendo simboli e virgole."""
    if not isinstance(s, str):
        return None
    s = s.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(s)
    except:
        return None

########################################
# Unifichiamo subito i file caricati
########################################
df_all = None
if uploaded_files:
    list_dfs = []
    for file in uploaded_files:
        df_temp = load_file(file)
        if df_temp is not None and not df_temp.empty:
            list_dfs.append(df_temp)
    if list_dfs:
        df_all = pd.concat(list_dfs, ignore_index=True)

########################################
# 1) Bottone "Estrai ASIN (Locale=it)"
########################################
if estrai_asin_button:
    if df_all is None or df_all.empty:
        st.warning("Non ci sono dati caricati, o i file sono vuoti.")
    else:
        # Verifichiamo esistenza colonna "Locale" e "ASIN"
        if "Locale" not in df_all.columns or "ASIN" not in df_all.columns:
            st.error("Manca la colonna 'Locale' o 'ASIN' nei dati caricati.")
        else:
            # Filtriamo righe con Locale == "it" (senza spazi)
            df_it = df_all[df_all["Locale"].str.lower() == "it"]
            asins_it = df_it["ASIN"].dropna().unique()
            if len(asins_it) == 0:
                st.info("Nessun ASIN trovato con 'Locale=it'.")
            else:
                text_asins = "\n".join(asins_it)
                st.info("**ASIN di Locale=it:**")
                st.text_area("Copia da qui:", text_asins, height=150)

########################################
# 2) Bottone "Confronta Prezzi (Calcolo Diff%)"
########################################
if confronta_button:
    if df_all is None or df_all.empty:
        st.warning("Non ci sono dati validi da confrontare.")
        st.stop()

    # Controlliamo che esistano le colonne minime
    needed_cols = ["Locale", "ASIN", "Buy Box: Current", "Amazon: Current"]
    for c in needed_cols:
        if c not in df_all.columns:
            st.error(f"Manca la colonna '{c}' nei file caricati.")
            st.stop()

    # Creiamo colonna numerica per Buy Box e Amazon
    df_all["BuyBox_num"] = df_all["Buy Box: Current"].apply(parse_price)
    df_all["Amazon_num"] = df_all["Amazon: Current"].apply(parse_price)

    # Calcoliamo la differenza in percentuale
    # Diff% = ((BuyBox_num - Amazon_num) / BuyBox_num)*100
    df_all["Diff%"] = None
    mask_valid = (df_all["BuyBox_num"].notna()) & (df_all["BuyBox_num"] != 0) & (df_all["Amazon_num"].notna())
    df_all.loc[mask_valid, "Diff%"] = (
        (df_all.loc[mask_valid, "BuyBox_num"] - df_all.loc[mask_valid, "Amazon_num"])
        / df_all.loc[mask_valid, "BuyBox_num"] * 100
    )

    # Possiamo selezionare le colonne finali
    # Se "Bought in past month" esiste, la includiamo
    final_cols = []
    # Controllo se la colonna esiste
    if "Locale" in df_all.columns:
        final_cols.append("Locale")
    if "ASIN" in df_all.columns:
        final_cols.append("ASIN")
    if "Title" in df_all.columns:
        final_cols.append("Title")
    if "Bought in past month" in df_all.columns:
        final_cols.append("Bought in past month")

    # Rimetto le originali "Buy Box: Current" e "Amazon: Current" e la "Diff%"
    final_cols += ["Buy Box: Current", "Amazon: Current", "Diff%"]

    # Creiamo un DataFrame finale
    df_final = df_all[final_cols].copy()

    # Ordiniamo se vogliamo ad es. per "Locale" e "ASIN"
    df_final.sort_values(by=["Locale","ASIN"], inplace=True)

    st.subheader("Risultati Confronto Prezzi (Diff%)")
    st.dataframe(df_final, height=600)

    # Bottone di download CSV
    csv_data = df_final.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati",
        data=csv_data,
        file_name="confronto_multi_locale.csv",
        mime="text/csv"
    )
