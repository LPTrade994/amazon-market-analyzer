import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO
import uuid

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
    .dataframe {
        font-size: 0.9rem !important;
    }
    .dataframe th {
        background-color: #f0f0f0;
        padding: 8px !important;
    }
    .dataframe td {
        padding: 8px !important;
    }
    .cart-item {
        margin-bottom: 10px; 
        padding: 8px; 
        background-color: #f0f0f0; 
        border-radius: 5px;
    }
    .remove-btn {
        font-size: 10px; 
        padding: 2px 5px; 
        float: right;
        background-color: #ff6b6b;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
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
if 'cart_items' not in st.session_state:
    st.session_state['cart_items'] = []

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
# SIDEBAR CONFIGURATION
#################################

with st.sidebar:
    st.image("https://m.media-amazon.com/images/G/01/sell/images/prime-boxes/prime-boxes-2._CB1198675309_.svg", width=200)
    st.markdown("### Impostazioni Analisi")
    
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
    st.markdown("#### 📤 Caricamento file")
    files_base = st.file_uploader(
        f"Lista di Origine ({MARKETS[base_market]['flag']} {base_market.upper()})",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        help="Carica uno o più file del mercato di origine (dove acquisti)"
    )
    
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

# Cart management functions
def add_to_cart(asin, title, profit, origin, destination, price_origin, price_dest):
    """Add product to cart"""
    if 'cart_items' not in st.session_state:
        st.session_state['cart_items'] = []
    
    # Check if product is already in cart
    for item in st.session_state['cart_items']:
        if item['asin'] == asin and item['destination'] == destination:
            st.warning(f"Prodotto {asin} per il mercato {destination} già presente nel carrello.")
            return
    
    # Add to cart
    st.session_state['cart_items'].append({
        'id': str(uuid.uuid4()),
        'asin': asin,
        'title': title,
        'profit': profit,
        'origin': origin,
        'destination': destination,
        'price_origin': price_origin,
        'price_dest': price_dest
    })
    st.success(f"Prodotto {asin} aggiunto al carrello per il mercato {destination}.")

def remove_from_cart(item_id):
    """Remove product from cart"""
    if 'cart_items' in st.session_state:
        st.session_state['cart_items'] = [item for item in st.session_state['cart_items'] if item['id'] != item_id]

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
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(opportunities)}</div>
                <div class="metric-label">Opportunità Totali</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_profit = opportunities["Profitto_Arbitraggio"].mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">€{avg_profit:.2f}</div>
                <div class="metric-label">Profitto Medio</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            avg_roi = opportunities["ROI_Arbitraggio"].mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_roi:.1f}%</div>
                <div class="metric-label">ROI Medio</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            max_profit = opportunities["Profitto_Arbitraggio"].max()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">€{max_profit:.2f}</div>
                <div class="metric-label">Profitto Massimo</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Market distribution
        st.markdown('<h3 class="sub-header">Distribuzione per Mercato</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Source markets pie chart
            source_counts = opportunities["Mercato_Origine"].value_counts()
            fig_source = px.pie(
                names=source_counts.index,
                values=source_counts.values,
                title="Mercati di Origine",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4
            )
            fig_source.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_source, use_container_width=True)
            
        with col2:
            # Destination markets pie chart
            dest_counts = opportunities["Mercato_Destinazione"].value_counts()
            fig_dest = px.pie(
                names=dest_counts.index,
                values=dest_counts.values,
                title="Mercati di Destinazione",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4
            )
            fig_dest.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_dest, use_container_width=True)
            
        # Top opportunities
        st.markdown('<h3 class="sub-header">Top 5 Opportunità</h3>', unsafe_allow_html=True)
        
        top_opps = opportunities.head(5).copy()
        top_opps["Link_Origine"] = top_opps.apply(
            lambda row: f"https://www.{MARKETS[row['Locale (base)']]['domain']}/dp/{row['ASIN']}", 
            axis=1
        )
        top_opps["Link_Destinazione"] = top_opps.apply(
            lambda row: f"https://www.{MARKETS[row['Locale (comp)']]['domain']}/dp/{row['ASIN']}", 
            axis=1
        )
        
        for idx, row in top_opps.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <h4>{row['Title (base)'][:100]}...</h4>
                    <p>ASIN: {row['ASIN']} | Categoria: {row.get('Categories: Root (base)', 'N/D')}</p>
                    <p>Mercato: {row['Mercato_Origine']} → {row['Mercato_Destinazione']} | Score: {row['Opportunità_Score']}</p>
                    <p>Prezzo Origine: €{row['Price_Base']:.2f} | Prezzo Destinazione: €{row['Price_Comp']:.2f}</p>
                    <p>Costo Acquisto: €{row['Acquisto_Netto']:.2f} | Profitto: €{row['Profitto_Arbitraggio']:.2f} ({row['Profitto_Percentuale']:.1f}%)</p>
                    <p>ROI: {row['ROI_Arbitraggio']:.1f}% | <a href="{row['Link_Origine']}" target="_blank">🔗 Origine</a> | <a href="{row['Link_Destinazione']}" target="_blank">🔗 Destinazione</a></p>
                </div>
                """, unsafe_allow_html=True)
        
        # Category distribution
        if "Categories: Root (base)" in opportunities.columns:
            st.markdown('<h3 class="sub-header">Distribuzione per Categoria</h3>', unsafe_allow_html=True)
            
            cat_counts = opportunities["Categories: Root (base)"].value_counts().reset_index()
            cat_counts.columns = ["Categoria", "Conteggio"]
            cat_counts = cat_counts.head(10)  # Top 10 categories
            
            fig_cat = px.bar(
                cat_counts, 
                x="Conteggio", 
                y="Categoria",
                orientation='h',
                title="Top 10 Categorie",
                color="Conteggio",
                color_continuous_scale=px.colors.sequential.Viridis
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        
    # DETAILED TABLE TAB
    with tabs[1]:
        st.markdown('<h2 class="sub-header">Tabella Dettagliata</h2>', unsafe_allow_html=True)
        
        # Filter options
        with st.expander("Filtri"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_origin = st.multiselect(
                    "Filtra per Mercato di Origine",
                    options=opportunities["Mercato_Origine"].unique(),
                    default=opportunities["Mercato_Origine"].unique()
                )
            
            with col2:
                filter_dest = st.multiselect(
                    "Filtra per Mercato di Destinazione",
                    options=opportunities["Mercato_Destinazione"].unique(),
                    default=opportunities["Mercato_Destinazione"].unique()
                )
                
            with col3:
                min_profit = st.number_input(
                    "Profitto Minimo (€)",
                    min_value=0.0,
                    max_value=float(opportunities["Profitto_Arbitraggio"].max()),
                    value=min_margin_euro
                )
        
        # Apply filters
        filtered_opps = opportunities[
            (opportunities["Mercato_Origine"].isin(filter_origin)) &
            (opportunities["Mercato_Destinazione"].isin(filter_dest)) &
            (opportunities["Profitto_Arbitraggio"] >= min_profit)
        ]
        
        # Define columns to display
        display_columns = [
            "ASIN", "Title (base)", "Mercato_Origine", "Mercato_Destinazione",
            "Price_Base", "Price_Comp", "Acquisto_Netto",
            "Total_Fees_Confronto", "Profitto_Arbitraggio", "Profitto_Percentuale",
            "ROI_Arbitraggio", "Opportunità_Score"
        ]
        
        # Check if Category column exists
        if "Categories: Root (base)" in filtered_opps.columns:
            display_columns.insert(2, "Categories: Root (base)")
        
        # Create a copy for display
        df_display = filtered_opps[display_columns].copy()
        
        # Format the DataFrame for display
        for col in ["Price_Base", "Price_Comp", "Acquisto_Netto", "Total_Fees_Confronto", "Profitto_Arbitraggio"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"€{x:.2f}" if not pd.isna(x) else "")
                
        for col in ["Profitto_Percentuale", "ROI_Arbitraggio"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"{x:.1f}%" if not pd.isna(x) else "")
        
        # Add buttons to each row for "Add to Cart"
        if not filtered_opps.empty:
            st.write("Seleziona le opportunità da aggiungere al carrello:")
            for idx, row in filtered_opps.iterrows():
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(f"**{row['ASIN']}** - {row['Title (base)'][:80]}... | Profitto: €{row['Profitto_Arbitraggio']:.2f}")
                with col2:
                    if st.button(f"➕ Aggiungi", key=f"add_{idx}"):
                        add_to_cart(
                            row['ASIN'], 
                            row['Title (base)'], 
                            row['Profitto_Arbitraggio'],
                            row['Mercato_Origine'],
                            row['Mercato_Destinazione'],
                            row['Price_Base'],
                            row['Price_Comp']
                        )
            
            # Display the table
            st.write("#### Elenco completo delle opportunità")
            st.dataframe(df_display)
        else:
            st.warning("Nessuna opportunità trovata con i filtri selezionati.")
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = filtered_opps.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="📥 Scarica CSV",
                data=csv_data,
                file_name="amazon_arbitrage_opportunities.csv",
                mime="text/csv"
            )
            
        with col2:
            # Excel export with formatting
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                filtered_opps.to_excel(writer, sheet_name="Opportunità", index=False)
                workbook = writer.book
                worksheet = writer.sheets["Opportunità"]
                
                # Add formats
                money_fmt = workbook.add_format({"num_format": "€#,##0.00"})
                percent_fmt = workbook.add_format({"num_format": "0.0%"})
                
                # Apply formats to columns
                for col_num, col_name in enumerate(filtered_opps.columns):
                    if "Price" in col_name or "Acquisto" in col_name or "Profitto" in col_name and "Percentuale" not in col_name:
                        worksheet.set_column(col_num, col_num, 12, money_fmt)
                    elif "Percentuale" in col_name or "ROI" in col_name:
                        worksheet.set_column(col_num, col_num, 12, percent_fmt)
            
            buffer.seek(0)
            st.download_button(
                label="📥 Scarica Excel",
                data=buffer,
                file_name="amazon_arbitrage_opportunities.xlsx",
                mime="application/vnd.ms-excel"
            )
    
    # CHARTS TAB
    with tabs[2]:
        st.markdown('<h2 class="sub-header">Grafici e Analisi</h2>', unsafe_allow_html=True)
        
        chart_type = st.radio(
            "Seleziona tipo di grafico",
            ["Distribuzione Profitti", "Confronto Mercati", "Relazione Prezzo-Profitto", "ROI per Categoria"],
            horizontal=True
        )
        
        if chart_type == "Distribuzione Profitti":
            # Histogram of profits
            fig = px.histogram(
                opportunities,
                x="Profitto_Arbitraggio",
                nbins=20,
                title="Distribuzione dei Profitti",
                labels={"Profitto_Arbitraggio": "Profitto (€)"},
                color_discrete_sequence=["#FF9900"]
            )
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, use_container_width=True)
            
            # Box plot by market pair
            opportunities["Market_Pair"] = opportunities["Mercato_Origine"] + " → " + opportunities["Mercato_Destinazione"]
            fig2 = px.box(
                opportunities,
                x="Market_Pair",
                y="Profitto_Arbitraggio",
                title="Distribuzione Profitti per Coppia di Mercati",
                labels={"Profitto_Arbitraggio": "Profitto (€)", "Market_Pair": "Coppia di Mercati"},
                color="Market_Pair"
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        elif chart_type == "Confronto Mercati":
            # Scatter plot comparing markets
            fig = px.scatter(
                opportunities,
                x="Price_Base",
                y="Price_Comp",
                size="Profitto_Arbitraggio",
                color="Profitto_Percentuale",
                hover_name="Title (base)",
                labels={
                    "Price_Base": f"Prezzo {base_market.upper()} (€)",
                    "Price_Comp": "Prezzo Mercato Destinazione (€)",
                    "Profitto_Arbitraggio": "Profitto (€)",
                    "Profitto_Percentuale": "Profitto (%)"
                },
                title="Confronto Prezzi tra Mercati",
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            # Add identity line
            max_price = max(opportunities["Price_Base"].max(), opportunities["Price_Comp"].max())
            fig.add_trace(
                go.Scatter(
                    x=[0, max_price],
                    y=[0, max_price],
                    mode="lines",
                    line=dict(color="red", dash="dash"),
                    name="Prezzo Uguale"
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Bar chart comparing average profits by market pair
            market_profit_avg = opportunities.groupby("Market_Pair")["Profitto_Arbitraggio"].mean().reset_index()
            market_profit_avg = market_profit_avg.sort_values("Profitto_Arbitraggio", ascending=False)
            
            fig2 = px.bar(
                market_profit_avg,
                x="Market_Pair",
                y="Profitto_Arbitraggio",
                title="Profitto Medio per Coppia di Mercati",
                labels={"Profitto_Arbitraggio": "Profitto Medio (€)", "Market_Pair": "Coppia di Mercati"},
                color="Profitto_Arbitraggio",
                color_continuous_scale=px.colors.sequential.Oranges
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        elif chart_type == "Relazione Prezzo-Profitto":
            # Scatter plot showing relationship between price and profit
            fig = px.scatter(
                opportunities,
                x="Price_Base",
                y="Profitto_Arbitraggio",
                size="Differenza_Percentuale",
                color="ROI_Arbitraggio",
                hover_name="Title (base)",
                hover_data=["ASIN", "Mercato_Origine", "Mercato_Destinazione"],
                labels={
                    "Price_Base": "Prezzo di Acquisto (€)",
                    "Profitto_Arbitraggio": "Profitto (€)",
                    "Differenza_Percentuale": "Differenza di Prezzo (%)",
                    "ROI_Arbitraggio": "ROI (%)"
                },
                title="Relazione tra Prezzo di Acquisto e Profitto",
                color_continuous_scale=px.colors.sequential.Plasma
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Line chart showing profit trend by price range
            price_bins = pd.cut(opportunities["Price_Base"], bins=10)
            price_profit = opportunities.groupby(price_bins)[["Profitto_Arbitraggio", "ROI_Arbitraggio"]].mean().reset_index()
            price_profit["Price_Range"] = price_profit["Price_Base"].astype(str)
            
            fig2 = px.line(
                price_profit,
                x="Price_Range",
                y=["Profitto_Arbitraggio", "ROI_Arbitraggio"],
                title="Trend di Profitto e ROI per Fascia di Prezzo",
                labels={
                    "Price_Range": "Fascia di Prezzo",
                    "value": "Valore",
                    "variable": "Metrica"
                }
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        elif chart_type == "ROI per Categoria":
            if "Categories: Root (base)" in opportunities.columns:
                # Get top categories
                top_cats = opportunities["Categories: Root (base)"].value_counts().head(10).index.tolist()
                cat_data = opportunities[opportunities["Categories: Root (base)"].isin(top_cats)]
                
                fig = px.box(
                    cat_data,
                    x="Categories: Root (base)",
                    y="ROI_Arbitraggio",
                    color="Categories: Root (base)",
                    title="ROI per Categoria (Top 10)",
                    labels={
                        "Categories: Root (base)": "Categoria",
                        "ROI_Arbitraggio": "ROI (%)"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Heatmap of Category by Market Pair
                if len(cat_data) > 10:  # Only show if we have enough data
                    pivot = pd.pivot_table(
                        cat_data,
                        values="Profitto_Arbitraggio",
                        index="Categories: Root (base)",
                        columns="Market_Pair",
                        aggfunc="mean"
                    ).fillna(0)
                    
                    fig2 = px.imshow(
                        pivot,
                        title="Profitto Medio per Categoria e Coppia di Mercati",
                        labels=dict(x="Coppia di Mercati", y="Categoria", color="Profitto (€)"),
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Dati di categoria non disponibili nei file caricati.")
    
    # PRODUCT ANALYSIS TAB
    with tabs[3]:
        st.markdown('<h2 class="sub-header">Analisi Prodotto</h2>', unsafe_allow_html=True)
        
        # Product selector
        selected_asin = st.selectbox(
            "Seleziona un ASIN da analizzare",
            options=opportunities["ASIN"].unique(),
            format_func=lambda asin: f"{asin} - {opportunities[opportunities['ASIN'] == asin]['Title (base)'].iloc[0][:50]}..."
        )
        
        # Get all data for this ASIN
        asin_data = opportunities[opportunities["ASIN"] == selected_asin]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Product details card
            product_title = asin_data["Title (base)"].iloc[0]
            category = asin_data.get("Categories: Root (base)", pd.Series(["N/D"])).iloc[0]
            source_market = asin_data["Locale (base)"].iloc[0]
            
            st.markdown(f"""
            <div class="card">
                <h3>{product_title}</h3>
                <p><strong>ASIN:</strong> {selected_asin}</p>
                <p><strong>Categoria:</strong> {category}</p>
                <p><strong>Mercato di Origine:</strong> {get_market_flag(source_market)} {source_market.upper()}</p>
                <p><strong>Prezzo di Acquisto:</strong> €{asin_data["Price_Base"].iloc[0]:.2f}</p>
                <p><strong>Prezzo di Acquisto Netto:</strong> €{asin_data["Acquisto_Netto"].iloc[0]:.2f}</p>
                <p><a href="https://www.{MARKETS[source_market]['domain']}/dp/{selected_asin}" target="_blank">🔍 Visualizza su Amazon {source_market.upper()}</a></p>
            </div>
            """, unsafe_allow_html=True)
            
            # Profit calculator
            st.markdown('<h4>Calcolo Profitto per Unità</h4>', unsafe_allow_html=True)
            
            custom_sell_price = st.number_input(
                "Prezzo di Vendita (€)",
                min_value=float(asin_data["Acquisto_Netto"].min()),
                value=float(asin_data["Price_Comp"].mean()),
                step=0.01
            )
            
            custom_market = st.selectbox(
                "Mercato di Vendita",
                options=list(VAT_RATES.keys()),
                format_func=lambda x: f"{get_market_flag(x)} {x.upper()}",
                index=list(VAT_RATES.keys()).index(asin_data["Locale (comp)"].iloc[0])
            )
            
            # Calculate custom profit
            vat_rate = VAT_RATES.get(custom_market, 0.22)
            net_price = custom_sell_price / (1 + vat_rate)
            
            # Get fees
            category_name = asin_data.get("Categories: Root (base)", pd.Series(["Other"])).iloc[0]
            fees = calc_fees(category_name, custom_sell_price, include_fixed_fee)
            fba_fee = 3.0 if include_fba_fee else 0  # Simplified estimate
            
            total_costs = fees["total_fees"] + shipping_cost_rev + fba_fee
            purchase_net = asin_data["Acquisto_Netto"].iloc[0]
            
            profit = net_price - total_costs - purchase_net
            profit_pct = (profit / custom_sell_price) * 100
            roi = (profit / purchase_net) * 100
            
            # Display profit calculation
            st.markdown(f"""
            <div class="card">
                <h4>Calcolo della Redditività</h4>
                <table style="width:100%">
                    <tr>
                        <td>Prezzo di Vendita</td>
                        <td style="text-align:right">€{custom_sell_price:.2f}</td>
                    </tr>
                    <tr>
                        <td>- IVA ({vat_rate*100:.0f}%)</td>
                        <td style="text-align:right">€{(custom_sell_price - net_price):.2f}</td>
                    </tr>
                    <tr>
                        <td>= Prezzo Netto</td>
                        <td style="text-align:right">€{net_price:.2f}</td>
                    </tr>
                    <tr>
                        <td>- Commissione Amazon</td>
                        <td style="text-align:right">€{fees["referral_fee"]:.2f}</td>
                    </tr>
                    <tr>
                        <td>- Tassa Servizi Digitali</td>
                        <td style="text-align:right">€{fees["digital_tax"]:.2f}</td>
                    </tr>
                    <tr>
                        <td>- Commissione FBA</td>
                        <td style="text-align:right">€{fba_fee:.2f}</td>
                    </tr>
                    <tr>
                        <td>- Spedizione</td>
                        <td style="text-align:right">€{shipping_cost_rev:.2f}</td>
                    </tr>
                    <tr>
                        <td>- Costo Acquisto</td>
                        <td style="text-align:right">€{purchase_net:.2f}</td>
                    </tr>
                    <tr style="font-weight:bold">
                        <td>= Profitto Netto</td>
                        <td style="text-align:right">€{profit:.2f}</td>
                    </tr>
                    <tr>
                        <td>Profitto Percentuale</td>
                        <td style="text-align:right">{profit_pct:.1f}%</td>
                    </tr>
                    <tr>
                        <td>ROI</td>
                        <td style="text-align:right">{roi:.1f}%</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Market comparison
            st.markdown('<h4>Confronto tra Mercati</h4>', unsafe_allow_html=True)
            
            # Create a comparison table for all destination markets
            market_data = []
            
            for idx, row in asin_data.iterrows():
                market_data.append({
                    "Mercato": f"{get_market_flag(row['Locale (comp)'])} {row['Locale (comp)'].upper()}",
                    "Prezzo": row["Price_Comp"],
                    "Profitto": row["Profitto_Arbitraggio"],
                    "ROI": row["ROI_Arbitraggio"],
                    "Link": f"https://www.{MARKETS[row['Locale (comp)']]['domain']}/dp/{selected_asin}"
                })
            
            # Sort by profit
            market_data = sorted(market_data, key=lambda x: x["Profitto"], reverse=True)
            
            for market in market_data:
                st.markdown(f"""
                <div class="card">
                    <h4>{market['Mercato']}</h4>
                    <table style="width:100%">
                        <tr>
                            <td>Prezzo di Vendita</td>
                            <td style="text-align:right">€{market['Prezzo']:.2f}</td>
                        </tr>
                        <tr>
                            <td>Profitto Netto</td>
                            <td style="text-align:right">€{market['Profitto']:.2f}</td>
                        </tr>
                        <tr>
                            <td>ROI</td>
                            <td style="text-align:right">{market['ROI']:.1f}%</td>
                        </tr>
                    </table>
                    <p><a href="{market['Link']}" target="_blank">🔍 Visualizza su Amazon</a></p>
                </div>
                """, unsafe_allow_html=True)
            
            # Price breakdown chart
            st.markdown('<h4>Breakdown dei Costi</h4>', unsafe_allow_html=True)
            
            best_market = market_data[0]
            best_market_locale = best_market["Mercato"].split()[-1].lower()
            
            # Prepare data for waterfall chart
            best_row = asin_data[asin_data["Locale (comp)"] == best_market_locale].iloc[0]
            
            net_sell_price = best_row["Price_Comp"] / (1 + VAT_RATES.get(best_market_locale, 0.22))
            vat_amount = best_row["Price_Comp"] - net_sell_price
            
            waterfall_data = [
                {"x": "Prezzo di Vendita", "y": best_row["Price_Comp"], "type": "total"},
                {"x": "IVA", "y": -vat_amount, "type": "negative"},
                {"x": "Commissione Amazon", "y": -best_row["Referral_Fee_Confronto"], "type": "negative"},
                {"x": "Tassa Digitale", "y": -best_row["Digital_Tax_Confronto"], "type": "negative"},
                {"x": "FBA", "y": -best_row["FBA_Fee_Confronto"], "type": "negative"},
                {"x": "Spedizione", "y": -shipping_cost_rev, "type": "negative"},
                {"x": "Costo Acquisto", "y": -best_row["Acquisto_Netto"], "type": "negative"},
                {"x": "Profitto Netto", "y": best_row["Profitto_Arbitraggio"], "type": "positive"}
            ]
            
            # Create color mapping
            colors = {
                "total": "#1f77b4",  # blue
                "negative": "#d62728",  # red
                "positive": "#2ca02c"   # green
            }
            
            # Create the waterfall chart
            fig = go.Figure(go.Waterfall(
                x=[item["x"] for item in waterfall_data],
                y=[item["y"] for item in waterfall_data],
                measure=["absolute"] + ["relative"] * 6 + ["total"],
                text=[f"€{abs(item['y']):.2f}" for item in waterfall_data],
                textposition="outside",
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                marker={"color": [colors[item["type"]] for item in waterfall_data]}
            ))
            
            fig.update_layout(
                title=f"Breakdown del Prezzo - {best_market['Mercato']}",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # NOTES TAB
    with tabs[4]:
        st.markdown('<h2 class="sub-header">Note e Suggerimenti</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h4>Come Utilizzare Questa Applicazione</h4>
            <p>Questa applicazione ti aiuta a identificare opportunità di arbitraggio tra i diversi marketplace Amazon europei. Ecco alcuni suggerimenti per ottenere i migliori risultati:</p>
            <ol>
                <li><strong>Seleziona il Mercato di Origine</strong> - Scegli il marketplace dove intendi acquistare i prodotti</li>
                <li><strong>Seleziona i Mercati di Destinazione</strong> - Scegli i marketplace dove intendi rivendere i prodotti</li>
                <li><strong>Carica i File</strong> - Carica i file di inventario scaricati da Amazon Seller Central per ogni mercato</li>
                <li><strong>Imposta i Parametri</strong> - Configura lo sconto per gli acquisti, i costi di spedizione e i margini minimi desiderati</li>
                <li><strong>Avvia l'Analisi</strong> - Clicca su "Calcola Opportunità" per iniziare l'analisi</li>
                <li><strong>Esamina i Risultati</strong> - Utilizza le diverse schede per analizzare i risultati da differenti prospettive</li>
            </ol>
        </div>
        
        <div class="card">
            <h4>Note sul Calcolo dei Profitti</h4>
            <p>L'applicazione calcola il profitto netto considerando:</p>
            <ul>
                <li><strong>Prezzo di Acquisto</strong> - Prezzo netto dopo lo sconto e al netto dell'IVA</li>
                <li><strong>Prezzo di Vendita</strong> - Prezzo di listino sul mercato di destinazione</li>
                <li><strong>Commissioni Amazon</strong> - Calcolate in base alla categoria del prodotto</li>
                <li><strong>Tassa sui Servizi Digitali</strong> - 3% della commissione Amazon</li>
                <li><strong>Fee FBA</strong> - Stima della commissione di fulfillment Amazon</li>
                <li><strong>Costi di Spedizione</strong> - Costi logistici per l'invio del prodotto</li>
            </ul>
            <p>Il profitto è calcolato come: Prezzo Netto - Commissioni - Costi - Prezzo di Acquisto</p>
        </div>
        
        <div class="card">
            <h4>Suggerimenti per l'Arbitraggio</h4>
            <p>Per massimizzare le opportunità di arbitraggio:</p>
            <ul>
                <li>Concentrati sui prodotti con alto ROI anziché solo sul profitto assoluto</li>
                <li>Considera la rotazione del prodotto e la velocità di vendita sul mercato di destinazione</li>
                <li>Verifica la classifica di vendita (BSR) per valutare la popolarità del prodotto</li>
                <li>Controlla regolarmente i prezzi, in quanto possono cambiare rapidamente</li>
                <li>Inizia con piccole quantità per testare il mercato prima di acquisti più grandi</li>
                <li>Considera la stagionalità di certi prodotti nei diversi mercati europei</li>
            </ul>
        </div>
        
        <div class="card">
            <h4>Informazioni sulle Commissioni</h4>
            <p>L'applicazione utilizza i seguenti tassi di commissione standard di Amazon:</p>
            <ul>
                <li>Elettronica: 8%</li>
                <li>Informatica: 7%</li>
                <li>Altre categorie: 15%</li>
            </ul>
            <p>Per una stima più precisa delle commissioni FBA, considera di utilizzare il <a href="https://sellercentral.amazon.it/hz/fba/profitabilitycalculator/index" target="_blank">Calcolatore di Redditività Amazon</a> ufficiale.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show calculation history
        if st.session_state["calculation_history"]:
            st.markdown('<h3 class="sub-header">Cronologia delle Analisi</h3>', unsafe_allow_html=True)
            
            history = st.session_state["calculation_history"]
            
            for i, calc in enumerate(reversed(history)):
                st.markdown(f"""
                <div class="card">
                    <p><strong>Analisi #{len(history)-i}</strong> - {calc["timestamp"].strftime("%d/%m/%Y %H:%M")}</p>
                    <p>Mercato di Origine: {get_market_flag(calc["base_market"])} {calc["base_market"].upper()}</p>
                    <p>Mercati di Destinazione: {", ".join([f"{get_market_flag(m)} {m.upper()}" for m in calc["comparison_markets"]])}</p>
                    <p>Sconto applicato: {calc["discount"]}%</p>
                    <p>Opportunità trovate: {calc["num_opportunities"]}</p>
                </div>
                """, unsafe_allow_html=True)

#################################
# CART SECTION IN SIDEBAR
#################################

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛒 Carrello Opportunità")

# Display cart items if any
if st.session_state["cart_items"]:
    for item in st.session_state["cart_items"]:
        cols = st.sidebar.columns([4, 1])
        with cols[0]:
            st.markdown(f"""
            <div class="cart-item">
                <small>{item["asin"]} - {item["title"][:20]}...</small><br/>
                <small>{item["origin"]} → {item["destination"]}</small><br/>
                <small>Profitto: €{item["profit"]:.2f}</small>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            if st.button("❌", key=f"remove_{item['id']}"):
                remove_from_cart(item['id'])
                st.experimental_rerun()
    
    st.sidebar.markdown(f"**Totale Prodotti:** {len(st.session_state['cart_items'])}")
    total_profit = sum(p["profit"] for p in st.session_state["cart_items"])
    st.sidebar.markdown(f"**Profitto Potenziale:** €{total_profit:.2f}")
    
    if st.sidebar.button("🗑️ Svuota Carrello"):
        st.session_state["cart_items"] = []
        st.experimental_rerun()
        
    # Export cart
    csv_cart = pd.DataFrame(st.session_state["cart_items"]).to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        "📥 Esporta Carrello",
        csv_cart,
        "amazon_arbitrage_cart.csv",
        "text/csv",
        key='download-csv-cart'
    )
else:
    st.sidebar.info("Nessun prodotto selezionato. Usa la tabella dettagliata per aggiungere prodotti al carrello.")

# Footer
st.markdown("""
<div class="footer">
    <p>Amazon Market Analyzer Pro - Versione 2.0</p>
    <p>Sviluppato per analisi di arbitraggio multi-mercato su Amazon</p>
</div>
""", unsafe_allow_html=True)

# If no results yet, show instructions
if not st.session_state["results_available"]:
    st.markdown("""
    <div class="card">
        <h2>Benvenuto in Amazon Market Analyzer Pro</h2>
        <p>Questa applicazione ti aiuta a identificare opportunità di arbitraggio tra i marketplace Amazon europei.</p>
        <p>Per iniziare:</p>
        <ol>
            <li>Seleziona i tuoi mercati di origine e destinazione dalla barra laterale</li>
            <li>Carica i file di inventario per ciascun mercato</li>
            <li>Configura i parametri di analisi come sconto e costi di spedizione</li>
            <li>Clicca su "Calcola Opportunità" per iniziare</li>
        </ol>
        <p>I file devono essere in formato CSV o Excel e contenere almeno le colonne ASIN, Title e il prezzo di riferimento selezionato.</p>
    </div>
    
    <div class="card">
        <h3>Come ottenere i file di inventario</h3>
        <p>Puoi ottenere i file di inventario direttamente da Amazon Seller Central:</p>
        <ol>
            <li>Accedi a Seller Central per ciascun marketplace</li>
            <li>Vai a "Inventario" > "Gestione dell'inventario"</li>
            <li>Clicca su "Preferenze" e assicurati che tutte le colonne necessarie siano visibili</li>
            <li>Clicca su "Scarica" e seleziona il formato desiderato (CSV o Excel)</li>
            <li>Carica i file scaricati nell'applicazione</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# Main execution
if __name__ == "__main__":
    # This will prevent unnecessary reloading in some Streamlit versions
    pass