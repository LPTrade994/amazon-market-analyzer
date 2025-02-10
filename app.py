import streamlit as st
import pandas as pd

##################################
# Configurazione della pagina
##################################
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi IT + Copia ASIN",
    page_icon="🔎",
    layout="wide"
)

##################################
# Eventuale CSS personalizzato
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
# Titolo app
##################################
st.title("Amazon Market Analyzer - Caricamento multiplo IT + Copia ASIN")

st.write("""
**Funzionalità principali**:
1. Carica **più file** CSV/XLSX per il **mercato italiano**. L’app concatena in un unico elenco.
2. Visualizza **subito** la lista degli ASIN italiani, così puoi copiarli e generare il file estero in modo rapido.
3. Infine, carica il **file estero** (un solo file) e premi **Confronta Prezzi** per ottenere l’analisi.
""")

##################################
# Sidebar: multi-file IT + singolo EST
##################################
with st.sidebar:
    st.subheader("Caricamento file")
    
    # Più file mercato IT
    files_ita = st.file_uploader(
        "Mercato IT (CSV/XLSX) - multipli",
        type=["csv","xlsx"],
        accept_multiple_files=True
    )
    
    # Singolo file EST
    file_est = st.file_uploader(
        "Mercato EST (CSV/XLSX) - singolo",
        type=["csv","xlsx"],
        accept_multiple_files=False
    )
    
    # Bottone per l'analisi finale
    avvia_confronto = st.button("Confronta Prezzi")

##################################
# Funzioni di caricamento/pulizia
##################################
def load_data(uploaded_file):
    """Carica un singolo CSV/XLSX in un DataFrame di stringhe."""
    if not uploaded_file:
        return None
    filename = uploaded_file.name.lower()

    if filename.endswith(".xlsx"):
        # richiede openpyxl installato
        df = pd.read_excel(uploaded_file, dtype=str)
        return df
    else:
        # CSV: tenta ; altrimenti ,
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def pulisci_prezzo(prezzo_raw):
    """Rimuove simboli, spazi, virgole e converte in float."""
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(prezzo)
    except:
        return None

##################################
# 1) Non appena carico i file IT,
#    unisco e mostro la lista ASIN
##################################
df_ita = None  # inizializziamo

if files_ita:
    # Unisco in un unico DataFrame
    df_ita_list = []
    for f in files_ita:
        df_temp = load_data(f)
        if df_temp is not None:
            df_ita_list.append(df_temp)
    
    if len(df_ita_list) > 0:
        df_ita = pd.concat(df_ita_list, ignore_index=True)
        
        # Verifica che la colonna "ASIN" esista
        if "ASIN" not in df_ita.columns:
            st.error("Nei file IT non c'è la colonna ASIN. Impossibile mostrare la lista.")
        else:
            # Estraiamo tutti gli ASIN (dropna + unique)
            asins = df_ita["ASIN"].dropna().unique()
            # Creiamo una stringa con un ASIN per riga
            asins_text = "\n".join(asins)
            
            st.info("**Ecco la lista di ASIN italiani unificati:**")
            st.text_area(
                "Copia qui sotto:",
                asins_text,
                height=200
            )
    else:
        st.warning("Nessuno dei file IT caricati è stato letto correttamente. Niente da mostrare.")

##################################
# 2) Se premi "Confronta Prezzi",
#    carichiamo anche EST e uniamo
##################################
if avvia_confronto:
    # Devi avere almeno 1 file IT e 1 file EST
    if not files_ita:
        st.warning("Devi prima caricare uno o più file per il Mercato IT.")
        st.stop()
    if not file_est:
        st.warning("Devi caricare il file per il Mercato EST.")
        st.stop()

    # df_ita già creato in precedenza
    if df_ita is None or df_ita.empty:
        st.error("Errore: l'elenco IT sembra vuoto o non caricato correttamente.")
        st.stop()

    df_est = load_data(file_est)
    if df_est is None or df_est.empty:
        st.error("Errore nel caricamento del file EST.")
        st.stop()

    # Definizione colonne
    col_asin = "ASIN"
    col_title_it = "Title"
    col_price_it = "Buy Box: Current"
    col_price_est = "Amazon: Current"

    # Controlliamo la presenza delle colonne minime
    for c in [col_asin, col_title_it, col_price_it]:
        if c not in df_ita.columns:
            st.error(f"Nei file IT manca la colonna '{c}'. Impossibile confrontare.")
            st.stop()
    for c in [col_asin, col_price_est]:
        if c not in df_est.columns:
            st.error(f"Nel file EST manca la colonna '{c}'. Impossibile confrontare.")
            st.stop()

    # Pulizia prezzi
    df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
    df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

    # Riduciamo le col solo a quelle necessarie
    df_ita = df_ita[[col_asin, col_title_it, "Prezzo_IT"]]
    df_est = df_est[[col_asin, "Prezzo_Est"]]

    # Merge su ASIN
    df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

    # Calcolo differenza percentuale
    df_merged["Risparmio_%"] = ((df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"])
                                / df_merged["Prezzo_IT"] * 100)

    # Filtra prodotti con Prezzo_Est < Prezzo_IT
    df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

    # Ordina in ordine decrescente
    df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

    # Colonne finali
    df_finale = df_filtered[[col_asin, col_title_it, "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]]

    # Output
    st.subheader("Risultati di Confronto")
    st.dataframe(df_finale, height=600)

    # Bottone scarica CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica Risultati (CSV)",
        data=csv_data,
        file_name="risultato_convenienza.csv",
        mime="text/csv"
    )
