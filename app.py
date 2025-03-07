import streamlit as st
import pandas as pd
import numpy as np
import re
import altair as alt
import math

# Inizializzazione delle "ricette" in session_state
if 'recipes' not in st.session_state:
    st.session_state['recipes'] = {}

# Configurazione della pagina
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide"
)
st.title("Amazon Market Analyzer - Arbitraggio Multi-Mercato")

#################################
# Mapping delle categorie e commissioni (da Keepa)
#################################
commission_params = {
    "Accessori per dispositivi Amazon": {"rate": 0.45, "min": 0.30},
    "Auto e moto": {"rate": 0.15, "threshold": 50, "rate_after": 0.09, "min": 0.30},
    "Prodotti prima infanzia": {"rate": 0.08, "threshold": 10, "rate_after": 0.15, "min": 0.30},
    "Zaini e borse": {"rate": 0.15, "min": 0.30},
    "Bellezza, salute e cura della persona": {"rate": 0.08, "threshold": 10, "rate_after": 0.15, "min": 0.30},
    "Birra, vino e alcolici": {"rate": 0.10, "min": 0.30},
    "Libri": {"rate": 0.15},
    "Forniture per commercio, industria e scienza": {"rate": 0.15, "min": 0.30},
    "Abbigliamento e accessori": {"rate": 0.08, "threshold": 15, "rate_after": 0.15, "min": 0.30},
    "Materiale elettrico e forniture di energia per uso industriale": {"rate": 0.12, "min": 0.30},
    "Elettrodomestici compatti": {"rate": 0.15, "min": 0.30},
    "Informatica": {"rate": 0.07, "min": 0.30},
    "Elettronica": {"rate": 0.07, "min": 0.30},
    "Accessori per biciclette": {"rate": 0.08, "min": 0.30},
    "Accessori elettronici": {"rate": 0.15, "threshold": 100, "rate_after": 0.08, "min": 0.30},
    "Occhiali": {"rate": 0.15, "min": 0.30},
    "Calzature": {"rate": 0.15, "min": 0.30},
    "Elettrodomestici di grandi dimensioni": {"rate": 0.07, "min": 0.30},
    "Arredamento": {"rate": 0.15, "threshold": 200, "rate_after": 0.10, "min": 0.30},
    "Alimentari e cura della casa": {"rate": 0.08, "threshold": 10, "rate_after": 0.15, "min": 0.30},
    "Amazon Handmade": {"rate": 0.12, "min": 0.30},
    "Casa e cucina": {"rate": 0.15, "min": 0.30},
    "Gioielli": {"rate": 0.20, "threshold": 250, "rate_after": 0.05, "min": 0.30},
    "Giardino e giardinaggio": {"rate": 0.15, "min": 0.30},
    "Valigeria": {"rate": 0.15, "min": 0.30},
    "Materassi": {"rate": 0.15, "min": 0.30},
    "Musica, video e DVD": {"rate": 0.15},
    "Strumenti musicali e DJ/Produzione audio e video": {"rate": 0.12, "min": 0.30},
    "Cancelleria e prodotti per ufficio": {"rate": 0.15, "min": 0.30},
    "Prodotti per animali domestici": {"rate": 0.15, "min": 0.30},
    "Software": {"rate": 0.15},
    "Sport e tempo libero": {"rate": 0.15, "min": 0.30},
    "Pneumatici": {"rate": 0.07, "min": 0.30},
    "Attrezzi e fai da te": {"rate": 0.13, "min": 0.30},
    "Giochi e giocattoli": {"rate": 0.15, "min": 0.30},
    "Videogiochi - Giochi e accessori": {"rate": 0.15},
    "Console per videogiochi": {"rate": 0.08},
    "Orologi": {"rate": 0.15, "threshold": 250, "rate_after": 0.05, "min": 0.30}
}

closing_fee_table = {
    "Libri": 1.01,
    "Musica, video e DVD": 0.81,
    "Software": 0.81,
    "Videogiochi - Giochi e accessori": 0.81,
    "Console per videogiochi": 0.81
}

#################################
# Sidebar: Caricamento file, Prezzo di riferimento, Sconto, Impostazioni, Ricette, Revenue Calculator
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
    st.subheader("Prezzo di riferimento")
    ref_price_base = st.selectbox(
        "Per la Lista di Origine",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )
    ref_price_comp = st.selectbox(
        "Per la Lista di Confronto",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )

    st.markdown("---")
    st.subheader("Sconto per gli acquisti")
    discount_percent = st.number_input("Inserisci lo sconto (%)", min_value=0.0, value=st.session_state.get("discount_percent", 20.0), step=0.1, key="discount_percent")
    discount = discount_percent / 100.0

    st.markdown("---")
    st.subheader("Impostazioni Opportunity Score")
    alpha = st.slider("Peso per Sales Rank (penalità)", 0.0, 5.0, st.session_state.get("alpha", 1.0), step=0.1, key="alpha")
    beta = st.slider("Peso per 'Bought in past month'", 0.0, 5.0, st.session_state.get("beta", 1.0), step=0.1, key="beta")
    delta = st.slider("Peso penalizzante per Offer Count", 0.0, 5.0, st.session_state.get("delta", 1.0), step=0.1, key="delta")
    epsilon = st.slider("Peso per il Margine (%)", 0.0, 10.0, st.session_state.get("epsilon", 1.0), step=0.1, key="epsilon")
    zeta = st.slider("Peso per Trend Sales Rank (90 giorni vs. attuale)", 0.0, 5.0, st.session_state.get("zeta", 1.0), step=0.1, key="zeta")

    st.markdown("---")
    st.subheader("Filtri Avanzati (Mercato di Confronto)")
    max_sales_rank = st.number_input("Sales Rank massimo", min_value=1, value=999999)
    max_offer_count = st.number_input("Offer Count massimo", min_value=1, value=999999)
    min_buybox_price = st.number_input("Prezzo di riferimento (Buy Box) minimo", min_value=0.0, value=0.0)
    max_buybox_price = st.number_input("Prezzo di riferimento (Buy Box) massimo", min_value=0.0, value=999999.0)

    st.markdown("---")
    st.subheader("Personalizzazione e Salvataggio di Ricette")
    selected_recipe = st.selectbox("Carica Ricetta", options=["-- Nessuna --"] + list(st.session_state['recipes'].keys()))
    if selected_recipe != "-- Nessuna --":
        recipe = st.session_state['recipes'][selected_recipe]
        st.session_state["alpha"] = recipe.get("alpha", 1.0)
        st.session_state["beta"] = recipe.get("beta", 1.0)
        st.session_state["delta"] = recipe.get("delta", 1.0)
        st.session_state["epsilon"] = recipe.get("epsilon", 1.0)
        st.session_state["zeta"] = recipe.get("zeta", 1.0)
        st.session_state["discount_percent"] = recipe.get("discount_percent", 20.0)
    new_recipe_name = st.text_input("Nome Nuova Ricetta")
    if st.button("Salva Ricetta"):
        if new_recipe_name:
            st.session_state['recipes'][new_recipe_name] = {
                "alpha": st.session_state.get("alpha", 1.0),
                "beta": st.session_state.get("beta", 1.0),
                "delta": st.session_state.get("delta", 1.0),
                "epsilon": st.session_state.get("epsilon", 1.0),
                "zeta": st.session_state.get("zeta", 1.0),
                "discount_percent": st.session_state.get("discount_percent", 20.0)
            }
            st.success(f"Ricetta '{new_recipe_name}' salvata!")
        else:
            st.error("Inserisci un nome valido per la ricetta.")

    st.markdown("---")
    st.subheader("Costo di Spedizione per Revenue Calculator")
    shipping_cost_rev = st.number_input("Inserisci il costo di spedizione (Revenue) (€)", min_value=0.0, value=0.0, step=0.1, key="shipping_cost_rev")
    
    st.markdown("---")
    st.subheader("Costo d'Acquisto Netto per Revenue Calculator")
    purchase_cost_rev = st.number_input("Inserisci il costo d'acquisto netto (€)", min_value=0.0, value=0.0, step=0.1, key="purchase_cost_rev")
    
    st.markdown("---")
    avvia = st.button("Calcola Opportunity Score")

#################################
# Funzioni di Caricamento e Parsing
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

def format_trend(trend):
    if pd.isna(trend):
        return "N/D"
    if trend > 0.1:
        return "🔼 Crescente"
    elif trend < -0.1:
        return "🔽 Decrescente"
    else:
        return "➖ Stabile"

#################################
# Funzioni Revenue Calculator (prefissate con "rev_")
#################################
def rev_truncate_2dec(value: float) -> float:
    """Tronca un valore a 2 decimali senza arrotondare."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    return math.floor(value * 100) / 100.0

def rev_calc_referral_fee(category: str, total_sale: float) -> float:
    """Calcola il referral fee in base alla categoria usando i parametri della tabella Keepa."""
    params = commission_params.get(category, {"rate": 0.15, "min": 0.30})
    if "threshold" in params:
        threshold = params["threshold"]
        if total_sale <= threshold:
            referral = params["rate"] * total_sale
        else:
            referral = params["rate"] * threshold + params["rate_after"] * (total_sale - threshold)
    else:
        referral = params["rate"] * total_sale
    if "min" in params:
        referral = max(referral, params["min"])
    return referral

def rev_calc_closing_fee(category: str) -> float:
    """Restituisce il closing fee per la categoria, se presente, altrimenti 0."""
    return closing_fee_table.get(category, 0.0)

def rev_calc_fees(category: str, price: float, shipping: float) -> dict:
    """Calcola le commissioni totali (referral, closing, digital tax) per il revenue calculator."""
    total_sale = price + shipping
    referral_raw = rev_calc_referral_fee(category, total_sale)
    referral_fee = rev_truncate_2dec(referral_raw)
    closing_raw = rev_calc_closing_fee(category)
    closing_fee = rev_truncate_2dec(closing_raw)
    digital_tax_raw = 0.03 * (referral_fee + closing_fee)
    digital_tax = rev_truncate_2dec(digital_tax_raw)
    total_fees = rev_truncate_2dec(referral_fee + closing_fee + digital_tax)
    return {
        "referral_fee": referral_fee,
        "closing_fee": closing_fee,
        "digital_tax": digital_tax,
        "total_fees": total_fees
    }

def rev_calc_revenue_metrics(row, shipping_cost_rev, purchase_cost_rev):
    """
    Calcola le metriche revenue sul mercato di riferimento:
      - Prezzo Vendita Corrente: da Price_Base
      - Costo d'Acquisto Netto: usa il valore fornito (purchase_cost_rev > 0) altrimenti Acquisto_Netto
      - Shipping_Cost, Fees, Net_Revenue, Margine Netto (€) e (%) e altri dati utili
    """
    purchase_net = purchase_cost_rev if purchase_cost_rev > 0 else row["Acquisto_Netto"]
    prezzo_vendita = row["Price_Base"]
    category = row.get("Category (base)", row.get("Category", "Altri prodotti"))
    fees = rev_calc_fees(category, prezzo_vendita, shipping_cost_rev)
    net_selling_price = prezzo_vendita - fees["total_fees"]
    margin_net = net_selling_price - (purchase_net + shipping_cost_rev)
    margin_pct = (margin_net / (purchase_net + shipping_cost_rev) * 100) if (purchase_net + shipping_cost_rev) != 0 else np.nan
    return pd.Series({
         "Prezzo Vendita Corrente": prezzo_vendita,
         "Costo d'Acquisto Netto": purchase_net,
         "Shipping_Cost": shipping_cost_rev,
         "Fees": fees["total_fees"],
         "Net_Revenue": net_selling_price,
         "Margine_Netto (€)": margin_net,
         "Margine_Netto (%)": margin_pct,
         "Bought_Comp": row.get("Bought_Comp", np.nan),
         "SalesRank_Comp": row.get("SalesRank_Comp", np.nan),
         "Trend": row.get("Trend", "")
    })

#################################
# Visualizzazione degli ASIN dalla Lista di Origine
#################################
if files_base:
    base_list = []
    for f in files_base:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            base_list.append(df_temp)
        else:
            st.warning(f"Il file base {f.name} è vuoto o non valido.")
    if base_list:
        df_base = pd.concat(base_list, ignore_index=True)
        if "ASIN" in df_base.columns:
            unique_asins = df_base["ASIN"].dropna().unique()
            st.info("Lista unificata di ASIN dalla Lista di Origine:")
            st.text_area("Copia qui:", "\n".join(unique_asins), height=200)
        else:
            st.warning("I file di origine non contengono la colonna ASIN.")
    else:
        st.info("Carica la Lista di Origine per vedere gli ASIN unificati.")

#################################
# Funzione per il calcolo del Prezzo d'Acquisto Netto (già presente)
#################################
def calc_final_purchase_price(row, discount):
    """
    Calcola il prezzo d'acquisto netto (IVA esclusa e scontato) in base al paese.
    """
    locale = row.get("Locale (base)", "it")
    try:
        locale = str(locale).strip().lower()
    except:
        locale = "it"
    gross = row["Price_Base"]
    if pd.isna(gross):
        return np.nan
    if locale == "it":
        return (gross / 1.22) - (gross * discount)
    else:
        return (gross / 1.19) * (1 - discount)

#################################
# Elaborazione Completa e Calcolo Opportunity Score e Revenue Calculator
#################################
if avvia:
    # Elaborazione file di confronto
    if not comparison_files:
        st.warning("Carica almeno un file di Liste di Confronto.")
        st.stop()
    
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
    
    if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
        st.error("Assicurati che entrambi i file contengano la colonna ASIN.")
        st.stop()
    
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        st.error("Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto.")
        st.stop()
    
    price_col_base = f"{ref_price_base} (base)"
    price_col_comp = f"{ref_price_comp} (comp)"
    df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(parse_float)
    df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(parse_float)
    
    df_merged["SalesRank_Comp"] = df_merged.get("Sales Rank: Current (comp)", pd.Series(np.nan)).apply(parse_int)
    df_merged["Bought_Comp"] = df_merged.get("Bought in past month (comp)", pd.Series(np.nan)).apply(parse_int)
    df_merged["NewOffer_Comp"] = df_merged.get("New Offer Count: Current (comp)", pd.Series(np.nan)).apply(parse_int)
    df_merged["SalesRank_90d"] = df_merged.get("Sales Rank: 90 days avg. (comp)", pd.Series(np.nan)).apply(parse_int)
    
    df_merged["Margin_Pct"] = (df_merged["Price_Comp"] - df_merged["Price_Base"]) / df_merged["Price_Base"] * 100
    df_merged = df_merged[df_merged["Margin_Pct"] > 0]
    
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount), axis=1)
    
    df_merged["Margine_Stimato"] = df_merged["Price_Comp"] - df_merged["Acquisto_Netto"]
    df_merged["Margine_%"] = (df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]) * 100
    
    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged = df_merged[df_merged["SalesRank_Comp"] <= max_sales_rank]
    
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    df_merged = df_merged[df_merged["NewOffer_Comp"] <= max_offer_count]
    
    df_merged["Price_Comp"] = df_merged["Price_Comp"].fillna(0)
    df_merged = df_merged[df_merged["Price_Comp"].between(min_buybox_price, max_buybox_price)]
    
    df_merged["Trend_Bonus"] = np.log((df_merged["SalesRank_90d"].fillna(df_merged["SalesRank_Comp"]) + 1) / (df_merged["SalesRank_Comp"] + 1))
    df_merged["Trend"] = df_merged["Trend_Bonus"].apply(format_trend)
    
    df_merged["Opportunity_Score"] = (
        epsilon * df_merged["Margin_Pct"] +
        beta * np.log(1 + df_merged["Bought_Comp"].fillna(0)) -
        delta * df_merged["NewOffer_Comp"].fillna(0) -
        alpha * np.log(df_merged["SalesRank_Comp"] + 1) +
        zeta * df_merged["Trend_Bonus"]
    )
    
    # ---------------------------
    # Calcolo e Visualizzazione Revenue Calculator (RISULTATI PRIMI)
    # ---------------------------
    df_revenue = df_merged.apply(lambda row: rev_calc_revenue_metrics(row, shipping_cost_rev, purchase_cost_rev), axis=1)
    df_revenue["ASIN"] = df_merged["ASIN"]
    df_revenue["Title (base)"] = df_merged["Title (base)"]
    df_revenue["Locale (base)"] = df_merged["Locale (base)"] if "Locale (base)" in df_merged.columns else np.nan
    df_revenue["Locale (comp)"] = df_merged["Locale (comp)"] if "Locale (comp)" in df_merged.columns else np.nan
    
    revenue_cols = [
        "Locale (base)", "Locale (comp)", "ASIN", "Title (base)", "Prezzo Vendita Corrente",
        "Costo d'Acquisto Netto", "Shipping_Cost", "Fees", "Net_Revenue",
        "Margine_Netto (€)", "Margine_Netto (%)", "Bought_Comp", "SalesRank_Comp", "Trend"
    ]
    df_revenue_final = df_revenue[revenue_cols].copy()
    for col in ["Prezzo Vendita Corrente", "Costo d'Acquisto Netto", "Shipping_Cost", "Fees", "Net_Revenue", "Margine_Netto (€)", "Margine_Netto (%)"]:
        df_revenue_final[col] = df_revenue_final[col].round(2)
    
    st.subheader("Risultati Revenue Calculator")
    st.dataframe(df_revenue_final, height=600)
    csv_data_rev = df_revenue_final.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati Revenue",
        data=csv_data_rev,
        file_name="risultato_revenue_calculator.csv",
        mime="text/csv"
    )
    
    # ---------------------------
    # Visualizzazione Opportunity Score (risultati successivi)
    # ---------------------------
    cols_final = [
        "Locale (base)", "Locale (comp)", "Title (base)", "ASIN",
        "Price_Base", "Acquisto_Netto", "Price_Comp", "Margin_Pct",
        "Margine_Stimato", "Margine_%", "SalesRank_Comp", "SalesRank_90d",
        "Trend", "Bought_Comp", "NewOffer_Comp", "Opportunity_Score",
        "Brand (base)", "Package: Dimension (cm³) (base)"
    ]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    for col in ["Price_Base", "Acquisto_Netto", "Price_Comp", "Margin_Pct", "Margine_Stimato", "Margine_%", "Opportunity_Score"]:
        if col in df_finale.columns:
            df_finale[col] = df_finale[col].round(2)
    
    st.subheader("Risultati Opportunity Score")
    st.dataframe(df_finale, height=600)
    st.markdown("---")
    st.subheader("Dashboard Interattiva")
    if not df_finale.empty:
        st.metric("Numero di Opportunità", len(df_finale))
        st.metric("Margine Medio (%)", round(df_finale["Margin_Pct"].mean(), 2))
        st.metric("Opportunity Score Massimo", round(df_finale["Opportunity_Score"].max(), 2))
    else:
        st.info("Nessun prodotto trovato con i filtri applicati.")
    
    chart = alt.Chart(df_finale.reset_index()).mark_circle(size=60).encode(
        x=alt.X("Margin_Pct:Q", title="Margine (%)"),
        y=alt.Y("Opportunity_Score:Q", title="Opportunity Score"),
        color=alt.Color("Locale (comp):N", title="Mercato Confronto"),
        tooltip=["Title (base)", "ASIN", "Margin_Pct", "Opportunity_Score", "Trend"]
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
    
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati Opportunity Score",
        data=csv_data,
        file_name="risultato_opportunity_arbitrage.csv",
        mime="text/csv"
    )
