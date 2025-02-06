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
st.title("Amazon Market Analyzer")

st.write("""
Carica i due file CSV:
- **Mercato Italiano** (con colonne `ASIN`, `Title`, `Buy Box: Current`).
- **Mercato Estero** (con colonne `ASIN`, `Amazon: Current`).

Il tool confronterà i prezzi e mostrerà (in ordine decrescente di convenienza) 
i prodotti in cui il prezzo **estero** risulta inferiore al prezzo **italiano**.
""")

########################################
# Caricamento file
########################################
file_ita = st.file_uploader("Carica CSV - Mercato Italiano", type=["csv"])
file_est = st.file_uploader("Carica CSV - Mercato Estero", type=["csv"])

if file_ita and file_est:
    # Bottone per avviare l'analisi
    if st.button("Confronta Prezzi"):
        # Leggi i CSV con pandas
        try:
            df_ita = pd.read_csv(file_ita, sep=";", dtype=str)
        except:
            file_ita.seek(0)
            df_ita = pd.read_csv(file_ita, sep=",", dtype=str)
        
        try:
            df_est = pd.read_csv(file_est, sep=";", dtype=str)
        except:
            file_est.seek(0)
            df_est = pd.read_csv(file_est, sep=",", dtype=str)

        # Colonne attese (adatta se i tuoi file usano nomi diversi)
        col_asin = "ASIN"
        col_title_it = "Title"
        col_price_it = "Buy Box: Current"
        col_price_est = "Amazon: Current"

        # Selezione colonne
        df_ita = df_ita[[col_asin, col_title_it, col_price_it]]
        df_est = df_est[[col_asin, col_price_est]]

        # Pulizia prezzi
        df_ita["Prezzo_IT"] = df_ita[col_price_it].apply(pulisci_prezzo)
        df_est["Prezzo_Est"] = df_est[col_price_est].apply(pulisci_prezzo)

        # Merge su ASIN
        df_merged = pd.merge(df_ita, df_est, on=col_asin, how="inner")

        # Calcolo risparmio %
        df_merged["Risparmio_%"] = (
            (df_merged["Prezzo_IT"] - df_merged["Prezzo_Est"]) / df_merged["Prezzo_IT"] * 100
        )

        # Filtra i casi in cui Prezzo Est < Prezzo IT
        df_filtered = df_merged[df_merged["Prezzo_Est"] < df_merged["Prezzo_IT"]]

        # Ordina in ordine decrescente di risparmio
        df_filtered = df_filtered.sort_values("Risparmio_%", ascending=False)

        # Seleziona le colonne finali
        df_finale = df_filtered[[col_asin, col_title_it, "Prezzo_IT", "Prezzo_Est", "Risparmio_%"]]

        # Mostra i risultati
        st.write("**Prodotti più convenienti sul mercato estero**:")
        st.dataframe(df_finale)

        # Opzione per scaricare la tabella
        csv_risultato = df_finale.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="Scarica risultati come CSV",
            data=csv_risultato,
            file_name="risultato_convenienza.csv",
            mime="text/csv"
        )

else:
    st.info("Carica entrambi i file CSV per procedere al confronto.")
