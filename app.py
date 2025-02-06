import streamlit as st
import pandas as pd

########################################
# Funzione di pulizia prezzo
########################################
def pulisci_prezzo(prezzo_raw):
    """
    Rimuove simboli di euro, spazi e converte virgole in punti.
    Restituisce un float o None se la conversione fallisce.
    """
    if not isinstance(prezzo_raw, str):
        return None
    # Rimuovi simboli euro e spazi
    prezzo = prezzo_raw.replace("€", "").replace(" ", "")
    # Sostituisci eventuali virgole con punti
    prezzo = prezzo.replace(",", ".")
    # Converti a float
    try:
        return float(prezzo)
    except ValueError:
        return None

########################################
# Titolo dell'app
########################################
st.title("Amazon Market Analyzer (CSV/XLSX)")

st.write("""
Carica i due file (italiano ed estero) in formato **CSV** o **XLSX**:

- **Mercato Italiano**: deve contenere almeno `ASIN`, `Title`, `Buy Box: Current`
- **Mercato Estero**: deve contenere almeno `ASIN`, `Amazon: Current`

Il tool:

1. Confronta i prodotti in base ad `ASIN`.
2. Mostra solo quelli con **Prezzo Estero < Prezzo Italiano**.
3. Calcola la differenza di prezzo in percentuale.
4. Ordina il risultato in ordine decrescente di convenienza.
""")

########################################
# Caricamento file (accetta .csv e .xlsx)
########################################
file_ita = st.file_uploader("Carica il file del mercato ITALIANO (CSV/XLSX)", 
                            type=["csv","xlsx"])
file_est = st.file_uploader("Carica il file del mercato ESTERO (CSV/XLSX)", 
                            type=["csv","xlsx"])

def load_data(uploaded_file):
    """
    Carica il DataFrame da un file CSV o XLSX (rileva l'estensione).
    Restituisce un DataFrame con stringhe.
    """
    if uploaded_file is None:
        return None
    
    filename = uploaded_file.name.lower()
    
    # Se è un file XLSX
    if filename.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str, engine="openpyxl")
        return df
    else:
        # Prova a leggerlo come CSV
        # Prima tentativo con ; come separatore, se fallisce usa ,
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

if file_ita and file_est:
    if st.button("Confronta Prezzi"):
        # Carica i dati con la funzione dedicata
        df_ita = load_data(file_ita)
        df_est = load_data(file_est)

        if df_ita is None or df_est is None:
            st.error("Errore nel caricamento dei file.")
        else:
            # Definizioni colonne
            col_asin = "ASIN"
            col_title_it = "Title"
            col_price_it = "Buy Box: Current"
            col_price_est = "Amazon: Current"

            # Tieni solo le colonne di interesse (adatta se i tuoi file usano naming diversi)
            if (col_asin not in df_ita.columns or 
                col_title_it not in df_ita.columns or
                col_price_it not in df_ita.columns):
                st.error("Il file IT non contiene le colonne richieste (ASIN, Title, Buy Box: Current)")
                st.stop()
            if (col_asin not in df_est.columns or 
                col_price_est not in df_est.columns):
                st.error("Il file EST non contiene le colonne richieste (ASIN, Amazon: Current)")
                st.stop()

            df_ita = df_ita[[col_asin, col_title_it, col_price_it]]
            df_est = df_est[[col_asin, col_price_est]]

            # Pulizia prezzi
            df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
            df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

            # Merge basato su ASIN
            df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

            # Calcolo differenza percentuale
            df_merged["Risparmio_%"] = (
                (df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"]) / 
                df_merged["Prezzo_IT"] * 100
            )

            # Filtra i prodotti in cui Prezzo_Est < Prezzo_IT
            df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

            # Ordina in ordine decrescente
            df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

            # Seleziona le colonne finali
            df_finale = df_filtered[[col_asin, col_title_it, 
                                     "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]]

            # Mostra la tabella
            st.write("**Prodotti più convenienti all'estero (ordine decrescente):**")
            st.dataframe(df_finale)

            # Scarica CSV
            csv_risultato = df_finale.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="Scarica risultati (CSV)",
                data=csv_risultato,
                file_name="risultato_convenienza.csv",
                mime="text/csv"
            )

else:
    st.info("Attendi di caricare entrambi i file (Italiano ed Estero).")
