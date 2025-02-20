import streamlit as st
import pandas as pd
import numpy as np

# Configurazione della pagina
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide"
)
st.title("Amazon Market Analyzer - Arbitraggio Multi-Mercato")

#################################
# Sidebar: Caricamento file e Impostazioni
#################################
with st.sidebar:
    st.subheader("Caricamento file")
    files_base = st.file_uploader(
        "Lista di Origine (Mercato Base)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    comparison_files = st.file_uploader(
        "Liste di Confronto (Mercati di Confronto)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )

    st.markdown("---")
    st.subheader("Impostazioni Opportunity Score")
    alpha = st.slider("Peso per Sales Rank (penalità)", 0.0, 5.0, 1.0, step=0.1)
    beta = st.slider("Peso per 'Bought in past month'", 0.0, 5.0, 1.0, step=0.1)
    gamma = st.slider("Peso per Reviews Rating", 0.0, 5.0, 1.0, step=0.1)
    delta = st.slider("Peso penalizzante per Offer Count", 0.0, 5.0, 1.0, step=0.1)
    epsilon = st.slider("Peso per il Margine (%)", 0.0, 10.0, 1.0, step=0.1)

    st.markdown("---")
    st.subheader("Filtri Avanzati (sul mercato di confronto)")
    max_sales_rank = st.number_input("Sales Rank massimo", min_value=1, value=999999)
    min_reviews_rating = st.number_input("Rating minimo", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
    max_offer_count = st.number_input("Offer Count massimo", min_value=1, value=999999)
    min_buybox_price = st.number_input("Prezzo Buy Box minimo", min_value=0.0, value=0.0)
    max_buybox_price = st.number_input("Prezzo Buy Box massimo", min_value=0.0, value=999999.0)

    st.markdown("---")
    avvia = st.button("Calcola Opportunity Score")

#################################
# Funzioni di caricamento e pulizia
#################################
def load_data(uploaded_file):
    """Carica dati da CSV o XLSX in un DataFrame."""
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    if fname.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, dtype=str)
    else:
        try:
            return pd.read_csv(uploaded_file, sep=";", dtype=str)
        except:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=",", dtype=str)

def parse_float(x):
    """Converte stringhe in float, gestendo simboli e errori."""
    if not isinstance(x, str):
        return np.nan
    x_clean = x.replace("€", "").replace(",", ".").strip()
    try:
        return float(x_clean)
    except:
        return np.nan

def parse_int(x):
    """Converte stringhe in int."""
    if not isinstance(x, str):
        return np.nan
    try:
        return int(x.strip())
    except:
        return np.nan

#################################
# Elaborazione quando si clicca "Calcola Opportunity Score"
#################################
if avvia:
    # Controllo file base
    if not files_base:
        st.warning("Carica almeno un file di Lista di Origine.")
        st.stop()
    if not comparison_files:
        st.warning("Carica almeno un file di Liste di Confronto.")
        st.stop()
    
    # Elaborazione Lista di Origine (Base)
    base_list = []
    for f in files_base:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            base_list.append(df_temp)
        else:
            st.warning(f"Il file base {f.name} è vuoto o non valido.")
    if not base_list:
        st.error("Nessun file base valido caricato.")
        st.stop()
    df_base = pd.concat(base_list, ignore_index=True)
    if "ASIN" in df_base.columns:
        unique_asins = df_base["ASIN"].dropna().unique()
        st.info("Lista unificata di ASIN dalla Lista di Origine:")
        st.text_area("Copia qui:", "\n".join(unique_asins), height=200)
    else:
        st.warning("I file di origine non contengono la colonna ASIN.")

    # Elaborazione Liste di Confronto
    comp_list = []
    for f in comparison_files:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            comp_list.append(df_temp)
        else:
            st.warning(f"Il file di confronto {f.name} è vuoto o non valido.")
    if not comp_list:
        st.error("Nessun file di confronto valido caricato.")
        st.stop()
    df_comp = pd.concat(comp_list, ignore_index=True)
    
    # Merge tra base e confronto sulla colonna ASIN
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        st.error("Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto.")
        st.stop()
    
    # Conversione dei dati di interesse (utilizziamo i dati del mercato di confronto)
    df_merged["BuyBox_Base"] = df_merged["Buy Box: Current (base)"].apply(parse_float)
    df_merged["BuyBox_Comp"] = df_merged["Buy Box: Current (comp)"].apply(parse_float)
    df_merged["SalesRank_Comp"] = df_merged["Sales Rank: Current (comp)"].apply(parse_int)
    df_merged["Bought_Comp"] = df_merged["Bought in past month (comp)"].apply(parse_int)
    df_merged["Reviews_Rating_Comp"] = df_merged["Reviews: Rating (comp)"].apply(parse_float)
    df_merged["NewOffer_Comp"] = df_merged["New Offer Count: Current (comp)"].apply(parse_int)
    
    # Calcolo del margine percentuale (differenza percentuale tra BuyBox nel mercato di confronto e quello di origine)
    df_merged["Margin_Pct"] = (df_merged["BuyBox_Comp"] - df_merged["BuyBox_Base"]) / df_merged["BuyBox_Base"] * 100
    # Consideriamo solo i casi in cui il margine è positivo (opportunità di arbitraggio)
    df_merged = df_merged[df_merged["Margin_Pct"] > 0]
    
    # Applichiamo i filtri avanzati (sul mercato di confronto)
    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged = df_merged[df_merged["SalesRank_Comp"] <= max_sales_rank]
    df_merged["Reviews_Rating_Comp"] = df_merged["Reviews_Rating_Comp"].fillna(0)
    df_merged = df_merged[df_merged["Reviews_Rating_Comp"] >= min_reviews_rating]
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    df_merged = df_merged[df_merged["NewOffer_Comp"] <= max_offer_count]
    df_merged = df_merged[df_merged["BuyBox_Comp"].fillna(0).between(min_buybox_price, max_buybox_price)]
    
    # Calcolo Opportunity Score
    # Formula proposta:
    # Opportunity_Score = ε * Margin_Pct +
    #                     β * log(1 + Bought_Comp) +
    #                     γ * Reviews_Rating_Comp -
    #                     δ * NewOffer_Comp -
    #                     α * log(SalesRank_Comp + 1)
    df_merged["Opportunity_Score"] = (
        epsilon * df_merged["Margin_Pct"] +
        beta * np.log(1 + df_merged["Bought_Comp"].fillna(0)) +
        gamma * df_merged["Reviews_Rating_Comp"].fillna(0) -
        delta * df_merged["NewOffer_Comp"].fillna(0) -
        alpha * np.log(df_merged["SalesRank_Comp"] + 1)
    )
    
    # Ordiniamo i risultati per Opportunity Score decrescente
    df_merged = df_merged.sort_values("Opportunity_Score", ascending=False)
    
    # Selezioniamo le colonne da mostrare
    cols_final = [
        "Locale (base)", "Locale (comp)", "Title (base)", "ASIN",
        "BuyBox_Base", "BuyBox_Comp", "Margin_Pct",
        "SalesRank_Comp", "Bought_Comp", "Reviews_Rating_Comp", "NewOffer_Comp",
        "Opportunity_Score", "Brand (base)", "Package: Dimension (cm³) (base)"
    ]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    
    st.subheader("Risultati Opportunità di Arbitraggio")
    st.dataframe(df_finale, height=600)
    
    # Pulsante di download CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati",
        data=csv_data,
        file_name="risultato_opportunity_arbitrage.csv",
        mime="text/csv"
    )
