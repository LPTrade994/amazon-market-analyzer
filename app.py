import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)")

#################################
# Sidebar: Caricamento file e impostazioni
#################################
with st.sidebar:
    st.subheader("Caricamento file")

    # Liste di confronto (può essere un unico file con più righe o più file)
    comparison_files = st.file_uploader(
        "Carica file CSV/XLSX con le nuove colonne (Sales Rank, Prezzi, ecc.)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )

    st.markdown("---")

    # Slider per i pesi dell'Opportunity Score
    st.subheader("Impostazioni Opportunity Score")
    alpha = st.slider("Peso per Sales Rank (valore negativo su rank alto)", 0.0, 5.0, 1.0, step=0.1)
    beta = st.slider("Peso per Bought in past month", 0.0, 5.0, 1.0, step=0.1)
    gamma = st.slider("Peso per Reviews Rating", 0.0, 5.0, 1.0, step=0.1)
    delta = st.slider("Peso penalizzante su Offer Count", 0.0, 5.0, 1.0, step=0.1)

    st.markdown("---")

    # Filtri Avanzati
    st.subheader("Filtri Avanzati")
    max_sales_rank = st.number_input("Filtro Sales Rank massimo", min_value=1, value=999999)
    min_reviews_rating = st.number_input("Filtro Recensioni minime (Rating)", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
    max_offer_count = st.number_input("Filtro Offer Count massimo", min_value=1, value=999999)
    # Esempio: filtro prezzo Buy Box (opzionale)
    min_buybox_price = st.number_input("Prezzo Buy Box minimo", min_value=0.0, value=0.0)
    max_buybox_price = st.number_input("Prezzo Buy Box massimo", min_value=0.0, value=999999.0)

    st.markdown("---")
    avvia_confronto = st.button("Carica e Calcola")

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
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def parse_float(x):
    """Converte stringhe in float, ignorando errori."""
    if not isinstance(x, str):
        return np.nan
    x_clean = x.replace("€", "").replace(",", ".").strip()
    try:
        return float(x_clean)
    except:
        return np.nan

def parse_int(x):
    """Converte stringhe in int, ignorando errori."""
    if not isinstance(x, str):
        return np.nan
    try:
        return int(x.strip())
    except:
        return np.nan

#################################
# Elaborazione
#################################
if avvia_confronto:
    if not comparison_files:
        st.warning("Devi caricare almeno un file con le colonne aggiornate.")
        st.stop()

    # Concatenazione di tutti i file
    df_list = []
    for f in comparison_files:
        dftemp = load_data(f)
        if dftemp is not None and not dftemp.empty:
            df_list.append(dftemp)
        else:
            st.warning(f"Il file {f.name} è vuoto o non valido.")
    
    if not df_list:
        st.error("Nessun file valido caricato.")
        st.stop()

    df = pd.concat(df_list, ignore_index=True)

    # Verifichiamo che le colonne chiave esistano
    needed_cols = [
        "Locale", "Title",
        "Sales Rank: Current", "Sales Rank: 30 days avg.",
        "Bought in past month",
        "Return Rate",
        "Reviews: Rating", "Reviews: Review Count",
        "Buy Box: Current", "Buy Box: Is Lowest", "Buy Box: Is Lowest 90 days",
        "Buy Box: Stock", "Buy Box out of stock percentage: 90 days OOS %",
        "Amazon: Current", "Amazon: Is Lowest", "Amazon: Is Lowest 90 days",
        "Amazon: Stock", "Amazon out of stock percentage: 90 days OOS %",
        "New out of stock percentage: 90 days OOS %",
        "New Offer Count: Current",
        "ASIN", "Brand",
        "Package: Dimension (cm³)"
    ]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        st.error(f"Mancano le seguenti colonne nel file: {', '.join(missing)}.")
        st.stop()

    # Conversione di colonne numeriche
    df["Sales_Rank_Current"] = df["Sales Rank: Current"].apply(parse_int)
    df["Sales_Rank_30days"] = df["Sales Rank: 30 days avg."].apply(parse_int)
    df["Bought_in_past_month_num"] = df["Bought in past month"].apply(parse_int)
    df["Return_Rate_num"] = df["Return Rate"].apply(parse_float)
    df["Reviews_Rating"] = df["Reviews: Rating"].apply(parse_float)
    df["Reviews_Count"] = df["Reviews: Review Count"].apply(parse_int)

    df["BuyBox_Current"] = df["Buy Box: Current"].apply(parse_float)
    df["BuyBox_IsLowest"] = df["Buy Box: Is Lowest"].str.lower().eq("yes")
    df["BuyBox_IsLowest90"] = df["Buy Box: Is Lowest 90 days"].str.lower().eq("yes")
    df["BuyBox_Stock"] = df["Buy Box: Stock"].apply(parse_int)
    df["BuyBox_OOS_90"] = df["Buy Box out of stock percentage: 90 days OOS %"].apply(parse_float)

    df["Amazon_Current"] = df["Amazon: Current"].apply(parse_float)
    df["Amazon_IsLowest"] = df["Amazon: Is Lowest"].str.lower().eq("yes")
    df["Amazon_IsLowest90"] = df["Amazon: Is Lowest 90 days"].str.lower().eq("yes")
    df["Amazon_Stock"] = df["Amazon: Stock"].apply(parse_int)
    df["Amazon_OOS_90"] = df["Amazon out of stock percentage: 90 days OOS %"].apply(parse_float)

    df["New_OOS_90"] = df["New out of stock percentage: 90 days OOS %"].apply(parse_float)
    df["New_OfferCount"] = df["New Offer Count: Current"].apply(parse_int)

    # Calcolo Opportunity Score
    # Esempio formula:
    # OppScore = alpha * -log(SalesRank+1) + beta * log(1 + BoughtMonth) + gamma * ReviewsRating - delta * OfferCount
    # Usa .fillna(0) o simili per evitare errori
    df["Sales_Rank_Current"] = df["Sales_Rank_Current"].fillna(999999)
    df["Bought_in_past_month_num"] = df["Bought_in_past_month_num"].fillna(0)
    df["Reviews_Rating"] = df["Reviews_Rating"].fillna(0)
    df["New_OfferCount"] = df["New_OfferCount"].fillna(0)

    # Per evitare log(0), aggiungiamo +1
    df["Opportunity_Score"] = (
        alpha * -np.log(df["Sales_Rank_Current"] + 1) +
        beta * np.log(1 + df["Bought_in_past_month_num"]) +
        gamma * df["Reviews_Rating"] -
        delta * df["New_OfferCount"]
    )

    # Filtri Avanzati
    # 1) Sales Rank <= max_sales_rank
    df_filtered = df[df["Sales_Rank_Current"] <= max_sales_rank]
    # 2) Rating >= min_reviews_rating
    df_filtered = df_filtered[df_filtered["Reviews_Rating"] >= min_reviews_rating]
    # 3) Offer Count <= max_offer_count
    df_filtered = df_filtered[df_filtered["New_OfferCount"] <= max_offer_count]
    # 4) Prezzo Buy Box compreso tra min_buybox_price e max_buybox_price
    df_filtered = df_filtered[df_filtered["BuyBox_Current"].fillna(0).between(min_buybox_price, max_buybox_price)]

    # Ordiniamo per Opportunity_Score decrescente
    df_filtered = df_filtered.sort_values("Opportunity_Score", ascending=False)

    # Selezioniamo le colonne finali per la visualizzazione
    columns_finali = [
        "Locale", "Title", "Sales_Rank_Current", "Sales_Rank_30days",
        "Bought_in_past_month_num", "Reviews_Rating", "Reviews_Count",
        "BuyBox_Current", "Amazon_Current", "New_OfferCount",
        "Opportunity_Score", "ASIN", "Brand"
    ]
    # Mantieni solo quelle che esistono
    columns_finali = [c for c in columns_finali if c in df_filtered.columns]

    df_finale = df_filtered[columns_finali].copy()

    st.subheader("Risultati con Opportunity Score e Filtri Avanzati")
    st.dataframe(df_finale, height=600)

    # Download CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati",
        data=csv_data,
        file_name="risultato_opportunity_score.csv",
        mime="text/csv"
    )
