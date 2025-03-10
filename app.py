import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode
import base64
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Amazon Market Analyzer Pro - Multi-Market Arbitrage",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #232F3E;
        font-weight: 700;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #FF9900, #232F3E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #232F3E;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .card {
        background-color: #FFFFFF;
        border-radius: 0.5rem;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #232F3E;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .stButton button {
        background-color: #FF9900;
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.3rem;
    }
    .stButton button:hover {
        background-color: #E88A00;
    }
    .market-flag {
        font-size: 1.2rem;
        margin-right: 0.5rem;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #666;
        font-size: 0.8rem;
    }
    div[data-testid="stSidebarNav"] {
        background-color: #232F3E;
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FAFAFA;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF9900;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to get market flags
def get_market_flag(locale):
    flags = {
        "it": "🇮🇹",
        "de": "🇩🇪",
        "fr": "🇫🇷",
        "es": "🇪🇸",
        "uk": "🇬🇧"
    }
    return flags.get(locale.lower(), "🌍")

# Title and introduction
st.markdown('<h1 class="main-header">Amazon Market Analyzer Pro</h1>', unsafe_allow_html=True)
st.markdown('<div class="card">Strumento avanzato per identificare opportunità di arbitraggio tra i marketplace Amazon europei. Analizza prezzi, calcola commissioni e individua i prodotti più redditizi da acquistare in un mercato e rivendere in un altro.</div>', unsafe_allow_html=True)

# Initialize session state
if 'opportunities' not in st.session_state:
    st.session_state['opportunities'] = None
if 'results_available' not in st.session_state:
    st.session_state['results_available'] = False
if 'selected_products' not in st.session_state:
    st.session_state['selected_products'] = []
if 'calculation_history' not in st.session_state:
    st.session_state['calculation_history'] = []

#################################
# CONSTANTS AND MAPPINGS
#################################

# VAT rates by market
VAT_RATES = {
    "it": 0.22,  # Italy
    "de": 0.19,  # Germany
    "fr": 0.20,  # France
    "es": 0.21,  # Spain
    "uk": 0.20,  # UK
}

# Amazon commission rates by category
COMMISSION_RATES = {
    "Elettronica": 0.08,
    "Elettronica di consumo": 0.08,
    "Informatica": 0.07,
    "Computer": 0.07,
    "Grandi elettrodomestici": 0.08,
    "Giardino e giardinaggio": 0.15,
    "Casa e cucina": 0.15,
    "Strumenti musicali": 0.15,
    "Videogiochi": 0.15,
    "Alimentari e cura della casa": 0.15,
    "Salute e cura della persona": 0.15,
    "Sport e tempo libero": 0.15,
    "Auto e Moto": 0.15,
    "Fai da te": 0.15,
    "Giochi e giocattoli": 0.15,
    "Prima infanzia": 0.15,
    "Moda": 0.15,
    "Abbigliamento": 0.15,
    "Scarpe e borse": 0.15,
    "Prodotti per animali domestici": 0.15,
    # German categories
    "Elektronik": 0.08,
    "Computer & Zubehör": 0.07,
    "Küche, Haushalt & Wohnen": 0.15,
    # French categories
    "Électronique": 0.08,
    "Informatique": 0.07,
    "Cuisine & Maison": 0.15,
    # Spanish categories
    "Electrónica": 0.08,
    "Informática": 0.07,
    "Hogar y cocina": 0.15
}

# Default category commission if not found
DEFAULT_COMMISSION_RATE = 0.15

# Fixed fees
FIXED_FEE_PER_UNIT = 0.99  # €0.99 fixed fee per unit
DIGITAL_TAX_RATE = 0.03  # 3% digital services tax on referral fee

# Market data
MARKETS = {
    "it": {"name": "Amazon Italia", "flag": "🇮🇹", "currency": "EUR", "domain": "amazon.it"},
    "de": {"name": "Amazon Germania", "flag": "🇩🇪", "currency": "EUR", "domain": "amazon.de"},
    "fr": {"name": "Amazon Francia", "flag": "🇫🇷", "currency": "EUR", "domain": "amazon.fr"},
    "es": {"name": "Amazon Spagna", "flag": "🇪🇸", "currency": "EUR", "domain": "amazon.es"},
    "uk": {"name": "Amazon UK", "flag": "🇬🇧", "currency": "GBP", "domain": "amazon.co.uk"},
}

#################################
# DATA LOADING AND PROCESSING FUNCTIONS
#################################

def load_data(uploaded_file):
    """Load data from uploaded file (CSV or Excel)"""
    if not uploaded_file:
        return None
    
    fname = uploaded_file.name.lower()
    try:
        if fname.endswith(".xlsx"):
            return pd.read_excel(uploaded_file, dtype=str)
        else:
            try:
                return pd.read_csv(uploaded_file, sep=";", dtype=str)
            except:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, sep=",", dtype=str)
    except Exception as e:
        st.error(f"Errore nel caricamento del file {fname}: {str(e)}")
        return None

def parse_float(x):
    """Parse float values from string with currency symbols"""
    if not isinstance(x, str):
        return np.nan
    
    # Remove currency symbols and normalize decimal separator
    x_clean = x.replace("€", "").replace("£", "").replace("$", "").replace(",", ".").strip()
    
    try:
        return float(x_clean)
    except:
        return np.nan

def convert_currency(value, from_currency, to_currency, exchange_rate):
    """Convert value between currencies"""
    if from_currency == to_currency:
        return value
    
    if from_currency == "GBP" and to_currency == "EUR":
        return value * exchange_rate
    elif from_currency == "EUR" and to_currency == "GBP":
        return value / exchange_rate
    
    return value  # Default case if currencies not handled

#################################
# PRICE AND PROFIT CALCULATION FUNCTIONS
#################################

def calc_final_purchase_price(row, discount, vat_rates):
    """Calculate the final purchase price considering VAT and discount"""
    locale = row.get("Locale (base)", base_market).lower()
    gross = row["Price_Base"]
    
    if pd.isna(gross):
        return np.nan
    
    vat_rate = vat_rates.get(locale, 0.22)
    net_price = gross / (1 + vat_rate)
    
    # Different discount calculation based on market
    if locale == "it":
        # For Italian market, discount is applied to the gross price directly
        discount_amount = gross * discount
        final_price = net_price - discount_amount
    else:
        # For other markets, discount is applied to the net price
        final_price = net_price * (1 - discount)
    
    return round(final_price, 2)

def truncate_2dec(value):
    """Truncate value to 2 decimal places (Amazon's method)"""
    if value is None or np.isnan(value):
        return np.nan
    return math.floor(value * 100) / 100.0

def calc_referral_fee(category, price):
    """Calculate Amazon referral fee based on category"""
    rate = COMMISSION_RATES.get(category, DEFAULT_COMMISSION_RATE)
    referral = rate * price
    min_referral = 0.30  # Minimum referral fee
    return max(referral, min_referral)

def calc_fba_fee(row, locale):
    """Calculate estimated FBA fee based on category and market"""
    # This is a simplified estimation
    # For a more accurate calculation, would need product dimensions and weight
    category = row.get("Categories: Root (base)", "Other")
    
    # Base FBA fee (simplified model)
    if "Elettronica" in category or "Electronic" in category:
        base_fee = 2.70
    elif "Informatica" in category or "Computer" in category:
        base_fee = 2.40
    else:
        base_fee = 3.20
    
    # Adjust by market
    market_multipliers = {
        "it": 1.0,
        "de": 1.05,
        "fr": 1.10,
        "es": 1.0,
        "uk": 0.95
    }
    
    return base_fee * market_multipliers.get(locale, 1.0)

def calc_fees(category, price, include_fixed_fee=True):
    """Calculate all Amazon fees"""
    # Calculate referral fee
    referral_raw = calc_referral_fee(category, price)
    referral_fee = truncate_2dec(referral_raw)
    
    # Digital services tax
    digital_tax_raw = DIGITAL_TAX_RATE * referral_fee
    digital_tax = truncate_2dec(digital_tax_raw)
    
    # Fixed fee per unit
    fixed_fee = FIXED_FEE_PER_UNIT if include_fixed_fee else 0
    
    # Total fees
    total_fees = truncate_2dec(referral_fee + digital_tax + fixed_fee)
    
    return {
        "referral_fee": referral_fee,
        "digital_tax": digital_tax,
        "fixed_fee": fixed_fee,
        "total_fees": total_fees
    }

def calc_revenue_metrics(row, shipping_cost, market_type, vat_rates, include_fba=True, include_fixed_fee=True):
    """Calculate all revenue and profit metrics"""
    # Get category and price based on market type
    if market_type == "base":
        price = row["Price_Base"]
        locale = row.get("Locale (base)", base_market).lower()
        category = row.get("Categories: Root (base)", "Other")
    else:
        price = row["Price_Comp"]
        locale = row.get("Locale (comp)", "de").lower()
        category = row.get("Categories: Root (comp)", row.get("Categories: Root (base)", "Other"))
    
    if pd.isna(price):
        return pd.Series({
            "Prezzo_Lordo": np.nan,
            "Prezzo_Netto": np.nan,
            "Referral_Fee": np.nan,
            "Digital_Tax": np.nan,
            "FBA_Fee": np.nan,
            "Fixed_Fee": np.nan,
            "Total_Fees": np.nan,
            "Margine_Netto": np.nan,
            "Margine_Percentuale": np.nan,
            "ROI": np.nan
        })
    
    # Calculate net price (minus VAT)
    vat_rate = vat_rates.get(locale, 0.22)
    price_net = price / (1 + vat_rate)
    
    # Calculate Amazon fees
    fees = calc_fees(category, price, include_fixed_fee)
    total_amazon_fees = fees["total_fees"]
    
    # FBA fee
    fba_fee = calc_fba_fee(row, locale) if include_fba else 0
    
    # Calculate total costs
    total_costs = total_amazon_fees + shipping_cost + fba_fee
    
    # Calculate margins
    purchase_net = row.get("Acquisto_Netto", 0)
    margin_net = price_net - total_costs - purchase_net
    margin_pct = (margin_net / price) * 100 if price > 0 else 0
    roi = (margin_net / purchase_net) * 100 if purchase_net > 0 else 0
    
    return pd.Series({
        "Prezzo_Lordo": round(price, 2),
        "Prezzo_Netto": round(price_net, 2),
        "Referral_Fee": round(fees["referral_fee"], 2),
        "Digital_Tax": round(fees["digital_tax"], 2),
        "FBA_Fee": round(fba_fee, 2) if include_fba else 0,
        "Fixed_Fee": round(fees["fixed_fee"], 2) if include_fixed_fee else 0,
        "Total_Fees": round(total_amazon_fees + fba_fee, 2),
        "Margine_Netto": round(margin_net, 2),
        "Margine_Percentuale": round(margin_pct, 2),
        "ROI": round(roi, 2)
    })

#################################
# SIDEBAR CONFIGURATION
#################################

with st.sidebar:
    st.image("https://m.media-amazon.com/images/G/01/sell/images/prime-boxes/prime-boxes-2._CB1198675309_.svg", width=200)
    st.markdown("### Impostazioni Analisi")
    
    # File Upload Section
    st.markdown("#### 📤 Caricamento file")
    
    # Base market selection
    base_market = st.selectbox(
        "Mercato di Origine (Acquisto)",
        options=["it", "de", "fr", "es", "uk"],
        format_func=lambda x: f"{MARKETS[x]['flag']} {MARKETS[x]['name']}",
    )
    
    # Comparison markets selection
    comparison_markets = st.multiselect(
        "Mercati di Destinazione (Vendita)",
        options=["it", "de", "fr", "es", "uk"],
        default=["de", "fr", "es"] if base_market != "de" else ["it", "fr", "es"],
        format_func=lambda x: f"{MARKETS[x]['flag']} {MARKETS[x]['name']}",
    )
    
    # Remove base market from comparison if selected
    if base_market in comparison_markets:
        comparison_markets.remove(base_market)
        st.warning(f"Rimosso {MARKETS[base_market]['name']} dai mercati di confronto perché è già il mercato di origine.")
    
    # File uploaders
    files_base = st.file_uploader(
        f"Lista di Origine ({MARKETS[base_market]['flag']} {base_market.upper()})",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        help="Carica uno o più file del mercato di origine (dove acquisti)"
    )
    
    # ASIN extraction section
    if files_base:
        with st.expander("📋 Estrai ASINs dalla Lista di Origine", expanded=True):
            st.info("Questa funzione estrae tutti gli ASIN dai file caricati per facilitare la creazione delle liste di confronto.")
            
            # Load and extract ASINs from base files
            base_asins = []
            for file in files_base:
                df = load_data(file)
                if df is not None and 'ASIN' in df.columns:
                    base_asins.extend(df['ASIN'].dropna().unique().tolist())
            
            # Remove duplicates and sort
            unique_asins = sorted(list(set(base_asins)))
            
            if unique_asins:
                # Display count and sample
                st.write(f"Trovati **{len(unique_asins)}** ASIN unici nei file caricati.")
                
                # Format options
                format_option = st.radio(
                    "Formato di output:",
                    ["Un ASIN per riga", "ASINs separati da virgola", "ASINs separati da spazio"]
                )
                
                # Format the ASINs based on the selection
                if format_option == "Un ASIN per riga":
                    formatted_asins = "\n".join(unique_asins)
                elif format_option == "ASINs separati da virgola":
                    formatted_asins = ", ".join(unique_asins)
                else:  # Separated by space
                    formatted_asins = " ".join(unique_asins)
                
                # Create a text area with the ASINs
                st.text_area(
                    "ASINs estratti (puoi copiare e incollare)",
                    value=formatted_asins,
                    height=200
                )
                
                # Download buttons
                col1, col2 = st.columns(2)
                
                # CSV download
                csv_data = pd.DataFrame({"ASIN": unique_asins})
                csv_file = csv_data.to_csv(index=False).encode('utf-8')
                col1.download_button(
                    label="📥 Scarica come CSV",
                    data=csv_file,
                    file_name=f"asins_{base_market}.csv",
                    mime="text/csv"
                )
                
                # TXT download
                txt_file = formatted_asins.encode('utf-8')
                col2.download_button(
                    label="📥 Scarica come TXT",
                    data=txt_file,
                    file_name=f"asins_{base_market}.txt",
                    mime="text/plain"
                )
            else:
                st.warning("Nessun ASIN trovato nei file caricati o la colonna 'ASIN' non è presente nei file.")
    
    # Dynamically create file uploaders for each comparison market
    comparison_files = {}
    for market in comparison_markets:
        comparison_files[market] = st.file_uploader(
            f"Lista per {MARKETS[market]['flag']} {market.upper()} (Confronto)",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
            help=f"Carica uno o più file del mercato {market.upper()} (dove vendi)"
        )
    
    st.markdown("---")
    
    # Price reference settings
    st.markdown("#### 💰 Impostazioni Prezzo")
    
    ref_price_base = st.selectbox(
        "Prezzo di riferimento (Origine)",
        ["Buy Box: Current", "Amazon: Current", "New: Current"],
        help="Scegli quale prezzo usare per il calcolo dal mercato di origine"
    )
    
    ref_price_comp = st.selectbox(
        "Prezzo di riferimento (Destinazione)",
        ["Buy Box: Current", "Amazon: Current", "New: Current"],
        help="Scegli quale prezzo usare per il calcolo dai mercati di destinazione"
    )
    
    st.markdown("---")
    
    # Discount settings
    st.markdown("#### 🏷️ Sconti e Costi")
    
    discount_percent = st.slider(
        "Sconto per gli acquisti (%)",
        min_value=0.0,
        max_value=40.0,
        value=20.0,
        step=0.5,
        help="Percentuale di sconto sui prodotti acquistati (es. per acquisti in volume)"
    )
    discount = discount_percent / 100.0
    
    shipping_cost_rev = st.number_input(
        "Costo di Spedizione (€)",
        min_value=0.0,
        value=5.13,
        step=0.1,
        help="Costo di spedizione per unità da includere nel calcolo della redditività"
    )
    
    min_margin_percent = st.slider(
        "Margine minimo (%)",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=1.0,
        help="Margine percentuale minimo per considerare un'opportunità valida"
    )
    
    min_margin_euro = st.number_input(
        "Margine minimo (€)",
        min_value=0.0,
        value=5.0,
        step=1.0,
        help="Margine minimo in euro per considerare un'opportunità valida"
    )
    
    st.markdown("---")
    
    # Advanced settings
    with st.expander("Impostazioni Avanzate"):
        include_fba_fee = st.checkbox(
            "Includi FBA Fee",
            value=True,
            help="Includi la fee di Fulfillment by Amazon nel calcolo dei costi"
        )
        
        include_fixed_fee = st.checkbox(
            "Includi Fee Fissa per Unità",
            value=True,
            help="Includi la fee fissa di €0.99 per unità venduta"
        )
        
        custom_exchange_rate = st.number_input(
            "Tasso di Cambio GBP/EUR",
            min_value=0.5,
            max_value=2.0,
            value=1.18,
            step=0.01,
            help="Tasso di cambio personalizzato tra GBP e EUR per il mercato UK"
        )
    
    # Calculate button
    st.markdown("---")
    avvia = st.button("🔍 Calcola Opportunità", use_container_width=True)

#################################
# DATA PROCESSING EXECUTION
#################################

if avvia:
    with st.spinner("Analisi in corso..."):
        # Validate inputs
        if not files_base:
            st.error("🚫 Devi caricare almeno un file per la Lista di Origine.")
            st.stop()
        
        empty_comparison = True
        for market in comparison_markets:
            if comparison_files.get(market):
                empty_comparison = False
                break
        
        if empty_comparison:
            st.error("🚫 Devi caricare almeno un file per un Mercato di Confronto.")
            st.stop()
        
        # Load base market data
        base_list = [load_data(f) for f in files_base if f is not None]
        base_list = [df for df in base_list if df is not None and not df.empty]
        
        if not base_list:
            st.error("🚫 Nessun file di origine valido caricato.")
            st.stop()
        
        df_base = pd.concat(base_list, ignore_index=True)
        df_base["Locale (base)"] = base_market  # Add base market locale
        
        # Process each comparison market
        all_opportunities = []
        
        for market in comparison_markets:
            if not comparison_files.get(market):
                continue
                
            # Load comparison market data
            comp_list = [load_data(f) for f in comparison_files[market] if f is not None]
            comp_list = [df for df in comp_list if df is not None and not df.empty]
            
            if not comp_list:
                st.warning(f"⚠️ Nessun file valido caricato per il mercato {market.upper()}.")
                continue
                
            df_comp = pd.concat(comp_list, ignore_index=True)
            df_comp["Locale (comp)"] = market  # Add comparison market locale
            
            # Check for ASIN column
            if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
                st.error(f"🚫 Assicurati che i file per {base_market.upper()} e {market.upper()} contengano la colonna ASIN.")
                continue
                
            # Merge datasets on ASIN
            df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
            
            if df_merged.empty:
                st.warning(f"⚠️ Nessuna corrispondenza trovata tra {base_market.upper()} e {market.upper()}.")
                continue
                
            # Extract price columns
            price_col_base = f"{ref_price_base} (base)"
            price_col_comp = f"{ref_price_comp} (comp)"
            
            df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(parse_float)
            df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(parse_float)
            
            # Handle currency conversion for UK market
            if base_market == "uk":
                df_merged["Price_Base"] = df_merged["Price_Base"].apply(
                    lambda x: convert_currency(x, "GBP", "EUR", custom_exchange_rate) if not pd.isna(x) else np.nan
                )
            
            if market == "uk":
                df_merged["Price_Comp"] = df_merged["Price_Comp"].apply(
                    lambda x: convert_currency(x, "GBP", "EUR", custom_exchange_rate) if not pd.isna(x) else np.nan
                )
            
            # Calculate net purchase price with discount
            df_merged["Acquisto_Netto"] = df_merged.apply(
                lambda row: calc_final_purchase_price(row, discount, VAT_RATES), axis=1
            )
            
            # Calculate revenue metrics for base market
            df_revenue_base = df_merged.apply(
                lambda row: calc_revenue_metrics(
                    row, shipping_cost_rev, "base", VAT_RATES, 
                    include_fba=include_fba_fee, include_fixed_fee=include_fixed_fee
                ), 
                axis=1
            )
            df_revenue_base = df_revenue_base.add_suffix("_Origine")
            
            # Calculate revenue metrics for comparison market
            df_revenue_comp = df_merged.apply(
                lambda row: calc_revenue_metrics(
                    row, shipping_cost_rev, "comp", VAT_RATES,
                    include_fba=include_fba_fee, include_fixed_fee=include_fixed_fee
                ), 
                axis=1
            )
            df_revenue_comp = df_revenue_comp.add_suffix("_Confronto")
            
            # Combine all data
            result_columns = [
                "ASIN", "Title (base)", "Locale (base)", "Locale (comp)",
                "Price_Base", "Price_Comp", "Acquisto_Netto"
            ]
            
            # Add categories if available
            if "Categories: Root (base)" in df_merged.columns:
                result_columns.append("Categories: Root (base)")
            if "Categories: Root (comp)" in df_merged.columns:
                result_columns.append("Categories: Root (comp)")
                
            df_result = pd.concat([
                df_merged[result_columns],
                df_revenue_base,
                df_revenue_comp
            ], axis=1)
            
            # Calculate arbitrage opportunity metrics
            df_result["Differenza_Prezzo"] = df_result["Price_Comp"] - df_result["Price_Base"]
            df_result["Differenza_Percentuale"] = (df_result["Differenza_Prezzo"] / df_result["Price_Base"] * 100).round(2)
            df_result["Profitto_Arbitraggio"] = df_result["Margine_Netto_Confronto"]
            df_result["Profitto_Percentuale"] = df_result["Margine_Percentuale_Confronto"]
            df_result["ROI_Arbitraggio"] = (df_result["Profitto_Arbitraggio"] / df_result["Acquisto_Netto"] * 100).round(2)
            
            # Filter for valid opportunities
            valid_opportunities = df_result[
                (df_result["Profitto_Arbitraggio"] >= min_margin_euro) & 
                (df_result["Profitto_Percentuale"] >= min_margin_percent)
            ].copy()
            
            if not valid_opportunities.empty:
                valid_opportunities["Opportunità_Score"] = (
                    valid_opportunities["Profitto_Arbitraggio"] * 0.6 + 
                    valid_opportunities["Profitto_Percentuale"] * 0.2 + 
                    valid_opportunities["ROI_Arbitraggio"] * 0.2
                ).round(2)
                
                valid_opportunities["Mercato_Origine"] = valid_opportunities["Locale (base)"].apply(
                    lambda x: f"{get_market_flag(x)} {x.upper()}"
                )
                valid_opportunities["Mercato_Destinazione"] = valid_opportunities["Locale (comp)"].apply(
                    lambda x: f"{get_market_flag(x)} {x.upper()}"
                )
                
                all_opportunities.append(valid_opportunities)
        
        # Combine all opportunities
        if all_opportunities:
            final_opportunities = pd.concat(all_opportunities, ignore_index=True)
            final_opportunities = final_opportunities.sort_values(by="Opportunità_Score", ascending=False)
            
            # Store in session state
            st.session_state["opportunities"] = final_opportunities
            st.session_state["results_available"] = True
            st.session_state["calculation_history"].append({
                "timestamp": pd.Timestamp.now(),
                "base_market": base_market,
                "comparison_markets": comparison_markets,
                "discount": discount_percent,
                "num_opportunities": len(final_opportunities)
            })
            
            # Success message
            st.success(f"✅ Analisi completata! Trovate {len(final_opportunities)} opportunità di arbitraggio redditizie.")
        else:
            st.warning("⚠️ Nessuna opportunità di arbitraggio trovata che soddisfi i criteri minimi di margine.")
            st.session_state["results_available"] = False

#################################
# RESULTS VISUALIZATION
#################################

if st.session_state["results_available"]:
    opportunities = st.session_state["opportunities"]
    
    # Create tabs for different views
    tabs = st.tabs(["📊 Dashboard", "📋 Tabella Dettagliata", "📈 Grafici", "🔍 Analisi Prodotto", "📝 Note"])
    
    # DASHBOARD TAB
    with tabs[0]:
        # Summary metrics
        st.markdown('<h2 class="sub-header">Riepilogo Opportunità</h2>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{len(opportunities)}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Opportunità Totali</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            avg_profit = opportunities["Profitto_Arbitraggio"].mean()
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">€{avg_profit:.2f}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Profitto Medio</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            avg_roi = opportunities["ROI_Arbitraggio"].mean()
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{avg_roi:.1f}%</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">ROI Medio</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            total_potential = opportunities["Profitto_Arbitraggio"].sum()
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">€{total_potential:.2f}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Potenziale Totale</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Top opportunities
        st.markdown('<h3 class="sub-header">Top 10 Migliori Opportunità</h3>', unsafe_allow_html=True)
        
        top_opportunities = opportunities.head(10)
        
        for i, row in top_opportunities.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{row['Title (base)'][:80]}...**")
                    st.markdown(f"ASIN: `{row['ASIN']}` | {row['Mercato_Origine']} → {row['Mercato_Destinazione']}")
                
                with col2:
                    st.markdown(f"Prezzo Acquisto: **€{row['Price_Base']:.2f}**")
                    st.markdown(f"Prezzo Vendita: **€{row['Price_Comp']:.2f}**")
                    st.markdown(f"Netto Acquisto: **€{row['Acquisto_Netto']:.2f}**")
                
                with col3:
                    st.markdown(f"Profitto: **€{row['Profitto_Arbitraggio']:.2f}**")
                    st.markdown(f"ROI: **{row['ROI_Arbitraggio']:.1f}%**")
                    st.markdown(f"Score: **{row['Opportunità_Score']:.1f}**")
                
                st.markdown("---")
        
        # Market distribution
        st.markdown('<h3 class="sub-header">Distribuzione per Mercato</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            market_counts = opportunities["Mercato_Destinazione"].value_counts().reset_index()
            market_counts.columns = ["Mercato", "Conteggio"]
            
            fig = px.bar(
                market_counts,
                x="Mercato",
                y="Conteggio",
                color="Conteggio",
                color_continuous_scale="Oranges",
                title="Opportunità per Mercato di Destinazione"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            profit_by_market = opportunities.groupby("Mercato_Destinazione")["Profitto_Arbitraggio"].mean().reset_index()
            profit_by_market.columns = ["Mercato", "Profitto Medio"]
            
            fig = px.bar(
                profit_by_market,
                x="Mercato",
                y="Profitto Medio",
                color="Profitto Medio",
                color_continuous_scale="Greens",
                title="Profitto Medio per Mercato di Destinazione"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # DETAILED TABLE TAB
    with tabs[1]:
        st.markdown('<h2 class="sub-header">Tabella Dettagliata delle Opportunità</h2>', unsafe_allow_html=True)
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_profit_filter = st.slider(
                "Profitto Minimo (€)",
                min_value=float(min_margin_euro),
                max_value=float(opportunities["Profitto_Arbitraggio"].max() + 5),
                value=float(min_margin_euro),
                step=1.0
            )
        
        with col2:
            min_roi_filter = st.slider(
                "ROI Minimo (%)",
                min_value=0.0,
                max_value=float(opportunities["ROI_Arbitraggio"].max() + 5),
                value=0.0,
                step=5.0
            )
        
        with col3:
            market_filter = st.multiselect(
                "Mercati di Destinazione",
                options=opportunities["Mercato_Destinazione"].unique(),
                default=opportunities["Mercato_Destinazione"].unique()
            )
        
        # Apply filters
        filtered_opportunities = opportunities[
            (opportunities["Profitto_Arbitraggio"] >= min_profit_filter) &
            (opportunities["ROI_Arbitraggio"] >= min_roi_filter) &
            (opportunities["Mercato_Destinazione"].isin(market_filter))
        ]
        
        # Show number of filtered results
        st.write(f"Mostrando {len(filtered_opportunities)} opportunità su {len(opportunities)} totali")
        
        # Prepare DataFrame for display
        display_columns = [
            "ASIN", "Title (base)", "Mercato_Origine", "Mercato_Destinazione",
            "Price_Base", "Price_Comp", "Acquisto_Netto", "Profitto_Arbitraggio",
            "Profitto_Percentuale", "ROI_Arbitraggio", "Opportunità_Score"
        ]
        
        display_df = filtered_opportunities[display_columns].copy()
        
        # Rename columns for display
        display_df.columns = [
            "ASIN", "Titolo", "Origine", "Destinazione",
            "Prezzo Acquisto", "Prezzo Vendita", "Acquisto Netto", "Profitto",
            "Margine %", "ROI %", "Score"
        ]
        
        # Configure the grid
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_column("ASIN", width=120)
        gb.configure_column("Titolo", width=300)
        gb.configure_column("Prezzo Acquisto", type=["numericColumn", "numberColumnFilter"], precision=2, width=130)
        gb.configure_column("Prezzo Vendita", type=["numericColumn", "numberColumnFilter"], precision=2, width=130)
        gb.configure_column("Acquisto Netto", type=["numericColumn", "numberColumnFilter"], precision=2, width=130)
        gb.configure_column("Profitto", type=["numericColumn", "numberColumnFilter"], precision=2, width=120)
        gb.configure_column("Margine %", type=["numericColumn", "numberColumnFilter"], precision=1, width=120)
        gb.configure_column("ROI %", type=["numericColumn", "numberColumnFilter"], precision=1, width=120)
        gb.configure_column("Score", type=["numericColumn", "numberColumnFilter"], precision=1, width=100)
        
        grid_options = gb.build()
        
        # Display the grid
        AgGrid(
            display_df,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            height=600,
            fit_columns_on_grid_load=False
        )
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = filtered_opportunities.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="📥 Scarica come CSV",
                data=csv_data,
                file_name="opportunita_arbitraggio.csv",
                mime="text/csv"
            )
        
        with col2:
            # Create Excel file
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                filtered_opportunities.to_excel(writer, sheet_name="Opportunità", index=False)
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📥 Scarica come Excel",
                data=excel_data,
                file_name="opportunita_arbitraggio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # CHARTS TAB
    with tabs[2]:
        st.markdown('<h2 class="sub-header">Grafici e Visualizzazioni</h2>', unsafe_allow_html=True)
        
        chart_type = st.selectbox(
            "Seleziona il tipo di grafico",
            [
                "Distribuzione dei Profitti", 
                "Confronto Mercati", 
                "ROI vs Profitto", 
                "Prezzo Acquisto vs Vendita"
            ]
        )
        
        if chart_type == "Distribuzione dei Profitti":
            fig = px.histogram(
                opportunities,
                x="Profitto_Arbitraggio",
                nbins=30,
                color_discrete_sequence=["#FF9900"],
                title="Distribuzione dei Profitti"
            )
            fig.update_layout(
                xaxis_title="Profitto (€)",
                yaxis_title="Numero di Opportunità",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics
            st.markdown("### Statistiche di Profitto")
            stats_df = pd.DataFrame({
                "Statistica": ["Minimo", "1° Quartile", "Mediana", "Media", "3° Quartile", "Massimo"],
                "Valore": [
                    f"€{opportunities['Profitto_Arbitraggio'].min():.2f}",
                    f"€{opportunities['Profitto_Arbitraggio'].quantile(0.25):.2f}",
                    f"€{opportunities['Profitto_Arbitraggio'].median():.2f}",
                    f"€{opportunities['Profitto_Arbitraggio'].mean():.2f}",
                    f"€{opportunities['Profitto_Arbitraggio'].quantile(0.75):.2f}",
                    f"€{opportunities['Profitto_Arbitraggio'].max():.2f}"
                ]
            })
            st.table(stats_df)
        
        elif chart_type == "Confronto Mercati":
            pivot_data = opportunities.pivot_table(
                index="Mercato_Destinazione",
                values=["Profitto_Arbitraggio", "ROI_Arbitraggio", "Opportunità_Score"],
                aggfunc="mean"
            ).reset_index()
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=pivot_data["Mercato_Destinazione"],
                y=pivot_data["Profitto_Arbitraggio"],
                name="Profitto Medio",
                marker_color="#FF9900"
            ))
            
            fig.add_trace(go.Bar(
                x=pivot_data["Mercato_Destinazione"],
                y=pivot_data["ROI_Arbitraggio"],
                name="ROI Medio",
                marker_color="#232F3E",
                yaxis="y2"
            ))
            
            fig.update_layout(
                title="Confronto Mercati: Profitto vs ROI",
                xaxis_title="Mercato di Destinazione",
                yaxis=dict(
                    title="Profitto Medio (€)",
                    side="left"
                ),
                yaxis2=dict(
                    title="ROI Medio (%)",
                    side="right",
                    overlaying="y"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Table with detailed stats
            st.markdown("### Statistiche per Mercato")
            
            detailed_stats = opportunities.groupby("Mercato_Destinazione").agg({
                "ASIN": "count",
                "Profitto_Arbitraggio": ["mean", "min", "max"],
                "ROI_Arbitraggio": ["mean", "min", "max"]
            }).reset_index()
            
            detailed_stats.columns = [
                "Mercato", "Conteggio", 
                "Profitto Medio", "Profitto Min", "Profitto Max",
                "ROI Medio", "ROI Min", "ROI Max"
            ]
            
            st.dataframe(detailed_stats, height=300)
        
        elif chart_type == "ROI vs Profitto":
            fig = px.scatter(
                opportunities,
                x="Profitto_Arbitraggio",
                y="ROI_Arbitraggio",
                color="Mercato_Destinazione",
                size="Opportunità_Score",
                hover_name="Title (base)",
                hover_data=["ASIN", "Price_Base", "Price_Comp", "Acquisto_Netto"],
                title="ROI vs Profitto per Opportunità",
                height=600,
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            
            fig.update_layout(
                xaxis_title="Profitto (€)",
                yaxis_title="ROI (%)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Correlation
            corr = opportunities["Profitto_Arbitraggio"].corr(opportunities["ROI_Arbitraggio"])
            st.info(f"Correlazione tra Profitto e ROI: {corr:.2f}")
        
        elif chart_type == "Prezzo Acquisto vs Vendita":
            fig = px.scatter(
                opportunities,
                x="Price_Base",
                y="Price_Comp",
                color="Profitto_Arbitraggio",
                size="Opportunità_Score",
                hover_name="Title (base)",
                hover_data=["ASIN", "Mercato_Destinazione", "Acquisto_Netto", "Profitto_Arbitraggio", "ROI_Arbitraggio"],
                title="Prezzo di Acquisto vs Prezzo di Vendita",
                height=600,
                color_continuous_scale="Viridis"
            )
            
            # Add reference line (y = x)
            fig.add_trace(
                go.Scatter(
                    x=[0, opportunities["Price_Base"].max() * 1.1],
                    y=[0, opportunities["Price_Base"].max() * 1.1],
                    mode="lines",
                    line=dict(dash="dash", color="gray"),
                    name="Prezzo Uguale"
                )
            )
            
            fig.update_layout(
                xaxis_title="Prezzo di Acquisto (€)",
                yaxis_title="Prezzo di Vendita (€)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Average price difference
            avg_diff = (opportunities["Price_Comp"] - opportunities["Price_Base"]).mean()
            avg_diff_pct = (opportunities["Differenza_Percentuale"]).mean()
            
            st.info(f"Differenza Media di Prezzo: {avg_diff:.2f}€ ({avg_diff_pct:.1f}%)")
    
    # PRODUCT ANALYSIS TAB
    with tabs[3]:
        st.markdown('<h2 class="sub-header">Analisi Prodotto Dettagliata</h2>', unsafe_allow_html=True)
        
        # Product selector
        selected_asin = st.selectbox(
            "Seleziona un prodotto da analizzare",
            options=opportunities["ASIN"].unique(),
            format_func=lambda asin: f"{asin} - {opportunities[opportunities['ASIN'] == asin]['Title (base)'].values[0][:60]}..."
        )
        
        if selected_asin:
            # Get product data
            product_data = opportunities[opportunities["ASIN"] == selected_asin].copy()
            
            # Basic info
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"## {product_data['Title (base)'].values[0]}")
                st.markdown(f"**ASIN:** {selected_asin}")
                
                if "Categories: Root (base)" in product_data.columns:
                    st.markdown(f"**Categoria:** {product_data['Categories: Root (base)'].values[0]}")
            
            with col2:
                st.markdown("### Punteggio Opportunità")
                
                # Calculate average score
                avg_score = product_data["Opportunità_Score"].mean()
                
                # Display gauge chart
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=avg_score,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "Score"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#FF9900"},
                        "steps": [
                            {"range": [0, 30], "color": "#f2f2f2"},
                            {"range": [30, 70], "color": "#e6e6e6"},
                            {"range": [70, 100], "color": "#d9d9d9"}
                        ],
                        "threshold": {
                            "line": {"color": "green", "width": 4},
                            "thickness": 0.75,
                            "value": avg_score
                        }
                    }
                ))
                
                fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)
            
            # Market comparison
            st.markdown("### Confronto tra i mercati")
            
            # Create table
            market_data = product_data[[
                "Mercato_Destinazione", "Price_Base", "Price_Comp", "Acquisto_Netto",
                "Profitto_Arbitraggio", "ROI_Arbitraggio", "Opportunità_Score"
            ]].copy()
            
            market_data.columns = [
                "Mercato", "Prezzo Origine", "Prezzo Destinazione", "Costo Acquisto Netto",
                "Profitto", "ROI %", "Score"
            ]
            
            # Add arrows to indicate market
            market_data["Mercato"] = product_data["Mercato_Origine"].values[0] + " → " + market_data["Mercato"]
            
            # Format numbers
            market_data["Prezzo Origine"] = market_data["Prezzo Origine"].round(2)
            market_data["Prezzo Destinazione"] = market_data["Prezzo Destinazione"].round(2)
            market_data["Costo Acquisto Netto"] = market_data["Costo Acquisto Netto"].round(2)
            market_data["Profitto"] = market_data["Profitto"].round(2)
            market_data["ROI %"] = market_data["ROI %"].round(1)
            market_data["Score"] = market_data["Score"].round(1)
            
            # Display as table
            st.table(market_data)
            
            # Detailed cost breakdown
            st.markdown("### Dettaglio Costi e Ricavi")
            
            # Select market for breakdown
            if len(product_data) > 1:
                selected_market = st.selectbox(
                    "Seleziona il mercato da analizzare",
                    options=product_data["Mercato_Destinazione"].unique()
                )
                
                # Filter data for selected market
                market_product = product_data[product_data["Mercato_Destinazione"] == selected_market].iloc[0]
            else:
                market_product = product_data.iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Costi")
                
                costs_data = {
                    "Voce": [
                        "Acquisto Prodotto (Netto)",
                        "Referral Fee",
                        "Digital Services Tax",
                        "FBA Fee",
                        "Fee Fissa per Unità",
                        "Spedizione"
                    ],
                    "Importo": [
                        market_product["Acquisto_Netto"],
                        market_product["Referral_Fee_Confronto"],
                        market_product["Digital_Tax_Confronto"],
                        market_product["FBA_Fee_Confronto"],
                        market_product["Fixed_Fee_Confronto"],
                        shipping_cost_rev
                    ]
                }
                
                costs_df = pd.DataFrame(costs_data)
                costs_df["Importo"] = costs_df["Importo"].round(2)
                
                # Add total
                costs_df.loc[len(costs_df)] = ["TOTALE COSTI", costs_df["Importo"].sum()]
                
                # Format as table
                st.table(costs_df)
                
                # Pie chart of costs
                fig = px.pie(
                    costs_df[:-1],  # Exclude total
                    values="Importo",
                    names="Voce",
                    title="Ripartizione dei Costi",
                    color_discrete_sequence=px.colors.sequential.Oranges
                )
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Ricavi e Profitto")
                
                revenue_data = {
                    "Voce": [
                        "Prezzo di Vendita Lordo",
                        "IVA",
                        "Prezzo di Vendita Netto",
                        "Totale Costi",
                        "Profitto Netto"
                    ],
                    "Importo": [
                        market_product["Prezzo_Lordo_Confronto"],
                        market_product["Prezzo_Lordo_Confronto"] - market_product["Prezzo_Netto_Confronto"],
                        market_product["Prezzo_Netto_Confronto"],
                        costs_df["Importo"].sum(),
                        market_product["Margine_Netto_Confronto"]
                    ]
                }
                
                revenue_df = pd.DataFrame(revenue_data)
                revenue_df["Importo"] = revenue_df["Importo"].round(2)
                
                # Format as table
                st.table(revenue_df)
                
                # Waterfall chart
                waterfall_data = {
                    "Voce": [
                        "Prezzo di Vendita Netto",
                        "Acquisto Prodotto",
                        "Referral Fee",
                        "Digital Services Tax",
                        "FBA Fee",
                        "Fee Fissa per Unità",
                        "Spedizione",
                        "Profitto Netto"
                    ],
                    "Importo": [
                        market_product["Prezzo_Netto_Confronto"],
                        -market_product["Acquisto_Netto"],
                        -market_product["Referral_Fee_Confronto"],
                        -market_product["Digital_Tax_Confronto"],
                        -market_product["FBA_Fee_Confronto"],
                        -market_product["Fixed_Fee_Confronto"],
                        -shipping_cost_rev,
                        market_product["Margine_Netto_Confronto"]
                    ],
                    "Tipo": [
                        "Ricavo",
                        "Costo",
                        "Costo",
                        "Costo",
                        "Costo",
                        "Costo",
                        "Costo",
                        "Profitto"
                    ]
                }
                
                waterfall_df = pd.DataFrame(waterfall_data)
                
                # Create waterfall chart
                fig = go.Figure(go.Waterfall(
                    name="Profitto",
                    orientation="v",
                    measure=["absolute"] + ["relative"] * 6 + ["total"],
                    x=waterfall_df["Voce"],
                    y=waterfall_df["Importo"],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "#FF9900"}},
                    increasing={"marker": {"color": "#232F3E"}},
                    totals={"marker": {"color": "green"}}
                ))
                
                fig.update_layout(
                    title="Analisi Profitto",
                    height=400,
                    xaxis_title="Componente",
                    yaxis_title="€"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # ROI Analysis
            st.markdown("### Analisi ROI e Redditività")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                roi = market_product["ROI_Arbitraggio"]
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{roi:.1f}%</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-label">Return on Investment</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if roi < 20:
                    roi_comment = "ROI basso, opportunità con margine di sicurezza ridotto."
                elif roi < 50:
                    roi_comment = "ROI nella media, opportunità interessante."
                else:
                    roi_comment = "ROI eccellente, opportunità ad alto rendimento!"
                
                st.write(roi_comment)
            
            with col2:
                margin_pct = market_product["Margine_Percentuale_Confronto"]
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{margin_pct:.1f}%</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-label">Margine Percentuale</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if margin_pct < 10:
                    margin_comment = "Margine basso, attenzione ai costi imprevisti."
                elif margin_pct < 25:
                    margin_comment = "Margine nella media, buona opportunità."
                else:
                    margin_comment = "Margine eccellente, opportunità molto redditizia!"
                
                st.write(margin_comment)
            
            with col3:
                profit = market_product["Profitto_Arbitraggio"]
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">€{profit:.2f}</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-label">Profitto Netto</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if profit < 5:
                    profit_comment = "Profitto basso, considerare quantità maggiori."
                elif profit < 15:
                    profit_comment = "Profitto nella media, buona opportunità."
                else:
                    profit_comment = "Profitto eccellente, ottima opportunità!"
                
                st.write(profit_comment)
            
            # Amazon links
            st.markdown("### Link ai Prodotti")
            
            col1, col2 = st.columns(2)
            
            with col1:
                base_url = f"https://www.{MARKETS[market_product['Locale (base)'].lower()]['domain']}/dp/{selected_asin}"
                st.markdown(f"[🔗 Visualizza su {market_product['Mercato_Origine']}]({base_url})")
            
            with col2:
                comp_url = f"https://www.{MARKETS[market_product['Locale (comp)'].lower()]['domain']}/dp/{selected_asin}"
                st.markdown(f"[🔗 Visualizza su {market_product['Mercato_Destinazione']}]({comp_url})")
    
    # NOTES TAB
    with tabs[4]:
        st.markdown('<h2 class="sub-header">Note e Considerazioni</h2>', unsafe_allow_html=True)
        
        # Input for notes
        if "notes" not in st.session_state:
            st.session_state["notes"] = ""
        
        notes = st.text_area(
            "Aggiungi note o appunti su questa analisi",
            value=st.session_state["notes"],
            height=300
        )
        
        st.session_state["notes"] = notes
        
        if st.button("Salva Note"):
            st.success("✅ Note salvate correttamente.")
        
        # Calculation history
        st.markdown("### Cronologia Calcoli")
        
        history = st.session_state["calculation_history"]
        
        if history:
            history_df = pd.DataFrame([
                {
                    "Data e Ora": h["timestamp"].strftime("%d-%m-%Y %H:%M"),
                    "Mercato Origine": h["base_market"].upper(),
                    "Mercati Destinazione": ", ".join([m.upper() for m in h["comparison_markets"]]),
                    "Sconto": f"{h['discount']:.1f}%",
                    "Opportunità Trovate": h["num_opportunities"]
                }
                for h in history
            ])
            
            st.dataframe(history_df, height=200)
        else:
            st.info("Nessun calcolo precedente trovato.")
        
        # Disclaimer and help
        st.markdown("---")
        st.markdown("### Informazioni e Aiuto")
        
        with st.expander("Informazioni sul calcolo del Revenue"):
            st.markdown("""
            **Come vengono calcolati i profitti:**
            
            1. **Prezzo Netto**: Il prezzo di vendita al netto dell'IVA del mercato di destinazione
            2. **Costo di Acquisto**: Il prezzo di acquisto al netto dell'IVA con lo sconto applicato
            3. **Amazon Fees**:
                - Referral Fee: Commissione basata sulla categoria del prodotto
                - Digital Services Tax: 3% sulla Referral Fee
                - FBA Fee (opzionale): Stimata in base alla categoria del prodotto
                - Fee Fissa (opzionale): €0.99 per ogni vendita
            4. **Costi di Spedizione**: Costi fissi per unità specificati nelle impostazioni
            5. **Profitto Netto**: Prezzo Netto - Costi Amazon - Costo di Acquisto - Spedizione
            
            L'app calcola automaticamente tutte queste componenti per identificare le migliori opportunità di arbitraggio.
            """)
        
        with st.expander("Consigli per ottimizzare le analisi"):
            st.markdown("""
            **Suggerimenti per trovare le migliori opportunità:**
            
            1. **Utilizzare i filtri** per concentrarsi su prodotti con margini e ROI più alti
            2. **Confrontare più mercati** per identificare le migliori destinazioni per specifiche categorie
            3. **Considerare il volume potenziale** oltre al margine unitario
            4. **Analizzare regolarmente** per catturare opportunità temporanee
            5. **Iniziare con prodotti noti** per ridurre i rischi nelle prime operazioni
            
            Ricorda che i calcoli sono basati sui prezzi attuali, che potrebbero cambiare rapidamente su Amazon.
            """)
        
        # Footer
        st.markdown("---")
        st.markdown('<div class="footer">Amazon Market Analyzer Pro - Versione 2.0</div>', unsafe_allow_html=True)
else:
    # Welcome screen when no results are available
    st.markdown('<h2 class="sub-header">Benvenuto in Amazon Market Analyzer Pro</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 🚀 Inizia la tua analisi di arbitraggio cross-border su Amazon!
    
    **Come utilizzare l'applicazione:**
    
    1. **Carica i tuoi file** nella barra laterale:
       - Lista di origine (dove acquisti i prodotti)
       - Liste di confronto (dove rivendi i prodotti)
    
    2. **Configura le impostazioni**:
       - Scegli i mercati di interesse
       - Imposta lo sconto per gli acquisti
       - Configura le soglie di margine minimo
    
    3. **Ottieni risultati dettagliati**:
       - Prodotti con le migliori opportunità di arbitraggio
       - Calcoli precisi di costi e profitti
       - Visualizzazioni e grafici esplicativi
    
    #### I file devono includere:
    - Colonna **ASIN** (obbligatoria)
    - Colonna con i prezzi (es. "Buy Box: Current")
    - Idealmente anche la categoria del prodotto
    
    **Compatibile con file CSV ed Excel (.csv, .xlsx)**
    """)
    
    # Sample files section
    st.markdown("---")
    st.markdown("### 📊 Esempio di File Compatibili")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Esempio di colonne necessarie:**
        - ASIN
        - Title
        - Buy Box: Current
        - Amazon: Current
        - New: Current
        - Categories: Root
        
        I file devono essere in formato CSV o Excel.
        """)
    
    with col2:
        st.image("https://m.media-amazon.com/images/G/01/sell/images/Capture-tools-Seller-app-2._CB1198675309_.png", width=300)

# End of the application