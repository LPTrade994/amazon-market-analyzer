import streamlit as st
import pandas as pd
import numpy as np
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
# Mapping delle aliquote IVA per mercato
#################################
iva_rates = {
    "it": 0.22,  # Italia
    "de": 0.19,  # Germania
    "fr": 0.20,  # Francia
    "es": 0.21,  # Spagna
}

#################################
# Mapping delle commissioni per categoria
#################################
commission_rates = {
    "Elettronica": 0.08,
    "Giardino e giardinaggio": 0.15,
    "Casa e cucina": 0.15,
    "Strumenti musicali": 0.15,
    "Videogiochi": 0.15,
    "Alimentari e cura della casa": 0.15,
    "Salute e cura della persona": 0.15,
    "Grandi elettrodomestici": 0.08,
    "Sport e tempo libero": 0.15,
    "Auto e Moto": 0.15,
    "Fai da te": 0.15,
    "Giochi e giocattoli": 0.15,
    "Prima infanzia": 0.15,
    "Moda": 0.15,
    "Prodotti per animali domestici": 0.15,
    "Informatica": 0.07
}

#################################
# Sidebar
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
    discount_percent = st.number_input("Inserisci lo sconto (%)", min_value=0.0, value=20.0, step=0.1)
    discount = discount_percent / 100.0

    st.markdown("---")
    st.subheader("Costo di Spedizione per Revenue Calculator")
    shipping_cost_rev = st.number_input("Inserisci il costo di spedizione (Revenue) (€)", min_value=0.0, value=5.13, step=0.1)

    st.markdown("---")
    avvia = st.button("Calcola Opportunity Score")

#################################
# Funzioni di Caricamento e Parsing
#################################
def load_data(uploaded_file):
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
    if not isinstance(x, str):
        return np.nan
    x_clean = x.replace("€", "").replace(",", ".").strip()
    try:
        return float(x_clean)
    except:
        return np.nan

#################################
# Calcolo Prezzo d'Acquisto Netto
#################################
def calc_final_purchase_price(row, discount, iva_rates):
    locale = row.get("Locale (base)", "it").lower()
    gross = row["Price_Base"]
    if pd.isna(gross):
        return np.nan
    iva_rate = iva_rates.get(locale, 0.22)
    net_price = gross / (1 + iva_rate)
    if locale == "it":
        discount_amount = gross * discount
        final_price = net_price - discount_amount
    else:
        final_price = net_price * (1 - discount)
    return round(final_price, 2)

#################################
# Funzioni Revenue Calculator (FBM)
#################################
def rev_truncate_2dec(value: float) -> float:
    if value is None or np.isnan(value):
        return np.nan
    return math.floor(value * 100) / 100.0

def rev_calc_referral_fee(category: str, price: float) -> float:
    rate = commission_rates.get(category, 0.15)  # Default al 15% se categoria non trovata
    referral = rate * price
    min_referral = 0.30  # Commissione minima
    return max(referral, min_referral)

def rev_calc_fees(category: str, price: float) -> dict:
    referral_raw = rev_calc_referral_fee(category, price)
    referral_fee = rev_truncate_2dec(referral_raw)
    digital_tax_raw = 0.03 * referral_fee  # Imposta sui servizi digitali (3%)
    digital_tax = rev_truncate_2dec(digital_tax_raw)
    total_fees = rev_truncate_2dec(referral_fee + digital_tax)
    return {
        "referral_fee": referral_fee,
        "digital_tax": digital_tax,
        "total_fees": total_fees
    }

def rev_calc_revenue_metrics(row, shipping_cost_rev, market_type, iva_rates):
    # Per FBM il prezzo di vendita lordo viene utilizzato direttamente
    category = row.get("Categories: Root (base)", "Altri prodotti")
    if market_type == "base":
        price = row["Price_Base"]
    else:
        price = row["Price_Comp"]
    
    if pd.isna(price):
        return pd.Series({
            "Margine_Netto (€)": np.nan,
            "Margine_Netto (%)": np.nan
        })
    
    # Calcola le fee basandosi sul prezzo lordo
    fees = rev_calc_fees(category, price)
    total_fees = fees["total_fees"]
    
    # Totale costi: commissioni + costo di spedizione
    total_costs = total_fees + shipping_cost_rev
    purchase_net = row["Acquisto_Netto"]
    
    # Calcola il margine netto usando il prezzo lordo
    margin_net = price - total_costs - purchase_net
    margin_pct = (margin_net / price) * 100 if price != 0 else np.nan
    
    return pd.Series({
        "Margine_Netto (€)": round(margin_net, 2),
        "Margine_Netto (%)": round(margin_pct, 2)
    })

#################################
# Elaborazione
#################################
if avvia:
    if not files_base or not comparison_files:
        st.warning("Carica almeno un file per la Lista di Origine e uno per le Liste di Confronto.")
        st.stop()
    
    base_list = [load_data(f) for f in files_base if load_data(f) is not None and not load_data(f).empty]
    if not base_list:
        st.error("Nessun file di origine valido caricato.")
        st.stop()
    df_base = pd.concat(base_list, ignore_index=True)

    comp_list = [load_data(f) for f in comparison_files if load_data(f) is not None and not load_data(f).empty]
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
    
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount, iva_rates), axis=1)
    
    df_revenue_base = df_merged.apply(lambda row: rev_calc_revenue_metrics(row, shipping_cost_rev, "base", iva_rates), axis=1)
    df_revenue_base = df_revenue_base.add_suffix("_Origine")
    
    df_revenue_comp = df_merged.apply(lambda row: rev_calc_revenue_metrics(row, shipping_cost_rev, "comp", iva_rates), axis=1)
    df_revenue_comp = df_revenue_comp.add_suffix("_Confronto")
    
    df_finale = pd.concat([
        df_merged[["Locale (base)", "Locale (comp)", "ASIN", "Title (base)", "Price_Base", "Price_Comp", "Acquisto_Netto"]],
        df_revenue_base[["Margine_Netto (€)_Origine", "Margine_Netto (%)_Origine"]],
        df_revenue_comp[["Margine_Netto (€)_Confronto", "Margine_Netto (%)_Confronto"]]
    ], axis=1)
    
    st.subheader("Risultati Revenue Calculator")
    st.dataframe(df_finale, height=600)
    csv_data_rev = df_finale.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="Scarica CSV Risultati Revenue",
        data=csv_data_rev,
        file_name="risultato_revenue_calculator.csv",
        mime="text/csv"
    )
