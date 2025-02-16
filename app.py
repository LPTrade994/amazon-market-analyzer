import streamlit as st
import pandas as pd
import numpy as np

#########################################################
# Configurazione base
#########################################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Paesi con LOCALE e Diff%",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Confronto Multipaesi (colonna LOCALE)")

st.write("""
Carica qui i tuoi file CSV/XLSX (multipli). **Ognuno** deve contenere:
- **LOCALE** (es. "IT", "ES", "DE", ...)
- **ASIN**
- **Title**
- **Buy Box: Current** (prezzo)
- **Bought in past month** (opzionale, se è presente)

L’app unificherà tutti i file in un unico DataFrame e ti consentirà di:
1. Estrarre la **lista di ASIN** del mercato italiano.
2. Calcolare la **differenza percentuale** di prezzo fra l’Italia e gli altri paesi.
""")

#########################################################
# Sidebar per caricamento file
#########################################################
with st.sidebar:
    st.subheader("Caricamento File (CSV/XLSX)")
    uploaded_files = st.file_uploader(
        "Seleziona uno o più file",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )

    # Bottone per estrarre la lista di ASIN IT
    estrai_asin_it_button = st.button("Estrai ASIN IT")

    # Bottone per calcolare il raffronto dei prezzi
    calcola_diff_button = st.button("Confronta Prezzi (Multi-Paesi)")

#########################################################
# Funzioni di caricamento e pulizia
#########################################################
def load_file(file):
    if file is None:
        return None
    fname = file.name.lower()
    try:
        if fname.endswith(".xlsx"):
            df = pd.read_excel(file, dtype=str)
        else:  # csv
            try:
                df = pd.read_csv(file, sep=";", dtype=str)
            except:
                file.seek(0)
                df = pd.read_csv(file, sep=",", dtype=str)
        return df
    except:
        return None

def parse_price(s):
    """Rimuove simboli/virgole/spazi e converte in float."""
    if not isinstance(s, str):
        return None
    s = s.replace("€","").replace(" ","").replace(",",".")
    try:
        return float(s)
    except:
        return None

#########################################################
# 1) Se l'utente vuole estrarre ASIN IT
#########################################################
# Dobbiamo unire i file in un unico DataFrame "df_all"
df_all = pd.DataFrame()

if uploaded_files:
    list_df = []
    for f in uploaded_files:
        df_temp = load_file(f)
        if df_temp is not None and not df_temp.empty:
            list_df.append(df_temp)
    if list_df:
        df_all = pd.concat(list_df, ignore_index=True)

# Bottone "Estrai ASIN IT" => Subito
if estrai_asin_it_button:
    if df_all.empty:
        st.warning("Non ci sono dati caricati o i file sono vuoti.")
    else:
        # Assicuriamoci che ci sia la colonna LOCALE e ASIN
        if "LOCALE" in df_all.columns and "ASIN" in df_all.columns:
            # Filtriamo solo le righe con LOCALE == "IT"
            df_it = df_all[df_all["LOCALE"].str.upper() == "IT"]
            # Unione di tutti gli ASIN
            asins_it = df_it["ASIN"].dropna().unique()
            if len(asins_it) > 0:
                text_asins = "\n".join(asins_it)
                st.info("**ASIN mercato IT**")
                st.text_area("Copia qui la lista ASIN di IT:", text_asins, height=150)
            else:
                st.info("Non ci sono ASIN con LOCALE == 'IT'.")
        else:
            st.error("Manca la colonna 'LOCALE' o 'ASIN' nei dati caricati.")

#########################################################
# 2) Bottone per calcolare la differenza di prezzo
#########################################################
if calcola_diff_button:
    if df_all.empty:
        st.warning("Devi prima caricare i file!")
        st.stop()

    # Verifichiamo che ci siano almeno col LOCALE = IT per fare un raffronto
    if "LOCALE" not in df_all.columns:
        st.error("Manca la colonna 'LOCALE' nei file caricati.")
        st.stop()
    if "ASIN" not in df_all.columns:
        st.error("Manca la colonna 'ASIN' nei file caricati.")
        st.stop()
    if "Buy Box: Current" not in df_all.columns:
        st.error("Manca la colonna 'Buy Box: Current' nei file caricati.")
        st.stop()

    # Convertiamo "Buy Box: Current" in una colonna numerica "Price"
    df_all["Price"] = df_all["Buy Box: Current"].apply(parse_price)

    # Ora abbiamo le righe con (LOCALE, ASIN, Title, Price, etc.)
    # Se c'è "Bought in past month", la terremo. Altrimenti ignora.

    # Vogliamo pivotare i dati, in modo da avere:
    #   Index = ASIN
    #   Columns = Price_LOCALE
    #   Valori = Price
    # E anche Title e "Bought in past month" presi da LOCALE=IT.
    # In primo luogo, estraiamo Title e BpM dal LOCALE=IT:
    df_it = df_all[df_all["LOCALE"].str.upper() == "IT"].copy()
    # Teniamo la colonna Title e BPM. Se mancano, le gestiremo come facoltative
    # Esempio: potremmo creare un DF con "ASIN", "Title", "Bought in past month"
    keep_cols_it = ["ASIN"]
    if "Title" in df_it.columns:
        keep_cols_it.append("Title")
    if "Bought in past month" in df_it.columns:
        keep_cols_it.append("Bought in past month")

    # df_info_it con info uniche su ASIN (Title, BPM)
    df_info_it = df_it[keep_cols_it].drop_duplicates(subset=["ASIN"])

    # Pivot su Price => colonna "LOCALE" -> colonna Price_{LOCALE}
    # Creiamo un campo "LOCALE_UP" = LOCALE.upper(), per uniformare
    df_all["LOCALE_UP"] = df_all["LOCALE"].str.upper()
    df_pivot = df_all.pivot_table(
        index="ASIN",
        columns="LOCALE_UP",
        values="Price",
        aggfunc="mean"
    )

    # Ora df_pivot ha le colonne "IT", "ES", "DE", ...
    # Rinominiamo in Price_IT, Price_ES, ...
    new_cols = {}
    for c in df_pivot.columns:
        new_cols[c] = f"Price_{c}"
    df_pivot.rename(columns=new_cols, inplace=True)

    # Uniamo df_info_it su ASIN
    df_final = df_info_it.merge(
        df_pivot,
        how="left",
        on="ASIN"
    )

    # Ora calcoliamo la differenza percentuale per ogni colonna != Price_IT
    # Se Price_IT non esiste, impossibile calcolare
    if "Price_IT" not in df_final.columns:
        st.warning("Non è presente 'IT' come LOCALE. Impossibile calcolare differenze.")
    else:
        for c in df_final.columns:
            if c.startswith("Price_") and c != "Price_IT":
                diff_col = c.replace("Price_", "Diff%_")
                # Dif% = ((Price_IT - Price_locale)/ Price_IT)*100
                df_final[diff_col] = np.where(
                    (df_final["Price_IT"].notna()) & (df_final["Price_IT"]!=0) & (df_final[c].notna()),
                    ((df_final["Price_IT"] - df_final[c]) / df_final["Price_IT"]) * 100,
                    None
                )

    # Usiamo un ordinamento personalizzato se vuoi
    # Oppure lasciamo cosi. Esempio: ordiniamo per "ASIN"
    df_final.sort_values("ASIN", inplace=True)

    # Mostriamo la tabella
    st.subheader("Confronto Prezzi Multi-Paesi")
    st.dataframe(df_final, height=600)

    # Scarica CSV
    csv_data = df_final.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Finale",
        data=csv_data,
        file_name="confronto_multipaesi_diff.csv",
        mime="text/csv"
    )
