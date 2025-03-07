import streamlit as st
import pandas as pd
import numpy as np
import re
import altair as alt
import math

#################################
# Funzioni Revenue Calculator
#################################
def truncate_2dec(value: float) -> float:
    """
    Tronca un valore a 2 decimali (senza arrotondare).
    Esempio: 0.689 -> 0.68
    """
    return math.floor(value * 100) / 100.0

def calc_referral_fee(category: str, total_sale: float) -> float:
    """
    Calcola la commissione di segnalazione (referral fee) in base alla categoria e al prezzo totale (prezzo + spedizione).
    Restituisce la commissione, SENZA la commissione di chiusura.
    Se applicabile, viene applicato il minimo di 0,30 €.
    """
    referral = 0.0
    if category == "Accessori per dispositivi Amazon":
        referral = 0.45 * total_sale
        referral = max(referral, 0.30)
    elif category == "Auto e moto":
        if total_sale <= 50:
            referral = 0.15 * total_sale
        else:
            referral = (0.15 * 50) + (0.09 * (total_sale - 50))
        referral = max(referral, 0.30)
    elif category == "Prodotti prima infanzia":
        if total_sale <= 10:
            referral = 0.08 * total_sale
        else:
            referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Zaini e borse":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Bellezza, salute e cura della persona":
        if total_sale <= 10:
            referral = 0.08 * total_sale
        else:
            referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Birra, vino e alcolici":
        referral = 0.10 * total_sale
        referral = max(referral, 0.30)
    elif category == "Libri":
        referral = 0.15 * total_sale
    elif category == "Forniture per commercio, industria e scienza":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Abbigliamento e accessori":
        if total_sale <= 15:
            referral = 0.08 * total_sale
        else:
            referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Materiale elettrico e forniture di energia per uso industriale":
        referral = 0.12 * total_sale
        referral = max(referral, 0.30)
    elif category == "Elettrodomestici compatti":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Informatica":
        referral = 0.07 * total_sale
        referral = max(referral, 0.30)
    elif category == "Elettronica":
        referral = 0.07 * total_sale
        referral = max(referral, 0.30)
    elif category == "Accessori per biciclette":
        referral = 0.08 * total_sale
        referral = max(referral, 0.30)
    elif category == "Accessori elettronici":
        if total_sale <= 100:
            referral = 0.15 * total_sale
        else:
            referral = (0.15 * 100) + (0.08 * (total_sale - 100))
        referral = max(referral, 0.30)
    elif category == "Occhiali":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Calzature":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Elettrodomestici di grandi dimensioni":
        referral = 0.07 * total_sale
        referral = max(referral, 0.30)
    elif category == "Arredamento":
        if total_sale <= 200:
            referral = 0.15 * total_sale
        else:
            referral = (0.15 * 200) + (0.10 * (total_sale - 200))
        referral = max(referral, 0.30)
    elif category == "Alimentari e cura della casa":
        if total_sale <= 10:
            referral = 0.08 * total_sale
        else:
            referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Amazon Handmade":
        referral = 0.12 * total_sale
        referral = max(referral, 0.30)
    elif category == "Casa e cucina":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Gioielli":
        if total_sale <= 250:
            referral = 0.20 * total_sale
        else:
            referral = (0.20 * 250) + (0.05 * (total_sale - 250))
        referral = max(referral, 0.30)
    elif category == "Giardino e giardinaggio":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Valigeria":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Materassi":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Musica, video e DVD":
        referral = 0.15 * total_sale
    elif category == "Strumenti musicali e DJ/Produzione audio e video":
        referral = 0.12 * total_sale
        referral = max(referral, 0.30)
    elif category == "Cancelleria e prodotti per ufficio":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Prodotti per animali domestici":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Software":
        referral = 0.15 * total_sale
    elif category == "Sport e tempo libero":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Pneumatici":
        referral = 0.07 * total_sale
        referral = max(referral, 0.30)
    elif category == "Attrezzi e fai da te":
        referral = 0.13 * total_sale
        referral = max(referral, 0.30)
    elif category == "Giochi e giocattoli":
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    elif category == "Videogiochi - Giochi e accessori":
        referral = 0.15 * total_sale
    elif category == "Console per videogiochi":
        referral = 0.08 * total_sale
    elif category == "Orologi":
        if total_sale <= 250:
            referral = 0.15 * total_sale
        else:
            referral = (0.15 * 250) + (0.05 * (total_sale - 250))
        referral = max(referral, 0.30)
    else:
        referral = 0.15 * total_sale
        referral = max(referral, 0.30)
    return referral

def calc_closing_fee(category: str) -> float:
    """
    Restituisce la commissione di chiusura (se prevista) in base alla categoria.
    Dalla tabella:
      - Libri -> 1,01 €
      - Musica, video e DVD, Software, Videogiochi - Giochi e accessori, Console per videogiochi -> 0,81 €
      - Altre categorie -> 0 €
    """
    if category == "Libri":
        return 1.01
    elif category in ["Musica, video e DVD", "Software", "Videogiochi - Giochi e accessori", "Console per videogiochi"]:
        return 0.81
    else:
        return 0.0

def calc_fees(category: str, price: float, shipping: float) -> dict:
    """
    Calcola le commissioni Amazon:
      - referral_fee (troncato a 2 decimali)
      - closing_fee (se prevista)
      - digital_tax (3% su [referral_fee + closing_fee], troncata a 2 decimali)
      - total_fees
    """
    total_sale = price + shipping
    referral_raw = calc_referral_fee(category, total_sale)
    referral_fee = truncate_2dec(referral_raw)
    closing_raw = calc_closing_fee(category)
    closing_fee = truncate_2dec(closing_raw)
    digital_tax_raw = 0.03 * (referral_fee + closing_fee)
    digital_tax = truncate_2dec(digital_tax_raw)
    total_fees = truncate_2dec(referral_fee + closing_fee + digital_tax)
    return {
        "referral_fee": referral_fee,
        "closing_fee": closing_fee,
        "digital_tax": digital_tax,
        "total_fees": total_fees
    }

#################################
# Funzione per calcolare il Prezzo d'Acquisto Netto
#################################
def calc_final_purchase_price(row, discount):
    """
    Calcola il prezzo d'acquisto netto (IVA esclusa e scontato) in base al paese.
    Se il prodotto è acquistato in Italia (Locale "it"):
      final = (prezzo lordo / 1.22) - (prezzo lordo * discount)
    Altrimenti:
      final = (prezzo lordo / 1.19) * (1 - discount)
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
# Funzione per calcolare le metriche Revenue rilevanti
#################################
def calc_revenue_metrics(row, shipping_cost):
    """
    Calcola le metriche Revenue basate sul Revenue Calculator, restituendo:
      - Acquisto_Netto: prezzo d'acquisto netto
      - Price_Comp: prezzo di vendita del mercato di confronto
      - Margine_Comp: margine netto in € (Price_Comp - Acquisto_Netto - commissioni su Price_Comp)
      - Margine_%_Comp: margine netto percentuale (Margine_Comp / Acquisto_Netto * 100)
    Utilizza la categoria proveniente dai dati italiani.
    """
    category = row.get("Category", "Altri prodotti")
    price_comp = row["Price_Comp"]  # Prezzo di vendita nel mercato di confronto
    fees_comp = calc_fees(category, price_comp, shipping_cost)
    net_revenue_comp = price_comp - fees_comp["total_fees"]
    acq_net = row["Acquisto_Netto"]
    margin_comp = net_revenue_comp - acq_net
    margin_comp_pct = (margin_comp / acq_net * 100) if acq_net != 0 else np.nan
    return pd.Series({
        "Acquisto_Netto": acq_net,
        "Price_Comp": price_comp,
        "Margine_Comp": margin_comp,
        "Margine_%_Comp": margin_comp_pct
    })

#################################
# Inizializzazione delle "ricette" in session_state
#################################
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
# Sidebar: Caricamento file, Prezzo di riferimento, Sconto, Shipping Cost, Impostazioni e Ricette
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
    discount = discount_percent / 100.0  # convertiamo in frazione
    st.markdown("---")
    st.subheader("Shipping Cost per Revenue Calculator")
    shipping_cost_input = st.number_input("Inserisci il costo di spedizione (€)", min_value=0.0, value=0.0, step=0.01, key="shipping_cost")
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
# Elaborazione e Calcolo Opportunity Score e Revenue Metrics
#################################
if avvia:
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
        st.error("Assicurati che entrambi i file (origine e confronto) contengano la colonna ASIN.")
        st.stop()
    
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        st.error("Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto.")
        st.stop()
    
    price_col_base = f"{ref_price_base} (base)"
    price_col_comp = f"{ref_price_comp} (comp)"
    df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(parse_float)
    df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(parse_float)
    
    # Altri parsing (SalesRank, Bought, etc.) rimossi, dato che non servono per il margine reale
    # Calcoliamo il prezzo d'acquisto netto
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount), axis=1)
    
    # Selezione della categoria: usiamo quella italiana (Category (base)) se presente
    if "Category (base)" in df_merged.columns:
        df_merged["Category"] = df_merged["Category (base)"]
    else:
        df_merged["Category"] = "Altri prodotti"
    
    # Calcolo delle metriche Revenue (utilizzando il Revenue Calculator sul prezzo di confronto)
    revenue_cols = df_merged.apply(lambda row: calc_revenue_metrics(row, shipping_cost_input), axis=1)
    df_merged = pd.concat([df_merged, revenue_cols], axis=1)
    
    # Selezioniamo solo le colonne essenziali:
    # Dati descrittivi e dati di margine reale:
    # - ASIN, Title (base), Brand (base), Category
    # - Acquisto_Netto, Price_Comp, Margine_Comp, Margine_%_Comp
    cols_final = ["ASIN", "Title (base)", "Brand (base)", "Category", 
                  "Acquisto_Netto", "Price_Comp", "Margine_Comp", "Margine_%_Comp"]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    
    # Arrotonda i valori numerici principali a 2 decimali
    cols_to_round = ["Acquisto_Netto", "Price_Comp", "Margine_Comp", "Margine_%_Comp"]
    for col in cols_to_round:
        if col in df_finale.columns:
            df_finale[col] = df_finale[col].round(2)
    
    st.subheader("Risultati: Margine Reale")
    st.dataframe(df_finale, height=600)
    
    # Pulsante per scaricare i risultati in CSV
    csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati",
        data=csv_data,
        file_name="risultato_margine_reale.csv",
        mime="text/csv"
    )
