import streamlit as st
import pandas as pd
import numpy as np
import math

# Set page configuration
st.set_page_config(
    page_title="Amazon Market Analyzer - Multi-Market Arbitrage",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS for better UI (minimal version)
st.markdown("""
<style>
    h1 {
        color: #232F3E;
    }
    .highlight {
        background-color: #FF9900;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        color: white;
        font-weight: 600;
    }
    .success {
        color: #008000;
        font-weight: bold;
    }
    .warning {
        color: #FFA500;
        font-weight: bold;
    }
    .error {
        color: #FF0000;
        font-weight: bold;
    }
    .stButton > button {
        background-color: #FF9900;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🛒 Amazon Market Analyzer")
st.subheader("Arbitraggio Multi-Mercato per Amazon Europa")

# Initialize session state
if 'opportunities' not in st.session_state:
    st.session_state['opportunities'] = None
if 'results_available' not in st.session_state:
    st.session_state['results_available'] = False

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

# Market flags
MARKET_FLAGS = {
    "it": "🇮🇹",
    "de": "🇩🇪",
    "fr": "🇫🇷",
    "es": "🇪🇸",
    "uk": "🇬🇧"
}

# Amazon commission rates by category
COMMISSION_RATES = {
    "Elettronica": 0.08,
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
    "Prodotti per animali domestici": 0.15
}

# Fixed fees
FIXED_FEE_PER_UNIT = 0.99  # €0.99 fixed fee per unit
DIGITAL_TAX_RATE = 0.03  # 3% digital services tax

#################################
# SIDEBAR CONFIGURATION
#################################

with st.sidebar:
    st.header("📊 Configurazione")
    
    # Base market selection
    base_market = st.selectbox(
        "Mercato di Origine (Acquisto)",
        options=["it", "de", "fr", "es", "uk"],
        format_func=lambda x: f"{MARKET_FLAGS[x]} {x.upper()}"
    )
    
    # Comparison markets selection
    comparison_markets = st.multiselect(
        "Mercati di Destinazione (Vendita)",
        options=["it", "de", "fr", "es", "uk"],
        default=["de", "fr", "es"] if base_market != "de" else ["it", "fr", "es"],
        format_func=lambda x: f"{MARKET_FLAGS[x]} {x.upper()}"
    )
    
    # Remove base market from comparison if selected
    if base_market in comparison_markets:
        comparison_markets.remove(base_market)
        st.warning(f"Rimosso {base_market.upper()} dai mercati di confronto.")
    
    # File uploaders
    st.subheader("📤 Caricamento File")
    files_base = st.file_uploader(
        f"Lista di Origine ({MARKET_FLAGS[base_market]} {base_market.upper()})",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    
    # Dynamically create file uploaders for each comparison market
    comparison_files = {}
    for market in comparison_markets:
        comparison_files[market] = st.file_uploader(
            f"Lista per {MARKET_FLAGS[market]} {market.upper()} (Confronto)",
            type=["csv", "xlsx"],
            accept_multiple_files=True
        )
    
    st.markdown("---")
    
    # Price reference settings
    st.subheader("💰 Impostazioni Prezzo")
    
    ref_price_base = st.selectbox(
        "Prezzo di riferimento (Origine)",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )
    
    ref_price_comp = st.selectbox(
        "Prezzo di riferimento (Destinazione)",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )
    
    st.markdown("---")
    
    # Discount settings
    st.subheader("🏷️ Sconti e Costi")
    
    discount_percent = st.number_input(
        "Sconto per gli acquisti (%)",
        min_value=0.0,
        max_value=40.0,
        value=20.0,
        step=0.5
    )
    discount = discount_percent / 100.0
    
    shipping_cost_rev = st.number_input(
        "Costo di Spedizione (€)",
        min_value=0.0,
        value=5.13,
        step=0.1
    )
    
    min_margin_percent = st.number_input(
        "Margine minimo (%)",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=1.0
    )
    
    min_margin_euro = st.number_input(
        "Margine minimo (€)",
        min_value=0.0,
        value=5.0,
        step=1.0
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

def convert_currency(value, from_currency, to_currency, exchange_rate=1.18):
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
    # Find the category in the commission rates table
    for cat_key in COMMISSION_RATES:
        if cat_key.lower() in str(category).lower():
            rate = COMMISSION_RATES[cat_key]
            break
    else:
        # Default commission if category not found
        rate = 0.15
    
    referral = rate * price
    min_referral = 0.30  # Minimum referral fee
    return max(referral, min_referral)

def calc_fba_fee(category, locale):
    """Calculate estimated FBA fee based on category and market"""
    # Simple estimation based on category
    if "elettron" in str(category).lower() or "electronic" in str(category).lower():
        base_fee = 2.70
    elif "inform" in str(category).lower() or "computer" in str(category).lower():
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

def calc_revenue_metrics(row, shipping_cost, market_type, vat_rates):
    """Calculate revenue and profit metrics"""
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
            "Commissione": np.nan,
            "Tassa_Digitale": np.nan,
            "FBA_Fee": np.nan,
            "Costi_Totali": np.nan,
            "Margine_Netto": np.nan,
            "Margine_Percentuale": np.nan
        })
    
    # Calculate net price (minus VAT)
    vat_rate = vat_rates.get(locale, 0.22)
    price_net = price / (1 + vat_rate)
    
    # Calculate Amazon referral fee
    referral_fee = calc_referral_fee(category, price)
    referral_fee = truncate_2dec(referral_fee)
    
    # Digital services tax
    digital_tax = truncate_2dec(DIGITAL_TAX_RATE * referral_fee)
    
    # FBA fee
    fba_fee = calc_fba_fee(category, locale)
    
    # Calculate total costs
    total_costs = referral_fee + digital_tax + shipping_cost + fba_fee + FIXED_FEE_PER_UNIT
    
    # Calculate margins
    purchase_net = row.get("Acquisto_Netto", 0)
    margin_net = price_net - total_costs - purchase_net
    margin_pct = (margin_net / price) * 100 if price > 0 else 0
    
    return pd.Series({
        "Prezzo_Lordo": round(price, 2),
        "Prezzo_Netto": round(price_net, 2),
        "Commissione": round(referral_fee, 2),
        "Tassa_Digitale": round(digital_tax, 2),
        "FBA_Fee": round(fba_fee, 2),
        "Costi_Totali": round(total_costs, 2),
        "Margine_Netto": round(margin_net, 2),
        "Margine_Percentuale": round(margin_pct, 2)
    })

#################################
# DATA PROCESSING EXECUTION
#################################

if avvia:
    with st.spinner("⏳ Analisi in corso..."):
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
                    lambda x: convert_currency(x, "GBP", "EUR") if not pd.isna(x) else np.nan
                )
            
            if market == "uk":
                df_merged["Price_Comp"] = df_merged["Price_Comp"].apply(
                    lambda x: convert_currency(x, "GBP", "EUR") if not pd.isna(x) else np.nan
                )
            
            # Calculate net purchase price with discount
            df_merged["Acquisto_Netto"] = df_merged.apply(
                lambda row: calc_final_purchase_price(row, discount, VAT_RATES), axis=1
            )
            
            # Calculate revenue metrics for base market
            df_revenue_base = df_merged.apply(
                lambda row: calc_revenue_metrics(row, shipping_cost_rev, "base", VAT_RATES), 
                axis=1
            )
            df_revenue_base = df_revenue_base.add_suffix("_Origine")
            
            # Calculate revenue metrics for comparison market
            df_revenue_comp = df_merged.apply(
                lambda row: calc_revenue_metrics(row, shipping_cost_rev, "comp", VAT_RATES), 
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
            
            # Filter for valid opportunities
            valid_opportunities = df_result[
                (df_result["Profitto_Arbitraggio"] >= min_margin_euro) & 
                (df_result["Profitto_Percentuale"] >= min_margin_percent)
            ].copy()
            
            if not valid_opportunities.empty:
                valid_opportunities["Opportunità_Score"] = (
                    valid_opportunities["Profitto_Arbitraggio"] * 0.6 + 
                    valid_opportunities["Profitto_Percentuale"] * 0.4
                ).round(2)
                
                valid_opportunities["Mercato_Origine"] = valid_opportunities["Locale (base)"].apply(
                    lambda x: f"{MARKET_FLAGS[x]} {x.upper()}"
                )
                valid_opportunities["Mercato_Destinazione"] = valid_opportunities["Locale (comp)"].apply(
                    lambda x: f"{MARKET_FLAGS[x]} {x.upper()}"
                )
                
                # Generate Amazon URLs
                valid_opportunities["URL_Origine"] = valid_opportunities.apply(
                    lambda row: f"https://www.amazon.{row['Locale (base)']}/dp/{row['ASIN']}", axis=1
                )
                valid_opportunities["URL_Destinazione"] = valid_opportunities.apply(
                    lambda row: f"https://www.amazon.{row['Locale (comp)']}/dp/{row['ASIN']}", axis=1
                )
                
                all_opportunities.append(valid_opportunities)
        
        # Combine all opportunities
        if all_opportunities:
            final_opportunities = pd.concat(all_opportunities, ignore_index=True)
            final_opportunities = final_opportunities.sort_values(by="Opportunità_Score", ascending=False)
            
            # Store in session state
            st.session_state["opportunities"] = final_opportunities
            st.session_state["results_available"] = True
            
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
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Risultati", "📊 Analisi", "💰 Redditività"])
    
    with tab1:
        # Count opportunities by market
        st.subheader("📊 Riepilogo")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Opportunità Totali", len(opportunities))
        with col2:
            st.metric("Profitto Medio", f"€{opportunities['Profitto_Arbitraggio'].mean():.2f}")
        with col3:
            st.metric("Margine % Medio", f"{opportunities['Profitto_Percentuale'].mean():.2f}%")
        
        # Main results table
        st.subheader("🔍 Migliori Opportunità")
        
        # Select columns to display
        display_cols = [
            "ASIN", "Title (base)", "Mercato_Origine", "Mercato_Destinazione",
            "Price_Base", "Price_Comp", "Differenza_Prezzo", "Acquisto_Netto",
            "Profitto_Arbitraggio", "Profitto_Percentuale", "Opportunità_Score"
        ]
        
        # Add hyperlink formatting
        def make_clickable(asin, market):
            return f'<a href="https://www.amazon.{market}/dp/{asin}" target="_blank">{asin}</a>'
        
        clickable_df = opportunities.copy()
        clickable_df["ASIN"] = clickable_df.apply(
            lambda x: make_clickable(x["ASIN"], x["Locale (comp)"]), axis=1
        )
        
        # Display table
        st.dataframe(
            clickable_df[display_cols].head(50),
            height=500,
            use_container_width=True
        )
        
        # Add download button
        st.download_button(
            label="⬇️ Scarica risultati (CSV)",
            data=opportunities.to_csv(index=False).encode('utf-8'),
            file_name=f"arbitraggio_amazon_{base_market}_to_{'_'.join(comparison_markets)}.csv",
            mime="text/csv",
        )
    
    with tab2:
        st.subheader("📊 Analisi per Mercato")
        
        # Market distribution
        market_counts = opportunities["Locale (comp)"].value_counts().reset_index()
        market_counts.columns = ["Mercato", "Conteggio"]
        
        st.write("Distribuzione delle opportunità per mercato:")
        st.bar_chart(market_counts.set_index("Mercato"))
        
        # Price difference analysis
        st.subheader("💸 Differenza Prezzi")
        st.write("Differenza di prezzo media per mercato:")
        
        price_diff_by_market = opportunities.groupby("Locale (comp)")["Differenza_Prezzo"].mean().reset_index()
        price_diff_by_market.columns = ["Mercato", "Differenza Media (€)"]
        
        st.dataframe(price_diff_by_market)
    
    with tab3:
        st.subheader("💰 Analisi Redditività")
        
        # Top 10 most profitable products
        st.write("Top 10 prodotti per profitto:")
        top_profit = opportunities.sort_values(by="Profitto_Arbitraggio", ascending=False).head(10)
        
        profit_cols = ["ASIN", "Title (base)", "Mercato_Origine", "Mercato_Destinazione", 
                      "Price_Base", "Price_Comp", "Profitto_Arbitraggio", "Profitto_Percentuale"]
        
        st.dataframe(top_profit[profit_cols])
        
        # ROI analysis
        st.subheader("📈 Return on Investment (ROI)")
        
        opportunities["ROI"] = (opportunities["Profitto_Arbitraggio"] / opportunities["Acquisto_Netto"] * 100).round(2)
        
        # Top 10 by ROI
        st.write("Top 10 prodotti per ROI:")
        top_roi = opportunities.sort_values(by="ROI", ascending=False).head(10)
        
        roi_cols = ["ASIN", "Title (base)", "Mercato_Origine", "Mercato_Destinazione", 
                   "Acquisto_Netto", "Profitto_Arbitraggio", "ROI"]
        
        st.dataframe(top_roi[roi_cols])
else:
    # Show instructions if no results available
    st.info("👆 Imposta i parametri e carica i file nella barra laterale, poi clicca su 'Calcola Opportunità' per iniziare l'analisi.")
    
    # Sample instruction card
    st.markdown("""
    ### 🔍 Come utilizzare l'app:
    
    1. **Carica i file** di origine e destinazione nella barra laterale
    2. **Imposta i parametri** di sconto e margine minimo
    3. **Clicca 'Calcola Opportunità'** per avviare l'analisi
    4. **Visualizza i risultati** nelle diverse schede
    
    L'app calcola le opportunità di arbitraggio tra i diversi marketplace Amazon europei, considerando commissioni, IVA, e altri costi.
    """)