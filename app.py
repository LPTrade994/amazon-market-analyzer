import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Amazon Market Analyzer - Multi Paesi",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi Paesi")

#################################
# Sidebar: Caricamento multiplo di file
#################################
st.sidebar.subheader("Caricamento file (IT + altri Paesi)")
uploaded_files = st.sidebar.file_uploader(
    "Carica i file CSV/XLSX di tutti i Paesi (incluso IT)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

avvia_confronto = st.sidebar.button("Confronta Prezzi")

#################################
# Funzioni di caricamento / pulizia
#################################
def load_data(uploaded_file):
    """Carica dati da CSV o XLSX in un DataFrame."""
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
    """Converte una stringa contenente un prezzo in float."""
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(prezzo)
    except:
        return None

#################################
# Riconoscimento del Paese
#################################
def get_locale_from_data(df, fallback_filename):
    """
    Ritorna il codice del Paese:
      - Se c'è la colonna 'Locale' e contiene un unico valore, usa quello.
      - Altrimenti prova a estrarlo dal nome del file.
    """
    if "Locale" in df.columns:
        valori_locale = df["Locale"].dropna().unique()
        if len(valori_locale) == 1:
            return valori_locale[0]

    # Se non troviamo un valore univoco nella colonna "Locale",
    # proviamo dal nome file (esempio: "report_DE.csv" -> "DE")
    nome = fallback_filename.upper()
    for possibile_locale in ["IT", "DE", "FR", "ES", "UK", "US", "NL", "SE"]:
        if f"_{possibile_locale}." in nome:
            return possibile_locale

    # Se non riconosciamo nulla, mettiamo un fallback generico
    return "UNKNOWN"

#################################
# Elaborazione e Confronto
#################################
if avvia_confronto:
    if not uploaded_files:
        st.warning("Devi caricare almeno un file (incluso quello IT).")
        st.stop()

    # Dizionari per salvare i DataFrame
    df_it = None
    dict_mercati = {}  # { "DE": df_de, "FR": df_fr, ... }

    # Carichiamo tutti i file
    for f in uploaded_files:
        df_temp = load_data(f)
        if df_temp is None or df_temp.empty:
            st.warning(f"Il file {f.name} sembra vuoto o non valido.")
            continue

        # Identifichiamo il locale
        locale = get_locale_from_data(df_temp, f.name)

        # Salviamo in base al Paese
        if locale.lower() == "it":
            df_it = df_temp.copy()
        else:
            dict_mercati[locale] = df_temp.copy()

    # Controlli
    if df_it is None or df_it.empty:
        st.error("Non è stato trovato un file con Locale == 'IT'. Impossibile procedere.")
        st.stop()

    # Verifichiamo che le colonne essenziali esistano in IT
    col_asin = "ASIN"
    col_price_it = "Buy Box: Current"
    col_bought_it = "Bought in past month"

    for c in [col_asin, col_price_it, col_bought_it]:
        if c not in df_it.columns:
            st.error(f"Nel file IT manca la colonna '{c}'.")
            st.stop()

    # Puliamo i prezzi per IT
    df_it["Prezzo_IT"] = df_it[col_price_it].apply(pulisci_prezzo)

    # Prepariamo un DataFrame finale dove aggiungeremo le info di IT
    df_it = df_it[[col_asin, "Title", col_bought_it, "Prezzo_IT"]].drop_duplicates(subset=[col_asin])

    risultati_finali = []

    # Confrontiamo ogni Paese con IT
    for locale, df_mercato in dict_mercati.items():
        if col_asin not in df_mercato.columns:
            st.warning(f"Nel file di {locale} manca la colonna 'ASIN'. Saltato.")
            continue

        # Colonna prezzo per i Paesi esteri
        col_price_est = "Amazon: Current"
        if col_price_est not in df_mercato.columns:
            st.warning(f"Nel file di {locale} manca la colonna '{col_price_est}'. Saltato.")
            continue

        # Pulizia prezzi
        df_mercato["Prezzo_"+locale] = df_mercato[col_price_est].apply(pulisci_prezzo)

        # Teniamo solo le colonne utili
        df_mercato = df_mercato[[col_asin, "Prezzo_"+locale]]

        # Merge con IT (inner join su ASIN)
        df_merge = pd.merge(df_it, df_mercato, on=col_asin, how="inner")

        # Calcolo risparmio rispetto a IT
        df_merge["Risparmio_%_"+locale] = (
            (df_merge["Prezzo_IT"] - df_merge["Prezzo_"+locale]) / df_merge["Prezzo_IT"] * 100
        )

        # Filtriamo solo i casi dove il prezzo di questo locale è < IT
        df_filter = df_merge[df_merge["Prezzo_"+locale] < df_merge["Prezzo_IT"]].copy()

        # Ordiniamo in base al risparmio
        df_filter.sort_values(by="Risparmio_%_"+locale, ascending=False, inplace=True)

        # Aggiungiamo una colonna con l'informazione del Paese
        df_filter["Locale"] = locale

        # Salviamo per unione finale
        risultati_finali.append(df_filter)

    if risultati_finali:
        # Uniamo tutti i risultati
        df_risultati = pd.concat(risultati_finali, ignore_index=True)

        st.subheader("Confronto con IT - Risparmio trovati")
        st.dataframe(df_risultati, height=600)

        # Scarica CSV
        csv_data = df_risultati.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="Scarica CSV Confronto",
            data=csv_data,
            file_name="risultato_multi_paesi.csv",
            mime="text/csv"
        )
    else:
        st.info("Nessun confronto disponibile o nessun risparmio trovato.")
