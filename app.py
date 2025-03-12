import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from itertools import permutations

# Configurazione della pagina
st.set_page_config(
    page_title="Amazon EU Arbitrage Calculator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF9900;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #232F3E;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #232F3E;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }
    .success-text {
        color: #008000;
        font-weight: bold;
    }
    .warning-text {
        color: #FFA500;
        font-weight: bold;
    }
    .danger-text {
        color: #FF0000;
        font-weight: bold;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #555;
        font-size: 0.8rem;
    }
    .stButton>button {
        background-color: #FF9900;
        color: white;
    }
    .stButton>button:hover {
        background-color: #e88e00;
    }
    .asin-list {
        max-height: 150px;
        overflow-y: auto;
        border: 1px solid #ddd;
        padding: 10px;
        background-color: #f5f5f5;
        border-radius: 5px;
        font-family: monospace;
        color: #333;
    }
    .asin-header {
        background-color: #232F3E;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Titolo principale
st.markdown("<h1 class='main-header'>Amazon European Marketplace Arbitrage Calculator</h1>", unsafe_allow_html=True)

# Inizializzazione delle variabili di stato
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'opportunity_scores' not in st.session_state:
    st.session_state['opportunity_scores'] = None
if 'marketplace_data' not in st.session_state:
    st.session_state['marketplace_data'] = {}
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'all_asins' not in st.session_state:
    st.session_state['all_asins'] = None
if 'all_opportunities' not in st.session_state:
    st.session_state['all_opportunities'] = None

# Inizializzazione degli stati per i widget
if 'italy_price_type' not in st.session_state:
    st.session_state['italy_price_type'] = "Buy Box: Current"
if 'foreign_price_type' not in st.session_state:
    st.session_state['foreign_price_type'] = "Amazon: Current"
if 'sell_price_type' not in st.session_state:
    st.session_state['sell_price_type'] = "Buy Box: Current"
if 'discount_percent' not in st.session_state:
    st.session_state['discount_percent'] = 20.0
if 'shipping_cost_italy' not in st.session_state:
    st.session_state['shipping_cost_italy'] = 5.13
if 'shipping_cost_europe' not in st.session_state:
    st.session_state['shipping_cost_europe'] = 8.50
if 'min_margin_percent' not in st.session_state:
    st.session_state['min_margin_percent'] = 10.0

# Configurazione dei tassi IVA per mercato
IVA_RATES = {
    "it": 0.22,  # Italia
    "de": 0.19,  # Germania
    "fr": 0.20,  # Francia
    "es": 0.21,  # Spagna
    "uk": 0.20,  # Regno Unito
    "nl": 0.21,  # Paesi Bassi
    "pl": 0.23,  # Polonia
    "se": 0.25,  # Svezia
}

# Configurazione delle commissioni Amazon per categoria
COMMISSION_RATES = {
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
    "Informatica": 0.07,
    "Libri": 0.15,
    "Altri prodotti": 0.15,
}

# Funzioni di utilità per il caricamento e l'elaborazione dei dati
def load_data(uploaded_file):
    """
    Carica un file CSV o Excel e lo converte in un DataFrame pandas.
    """
    if not uploaded_file:
        return None
    
    filename = uploaded_file.name.lower()
    
    try:
        if filename.endswith(".xlsx"):
            return pd.read_excel(uploaded_file, dtype=str)
        elif filename.endswith(".csv"):
            try:
                return pd.read_csv(uploaded_file, sep=";", dtype=str)
            except:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, sep=",", dtype=str)
        else:
            st.error(f"Formato file non supportato: {filename}. Usa .csv o .xlsx")
            return None
    except Exception as e:
        st.error(f"Errore nel caricamento del file {filename}: {str(e)}")
        return None

def parse_float(value):
    """
    Converte una stringa in un valore float, gestendo simboli di valuta e formati diversi.
    """
    if pd.isna(value) or not isinstance(value, str):
        return np.nan
    
    # Rimuove simboli di valuta e sostituisce virgole con punti
    clean_value = value.replace("€", "").replace("£", "").replace("$", "").replace(",", ".").strip()
    
    try:
        return float(clean_value)
    except:
        return np.nan

def calc_final_purchase_price(price, locale, discount, iva_rates):
    """
    Calcola il prezzo d'acquisto netto considerando lo sconto e l'IVA.
    Formula differente per mercato italiano rispetto agli altri.
    """
    if pd.isna(price):
        return np.nan
    
    locale = locale.lower()
    iva_rate = iva_rates.get(locale, 0.22)  # Default all'IVA italiana se non trovata
    net_price = price / (1 + iva_rate)
    
    # Logica differente per l'Italia rispetto agli altri paesi
    if locale == "it":
        # Per Italia: lo sconto si applica al prezzo lordo, poi si toglie dal netto
        discount_amount = price * discount
        final_price = net_price - discount_amount
    else:
        # Per altri paesi: lo sconto si applica direttamente al prezzo netto
        final_price = net_price * (1 - discount)
    
    return round(final_price, 2)

# Funzioni per il Revenue Calculator di Amazon
def rev_truncate_2dec(value):
    """
    Tronca un valore a 2 decimali (non arrotonda).
    """
    if value is None or np.isnan(value):
        return np.nan
    return math.floor(value * 100) / 100.0

def rev_calc_referral_fee(category, price):
    """
    Calcola la commissione di referral in base alla categoria e al prezzo.
    """
    rate = COMMISSION_RATES.get(category, 0.15)  # Default 15% se categoria non trovata
    referral = rate * price
    min_referral = 0.30  # Commissione minima 0,30€
    return max(referral, min_referral)

def rev_calc_fees(category, price):
    """
    Calcola tutte le commissioni per un prodotto.
    """
    referral_raw = rev_calc_referral_fee(category, price)
    referral_fee = rev_truncate_2dec(referral_raw)
    
    # Imposta sui servizi digitali (3% della commissione di referral)
    digital_tax_raw = 0.03 * referral_fee
    digital_tax = rev_truncate_2dec(digital_tax_raw)
    
    # Commissione totale
    total_fees = rev_truncate_2dec(referral_fee + digital_tax)
    
    return {
        "referral_fee": referral_fee,
        "digital_tax": digital_tax,
        "total_fees": total_fees
    }

def rev_calc_revenue_metrics(sell_price, purchase_price, category, locale, shipping_cost_rev, iva_rates):
    """
    Calcola le metriche di redditività per un prodotto.
    """
    # Se il prezzo non è disponibile, restituisce valori nulli
    if pd.isna(sell_price) or pd.isna(purchase_price):
        return {
            "Margine_Netto": np.nan,
            "Margine_Percentuale": np.nan,
            "Commissioni": np.nan,
            "Prezzo_Netto": np.nan
        }
    
    # Ottiene l'aliquota IVA per la località
    iva_rate = iva_rates.get(locale.lower(), 0.22)
    
    # Calcola il prezzo al netto dell'IVA
    price_net = sell_price / (1 + iva_rate)
    
    # Calcola le commissioni
    fees = rev_calc_fees(category, sell_price)
    total_fees = fees["total_fees"]
    
    # Calcola i costi totali (commissioni + spedizione)
    total_costs = total_fees + shipping_cost_rev
    
    # Calcola il margine netto
    margin_net = price_net - total_costs - purchase_price
    
    # Calcola il margine in percentuale
    margin_pct = (margin_net / sell_price) * 100 if sell_price != 0 else np.nan
    
    return {
        "Margine_Netto": round(margin_net, 2),
        "Margine_Percentuale": round(margin_pct, 2),
        "Commissioni": round(total_fees, 2),
        "Prezzo_Netto": round(price_net, 2)
    }

def calculate_opportunity_score(margin_source, margin_target, margin_pct_target):
    """
    Calcola un punteggio di opportunità tra due mercati.
    """
    try:
        if pd.isna(margin_source) or pd.isna(margin_target):
            return 0
        
        # Calcola la differenza di margine tra i mercati
        margin_diff = margin_target - margin_source
        
        # Calcola il punteggio di opportunità
        # Formula: Differenza di margine * Margine % nel mercato target
        opportunity_score = margin_diff * margin_pct_target / 100
        
        return round(opportunity_score, 2)
    except:
        return 0

def extract_asins(df):
    """
    Estrae e formatta gli ASIN da un DataFrame.
    """
    if df is None or "ASIN" not in df.columns:
        return []
    
    return df["ASIN"].dropna().unique().tolist()

def detect_locale_from_filename(filename):
    """
    Rileva il marketplace dal nome del file.
    """
    locale_markers = {
        "it": ["it", "ita", "italy", "italia"],
        "de": ["de", "deu", "germany", "germania"],
        "fr": ["fr", "fra", "france", "francia"],
        "es": ["es", "esp", "spain", "spagna"],
        "uk": ["uk", "gbr", "united kingdom", "regno unito"],
        "nl": ["nl", "nld", "netherlands", "paesi bassi"],
        "pl": ["pl", "pol", "poland", "polonia"],
        "se": ["se", "swe", "sweden", "svezia"]
    }
    
    filename_lower = filename.lower()
    
    for locale, markers in locale_markers.items():
        for marker in markers:
            if marker in filename_lower:
                return locale
    
    # Default a "it" se non rilevato
    return "it"

# Layout sidebar per i parametri di input
with st.sidebar:
    st.markdown("<h2 style='color:#FF9900'>Impostazioni</h2>", unsafe_allow_html=True)
    
    with st.expander("Caricamento File", expanded=True):
        uploaded_files = st.file_uploader(
            "Carica file dei marketplace (CSV/Excel)",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
            help="Carica uno o più file CSV/Excel contenenti dati di prodotti Amazon. Il sistema cercherà di rilevare automaticamente il marketplace dal nome del file."
        )
    
    if uploaded_files:
        analyze_files_btn = st.button("Analizza i file caricati", use_container_width=True)
        
        if analyze_files_btn:
            with st.spinner("Analisi dei file in corso..."):
                marketplace_data = {}
                all_asins = set()
                
                for file in uploaded_files:
                    df = load_data(file)
                    if df is not None and not df.empty:
                        # Rileva il marketplace dal nome del file
                        detected_locale = detect_locale_from_filename(file.name)
                        
                        # Se c'è già una colonna Locale, usa quella
                        if "Locale" in df.columns:
                            # Verifica se tutti i valori sono uguali
                            unique_locales = df["Locale"].dropna().unique()
                            if len(unique_locales) == 1:
                                locale = unique_locales[0].lower()
                            else:
                                locale = detected_locale
                        else:
                            locale = detected_locale
                        
                        # Aggiunge la colonna Locale se non esiste
                        if "Locale" not in df.columns:
                            df["Locale"] = locale
                        
                        # Estrai gli ASIN e aggiungi al set principale
                        file_asins = extract_asins(df)
                        all_asins.update(file_asins)
                        
                        # Prepara i dati del marketplace
                        if locale not in marketplace_data:
                            marketplace_data[locale] = df
                        else:
                            # Concatena con i dati esistenti per quel marketplace
                            marketplace_data[locale] = pd.concat([marketplace_data[locale], df], ignore_index=True)
                
                # Salva i dati nei session_state
                st.session_state['marketplace_data'] = marketplace_data
                st.session_state['all_asins'] = list(all_asins)
                
                # Mostra un riepilogo
                st.success(f"Caricati dati per {len(marketplace_data)} marketplace con un totale di {len(all_asins)} ASIN unici.")
                
                for locale, df in marketplace_data.items():
                    st.info(f"Marketplace {locale.upper()}: {len(df)} prodotti")
    
    with st.expander("Configurazione Prezzi", expanded=True):
        # Per acquisti dall'Italia
        st.subheader("Prezzi di acquisto")
        italy_price_type = st.selectbox(
            "Prezzo di riferimento per acquisti dall'Italia",
            ["Buy Box: Current", "Amazon: Current"],
            key="italy_price_type"
        )
        
        # Per acquisti dall'estero
        foreign_price_type = st.selectbox(
            "Prezzo di riferimento per acquisti dall'estero",
            ["Amazon: Current"],
            key="foreign_price_type"
        )
        
        # Per vendita (uguale per tutti)
        sell_price_type = st.selectbox(
            "Prezzo di riferimento per vendita",
            ["Buy Box: Current", "Amazon: Current", "New: Current"],
            key="sell_price_type"
        )
    
    with st.expander("Parametri Finanziari", expanded=True):
        discount_percent = st.slider(
            "Sconto per gli acquisti (%)",
            min_value=0.0,
            max_value=50.0,
            value=20.0,
            step=0.5,
            key="discount_percent"
        )
        discount = discount_percent / 100.0
        
        col1, col2 = st.columns(2)
        with col1:
            shipping_cost_italy = st.number_input(
                "Costo di Spedizione Italia (€)",
                min_value=0.0,
                value=5.13,
                step=0.1,
                key="shipping_cost_italy"
            )
        with col2:
            shipping_cost_europe = st.number_input(
                "Costo di Spedizione Europa (€)",
                min_value=0.0,
                value=8.50,
                step=0.1,
                key="shipping_cost_europe"
            )
        
        min_margin_percent = st.slider(
            "Margine minimo (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            key="min_margin_percent"
        )
    
    calcola_btn = st.button("Calcola Opportunità di Arbitraggio", use_container_width=True)

# Mostra ASIN estratti se disponibili
if 'all_asins' in st.session_state and st.session_state['all_asins']:
    with st.expander("📑 ASIN Estratti", expanded=False):
        st.markdown(f"""
        <div class="asin-header">
            <strong>{len(st.session_state['all_asins'])} ASIN unici estratti</strong>
        </div>
        """, unsafe_allow_html=True)
        
        asins = st.session_state['all_asins']
        
        # Opzioni di formattazione
        format_options = st.radio(
            "Formato visualizzazione:",
            ["Uno per riga", "Separati da virgola", "Separati da tab"],
            horizontal=True
        )
        
        if format_options == "Uno per riga":
            formatted_asins = "\n".join(asins)
        elif format_options == "Separati da virgola":
            formatted_asins = ", ".join(asins)
        elif format_options == "Separati da tab":
            formatted_asins = "\t".join(asins)
        
        # Mostra gli ASIN nel formato scelto in un box più piccolo
        st.markdown(f"""
        <div class="asin-list">
            <pre style="margin: 0; white-space: pre-wrap;">{formatted_asins}</pre>
        </div>
        """, unsafe_allow_html=True)
        
        # Pulsanti per copiare e scaricare
        col1, col2 = st.columns(2)
        
        # Aggiungere JavaScript per copiare negli appunti
        js_code = f"""
        <script>
        function copyToClipboard() {{
            const text = `{formatted_asins}`;
            navigator.clipboard.writeText(text).then(() => {{
                // Feedback visivo
                const button = document.getElementById('copy-button');
                button.textContent = '✓ Copiato!';
                setTimeout(() => {{
                    button.textContent = '📋 Copia negli appunti';
                }}, 2000);
            }});
        }}
        </script>
        <button id="copy-button" onclick="copyToClipboard()" style="background-color: #FF9900; color: white; border: none; border-radius: 4px; padding: 0.5rem 1rem; cursor: pointer; width: 100%;">
            📋 Copia negli appunti
        </button>
        """
        
        with col1:
            st.components.v1.html(js_code, height=50)
            
        with col2:
            st.download_button(
                label="💾 Scarica ASIN",
                data=formatted_asins,
                file_name=f"asin_list_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                key="download_asins"
            )

# Funzione principale per l'elaborazione dei dati
def process_arbitrage_opportunities():
    """
    Elabora tutte le possibili opportunità di arbitraggio tra i diversi marketplace.
    """
    if not st.session_state['marketplace_data'] or len(st.session_state['marketplace_data']) < 2:
        st.warning("Carica dati per almeno due marketplace diversi per calcolare le opportunità di arbitraggio.")
        return None
    
    # Lista di opportunità
    all_opportunities = []
    
    # Itera su tutte le coppie di marketplace (source, target)
    for source_locale, source_df in st.session_state['marketplace_data'].items():
        for target_locale, target_df in st.session_state['marketplace_data'].items():
            # Salta se source e target sono lo stesso marketplace
            if source_locale == target_locale:
                continue
            
            # Determina il tipo di prezzo corretto per l'acquisto in base al locale
            if source_locale.lower() == "it":
                source_price_col = italy_price_type
            else:
                source_price_col = foreign_price_type
                
            # Tipo di prezzo per la vendita è sempre lo stesso
            target_price_col = sell_price_type
            
            # Crea un DataFrame con i prodotti presenti in entrambi i marketplace
            # Prima standardizziamo i dati
            source_df_clean = source_df.copy()
            target_df_clean = target_df.copy()
            
            # Assicurati che entrambi abbiano la colonna ASIN
            if "ASIN" not in source_df_clean.columns or "ASIN" not in target_df_clean.columns:
                continue
                
            # Prepara i prezzi
            if source_price_col in source_df_clean.columns:
                source_df_clean["Price"] = source_df_clean[source_price_col].apply(parse_float)
            else:
                continue
                
            if target_price_col in target_df_clean.columns:
                target_df_clean["Price"] = target_df_clean[target_price_col].apply(parse_float)
            else:
                continue
            
            # Merge sui prodotti comuni
            merged_df = pd.merge(
                source_df_clean[["ASIN", "Title", "Price", "Locale", "Categories: Root"]],
                target_df_clean[["ASIN", "Price", "Locale"]],
                on="ASIN",
                suffixes=("_source", "_target")
            )
            
            if merged_df.empty:
                continue
            
            # Calcola i prezzi di acquisto netti
            merged_df["Buy_Price"] = merged_df.apply(
                lambda row: calc_final_purchase_price(
                    row["Price_source"], 
                    row["Locale_source"], 
                    discount, 
                    IVA_RATES
                ), 
                axis=1
            )
            
            # Calcola le metriche per ogni prodotto
            opportunities = []
            
            for _, row in merged_df.iterrows():
                category = row.get("Categories: Root", "Altri prodotti")
                
                # Determina il costo di spedizione in base al marketplace
                shipping_cost = shipping_cost_italy if row["Locale_target"].lower() == "it" else shipping_cost_europe
                
                # Calcola il margine di tenere il prodotto nello stesso marketplace (source)
                source_metrics = rev_calc_revenue_metrics(
                    row["Price_source"],
                    row["Buy_Price"],
                    category,
                    row["Locale_source"],
                    shipping_cost,
                    IVA_RATES
                )
                
                # Calcola il margine di vendere il prodotto nel marketplace target
                target_metrics = rev_calc_revenue_metrics(
                    row["Price_target"],
                    row["Buy_Price"],
                    category,
                    row["Locale_target"],
                    shipping_cost,
                    IVA_RATES
                )
                
                # Calcola l'opportunity score
                opportunity_score = calculate_opportunity_score(
                    source_metrics["Margine_Netto"],
                    target_metrics["Margine_Netto"],
                    target_metrics["Margine_Percentuale"]
                )
                
                # Crea un dict con i dati dell'opportunità
                opportunity = {
                    "ASIN": row["ASIN"],
                    "Title": row["Title"],
                    "Source_Marketplace": row["Locale_source"].upper(),
                    "Target_Marketplace": row["Locale_target"].upper(),
                    "Source_Price": row["Price_source"],
                    "Source_Price_Type": source_price_col,
                    "Target_Price": row["Price_target"],
                    "Target_Price_Type": target_price_col,
                    "Buy_Price": row["Buy_Price"],
                    "Category": category,
                    "Source_Margin": source_metrics["Margine_Netto"],
                    "Source_Margin_Pct": source_metrics["Margine_Percentuale"],
                    "Target_Margin": target_metrics["Margine_Netto"],
                    "Target_Margin_Pct": target_metrics["Margine_Percentuale"],
                    "Opportunity_Score": opportunity_score,
                    "Shipping_Cost": shipping_cost
                }
                
                opportunities.append(opportunity)
            
            # Aggiungi le opportunità alla lista principale
            all_opportunities.extend(opportunities)
    
    # Converti in DataFrame
    if all_opportunities:
        df_opportunities = pd.DataFrame(all_opportunities)
        
        # Filtra per margine minimo
        df_opportunities = df_opportunities[df_opportunities["Target_Margin_Pct"] >= min_margin_percent]
        
        # Ordina per opportunity score
        df_opportunities.sort_values("Opportunity_Score", ascending=False, inplace=True)
        
        return df_opportunities
    else:
        return None

# Esegui l'elaborazione quando il pulsante viene premuto
if calcola_btn:
    with st.spinner("Calcolo delle opportunità in corso..."):
        df_opportunities = process_arbitrage_opportunities()
        if df_opportunities is not None and not df_opportunities.empty:
            st.session_state['all_opportunities'] = df_opportunities
            st.session_state['last_update'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            st.success(f"Trovate {len(df_opportunities)} opportunità di arbitraggio!")
        else:
            st.warning("Nessuna opportunità di arbitraggio trovata con i criteri specificati.")

# Visualizza i risultati
if 'all_opportunities' in st.session_state and st.session_state['all_opportunities'] is not None:
    df_opps = st.session_state['all_opportunities']
    
    st.markdown("<h2 class='sub-header'>Opportunità di Arbitraggio</h2>", unsafe_allow_html=True)
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Opportunità Trovate", len(df_opps))
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        if not df_opps.empty:
            top_margin = df_opps["Target_Margin_Pct"].max()
            top_margin_str = f"{top_margin:.2f}%" if not pd.isna(top_margin) else "N/A"
        else:
            top_margin_str = "N/A"
        st.metric("Miglior Margine", top_margin_str)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        if not df_opps.empty:
            marketplace_pairs = df_opps[["Source_Marketplace", "Target_Marketplace"]].value_counts().count()
        else:
            marketplace_pairs = 0
        st.metric("Combinazioni Marketplace", marketplace_pairs)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Ultimo Aggiornamento", st.session_state['last_update'])
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tabs per i diversi tipi di visualizzazione
    tab1, tab2, tab3 = st.tabs(["🔝 Migliori Opportunità", "📊 Analisi Grafica", "📋 Tutti i Risultati"])
    
    with tab1:
        if not df_opps.empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Filtri per marketplace source e target
            col1, col2 = st.columns(2)
            with col1:
                source_markets = sorted(df_opps["Source_Marketplace"].unique())
                selected_sources = st.multiselect(
                    "Filtra per Marketplace di Origine",
                    options=source_markets,
                    default=source_markets
                )
            
            with col2:
                target_markets = sorted(df_opps["Target_Marketplace"].unique())
                selected_targets = st.multiselect(
                    "Filtra per Marketplace di Destinazione",
                    options=target_markets,
                    default=target_markets
                )
            
            # Applica filtri
            filtered_opps = df_opps.copy()
            if selected_sources:
                filtered_opps = filtered_opps[filtered_opps["Source_Marketplace"].isin(selected_sources)]
            if selected_targets:
                filtered_opps = filtered_opps[filtered_opps["Target_Marketplace"].isin(selected_targets)]
            
            # Visualizza le top opportunità
            st.markdown("### Top Prodotti per Opportunità")
            
            top_opportunities = filtered_opps.head(10)
            
            for index, row in top_opportunities.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.markdown(f"**ASIN**: [{row['ASIN']}](https://www.amazon.{row['Target_Marketplace'].lower()}/dp/{row['ASIN']})")
                        st.markdown(f"**Score**: {row['Opportunity_Score']:.2f}")
                    
                    with col2:
                        st.markdown(f"**{row['Title']}**")
                        source_info = f"🛒 Acquista da: {row['Source_Marketplace']} → €{row['Source_Price']:.2f} ({row['Source_Price_Type']}, Acquisto netto: €{row['Buy_Price']:.2f})"
                        target_info = f"💰 Vendi su: {row['Target_Marketplace']} → €{row['Target_Price']:.2f} ({row['Target_Price_Type']}, Margine: {row['Target_Margin_Pct']:.2f}%)"
                        diff_info = f"📈 Differenza margine: €{(row['Target_Margin'] - row['Source_Margin']):.2f}"
                        
                        st.markdown(source_info)
                        st.markdown(target_info)
                        st.markdown(diff_info)
                    
                    st.markdown("---")
            
            # Pulsante per scaricare i risultati
            csv_data = filtered_opps.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="📥 Scarica Opportunità (CSV)",
                data=csv_data,
                file_name=f"amazon_arbitrage_opportunities_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Nessuna opportunità trovata che soddisfi i criteri di margine minimo.")
    
    with tab2:
        if not df_opps.empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Crea grafici informativi
            # 1. Grafico a barre per il numero di opportunità per combinazione di marketplace
            marketplace_counts = df_opps.groupby(["Source_Marketplace", "Target_Marketplace"]).size().reset_index(name="Count")
            marketplace_counts["Market_Pair"] = marketplace_counts["Source_Marketplace"] + " → " + marketplace_counts["Target_Marketplace"]
            
            fig1 = px.bar(
                marketplace_counts.sort_values("Count", ascending=False),
                x="Market_Pair",
                y="Count",
                title="Numero di Opportunità per Combinazione di Marketplace",
                labels={"Market_Pair": "Combinazione Marketplace", "Count": "Numero di Opportunità"},
                color="Count",
                color_continuous_scale="Blues"
            )
            fig1.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig1, use_container_width=True)
            
            # 2. Grafico a dispersione per Prezzo vs Margine
            fig2 = px.scatter(
                df_opps,
                x="Target_Price",
                y="Target_Margin_Pct",
                color="Source_Marketplace",
                hover_name="Title",
                hover_data=["ASIN", "Target_Marketplace", "Opportunity_Score"],
                title="Relazione tra Prezzo di Vendita e Margine",
                labels={"Target_Price": "Prezzo di Vendita (€)", "Target_Margin_Pct": "Margine (%)"},
                size="Opportunity_Score",
                size_max=20
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # 3. Grafico a box per la distribuzione dei margini per marketplace di destinazione
            fig3 = px.box(
                df_opps,
                x="Target_Marketplace",
                y="Target_Margin_Pct",
                color="Target_Marketplace",
                title="Distribuzione dei Margini per Marketplace di Destinazione",
                labels={"Target_Marketplace": "Marketplace di Destinazione", "Target_Margin_Pct": "Margine (%)"}
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Nessun dato disponibile per l'analisi grafica.")
    
    with tab3:
        if not df_opps.empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("### Tutti i Risultati")
            
            # Aggiungi filtri interattivi
            col1, col2, col3 = st.columns(3)
            with col1:
                min_price = st.number_input("Prezzo Min (€)", value=0.0)
            with col2:
                max_price = st.number_input("Prezzo Max (€)", value=1000.0)
            with col3:
                search_asin = st.text_input("Cerca ASIN o Titolo", "")
            
            # Applica filtri
            df_display = df_opps.copy()
            df_display = df_display[df_display["Target_Price"] >= min_price]
            df_display = df_display[df_display["Target_Price"] <= max_price]
            
            if search_asin:
                df_display = df_display[(df_display["ASIN"].str.contains(search_asin, case=False)) | 
                                       (df_display["Title"].str.contains(search_asin, case=False))]
            
            # Mostra l'intero dataframe con colori condizionali
            st.dataframe(
                df_display.style.applymap(
                    lambda x: "color: green" if isinstance(x, (int, float)) and x > 0 else "color: red" if isinstance(x, (int, float)) and x < 0 else "",
                    subset=["Target_Margin", "Source_Margin", "Opportunity_Score"]
                ),
                height=600
            )
            
            # Pulsante per scaricare tutti i risultati
            csv_data_all = df_display.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="📥 Scarica Tutti i Risultati (CSV)",
                data=csv_data_all,
                file_name=f"amazon_arbitrage_full_results_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Nessun dato disponibile.")
else:
    # Pagina iniziale quando non ci sono dati
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("""
    ### 👋 Benvenuto nell'Amazon European Marketplace Arbitrage Calculator!
    
    Questa applicazione ti aiuta a identificare opportunità di arbitraggio tra tutti i marketplace Amazon europei, consentendoti di acquistare prodotti dove costano meno e venderli dove hanno prezzi più alti.
    
    #### Come utilizzare l'app:
    
    1. **Carica i file** nella barra laterale:
       - Carica file CSV/Excel di tutti i marketplace che vuoi analizzare
       - Il sistema identificherà automaticamente il marketplace dal nome del file o dai dati interni
    
    2. **Estrai ASIN** per ulteriori analisi
       - Dopo aver caricato i file, vedrai una lista completa di ASIN che puoi usare con Keepa o altri strumenti
    
    3. **Configura i parametri**:
       - Seleziona i prezzi di riferimento per acquisti da Italia e dall'estero
       - Imposta lo sconto per gli acquisti
       - Definisci i costi di spedizione per Italia ed Europa
       - Stabilisci il margine minimo desiderato
    
    4. **Calcola le opportunità** di arbitraggio tra tutti i possibili marketplace.
    
    #### Cosa rende unica questa app:
    
    - **Analisi multi-direzionale**: Confronta tutte le combinazioni di marketplace, non solo da un mercato base verso altri
    - **Flessibilità nei prezzi**: Usa prezzi di Buy Box per l'Italia e prezzi Amazon per l'estero
    - **Costi di spedizione differenziati**: Calcola i costi in base alla destinazione (Italia o altri paesi UE)
    - **Revenue Calculator preciso**: Calcoli basati sul modello ufficiale Amazon con IVA e commissioni specifiche per paese
    
    #### Tips per massimizzare i risultati:
    
    - Carica file recenti con prezzi aggiornati
    - Assicurati che i file contengano la colonna ASIN e i prezzi nel formato corretto
    - Considera i costi di spedizione internazionale per un calcolo più preciso
    - Filtra per un margine minimo che copra i rischi dell'arbitraggio
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Mostra esempio/guida
    with st.expander("Guida rapida al formato dei file"):
        st.markdown("""
        ### Formato dei file richiesto
        
        I file CSV/Excel devono contenere almeno le seguenti colonne:
        
        - **ASIN**: codice prodotto Amazon (obbligatorio)
        - **Title**: titolo del prodotto
        - **Buy Box: Current**: prezzo attuale nella Buy Box (per acquisti in Italia)
        - **Amazon: Current**: prezzo attuale di Amazon (per acquisti dall'estero)
        - **New: Current**: prezzo attuale del prodotto nuovo (opzionale)
        - **Locale**: codice del marketplace (it, de, fr, es, ecc.) - opzionale, può essere rilevato dal nome file
        - **Categories: Root**: categoria principale del prodotto (opzionale, ma utile per calcoli più precisi)
        
        **Consiglio**: Includi nel nome del file un'indicazione del marketplace (es. "amazon_it.csv", "prodotti_de.xlsx") per facilitare il rilevamento automatico.
        """)
        
        # Mostra esempio di formato file
        example_data = {
            "ASIN": ["B08X6NOCL3", "B07PVCVBN7", "B01N5IB20Q"],
            "Title": ["Cuffie Bluetooth", "SSD 1TB", "Monitor 24 pollici"],
            "Buy Box: Current": ["€59,99", "€89,90", "€129,99"],
            "Amazon: Current": ["€62,99", "€92,90", "€134,99"],
            "New: Current": ["€58,50", "€87,50", "€126,99"],
            "Locale": ["it", "it", "it"],
            "Categories: Root": ["Elettronica", "Informatica", "Informatica"]
        }
        
        example_df = pd.DataFrame(example_data)
        st.dataframe(example_df)

# Aggiungi una sezione FAQ
with st.expander("❓ Domande Frequenti"):
    st.markdown("""
    #### Come funziona il rilevamento del marketplace?
    L'app cerca di rilevare automaticamente il marketplace in due modi:
    1. Cercando un codice paese nel nome del file (it, de, fr, ecc.)
    2. Controllando la colonna "Locale" nel file, se presente
    Se non riesce a rilevare il marketplace, usa "it" (Italia) come default.
    
    #### Perché ci sono prezzi diversi per Italia ed estero?
    Per l'Italia, puoi acquistare sia dai venditori nella Buy Box che direttamente da Amazon. Per gli acquisti dall'estero, è più affidabile comprare solo direttamente da Amazon, quindi l'opzione è limitata a "Amazon: Current".
    
    #### Perché ci sono due costi di spedizione?
    Le spedizioni verso l'Italia e verso altri paesi europei hanno costi diversi. Specificando entrambi i valori, ottieni calcoli di margine più precisi a seconda del marketplace di destinazione.
    
    #### Come vengono calcolate le commissioni Amazon?
    Le commissioni vengono calcolate in base alla categoria del prodotto, con percentuali che vanno dal 7% al 15%. Utilizziamo le stesse formule del Revenue Calculator ufficiale di Amazon, inclusa l'imposta sui servizi digitali del 3%.
    
    #### Come funziona il calcolo dello sconto?
    Per i prodotti su Amazon.it, lo sconto viene applicato al prezzo lordo e poi sottratto dal prezzo netto. Per gli altri marketplace, lo sconto viene applicato direttamente al prezzo netto.
    
    #### Cosa significa "Opportunity Score"?
    È un valore calcolato che combina la differenza di margine tra i mercati e il margine percentuale nel mercato target. Un punteggio più alto indica un'opportunità di arbitraggio più vantaggiosa.
    """)

# Aggiungi una sezione per i calcoli dettagliati
with st.expander("📝 Dettagli sui Calcoli"):
    st.markdown("""
    #### Formula per il prezzo d'acquisto netto (Italia)
    ```
    prezzo_lordo = prezzo_con_iva
    prezzo_netto = prezzo_lordo / (1 + aliquota_iva)
    sconto_importo = prezzo_lordo * percentuale_sconto
    prezzo_acquisto_finale = prezzo_netto - sconto_importo
    ```
    
    #### Formula per il prezzo d'acquisto netto (Altri paesi)
    ```
    prezzo_lordo = prezzo_con_iva
    prezzo_netto = prezzo_lordo / (1 + aliquota_iva)
    prezzo_acquisto_finale = prezzo_netto * (1 - percentuale_sconto)
    ```
    
    #### Formula per il calcolo delle commissioni
    ```
    commissione_referral = prezzo_vendita * percentuale_categoria
    commissione_referral = max(commissione_referral, 0.30)  # Minimo 0,30€
    imposta_servizi_digitali = commissione_referral * 0.03
    commissioni_totali = commissione_referral + imposta_servizi_digitali
    ```
    
    #### Formula per il margine netto
    ```
    prezzo_netto = prezzo_vendita / (1 + aliquota_iva)
    costi_totali = commissioni_totali + costo_spedizione
    margine_netto = prezzo_netto - costi_totali - prezzo_acquisto
    margine_percentuale = (margine_netto / prezzo_vendita) * 100
    ```
    
    #### Formula per l'Opportunity Score
    ```
    differenza_margine = margine_target - margine_source
    opportunity_score = differenza_margine * (margine_percentuale_target / 100)
    ```
    """)

# Aggiungi statistiche di utilizzo nella sidebar
if 'all_opportunities' in st.session_state and st.session_state['all_opportunities'] is not None:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 Statistiche")
        
        df_opps = st.session_state['all_opportunities']
        
        st.markdown(f"**Opportunità analizzate:** {len(df_opps)}")
        
        if not df_opps.empty:
            # Migliori coppie di marketplace
            market_pairs = df_opps.groupby(["Source_Marketplace", "Target_Marketplace"])["Opportunity_Score"].mean().sort_values(ascending=False)
            
            st.markdown("**Migliori coppie di marketplace:**")
            for (source, target), score in market_pairs.head(5).items():
                st.markdown(f"- {source} → {target}: {score:.2f}")
            
            # Categorie più profittevoli
            if "Category" in df_opps.columns:
                top_categories = df_opps.groupby("Category")["Target_Margin_Pct"].mean().sort_values(ascending=False)
                
                st.markdown("**Categorie più profittevoli:**")
                for category, margin in top_categories.head(3).items():
                    st.markdown(f"- {category}: {margin:.2f}%")

# Aggiungi un footer
st.markdown("""
<div class="footer">
    <p>Amazon EU Multi-Marketplace Arbitrage Calculator v2.0</p>
    <p>Sviluppato per l'arbitraggio tra tutti i marketplace Amazon europei</p>
    <p>Ultimo aggiornamento: Marzo 2025</p>
</div>
""", unsafe_allow_html=True)

# Aggiungi funzionalità per visualizzare dettagli di un singolo prodotto
with st.expander("🔍 Analisi dettagliata per ASIN"):
    search_asin_detail = st.text_input("Inserisci ASIN da analizzare", "")
    
    if search_asin_detail and 'all_opportunities' in st.session_state and st.session_state['all_opportunities'] is not None:
        df_opps = st.session_state['all_opportunities']
        product_data = df_opps[df_opps["ASIN"] == search_asin_detail]
        
        if not product_data.empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Prendi la prima riga per le informazioni generali
            product = product_data.iloc[0]
            
            st.markdown(f"## {product['Title']}")
            st.markdown(f"**ASIN:** {product['ASIN']}")
            
            # Mostra tutte le opportunità per questo ASIN
            st.markdown("### Opportunità di arbitraggio per questo prodotto")
            
            # Ordina per opportunity score
            product_data = product_data.sort_values("Opportunity_Score", ascending=False)
            
            for idx, row in product_data.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown(f"**{row['Source_Marketplace']} → {row['Target_Marketplace']}**")
                        st.markdown(f"Score: {row['Opportunity_Score']:.2f}")
                    
                    with col2:
                        buy_info = f"🛒 Acquista a €{row['Source_Price']:.2f} ({row['Source_Price_Type']}, Netto: €{row['Buy_Price']:.2f})"
                        sell_info = f"💰 Vendi a €{row['Target_Price']:.2f} ({row['Target_Price_Type']})"
                        margin_info = f"📊 Margine: €{row['Target_Margin']:.2f} ({row['Target_Margin_Pct']:.2f}%)"
                        shipping_info = f"🚚 Spedizione: €{row['Shipping_Cost']:.2f}"
                        
                        st.markdown(buy_info)
                        st.markdown(sell_info)
                        st.markdown(margin_info)
                        st.markdown(shipping_info)
                
                st.markdown("---")
            
            # Aggiungi link ad Amazon per i vari marketplace
            st.markdown("### Visualizza su Amazon")
            
            marketplace_links = []
            for marketplace in product_data["Source_Marketplace"].unique():
                marketplace_code = marketplace.lower()
                marketplace_links.append(f"[Amazon {marketplace}](https://www.amazon.{marketplace_code}/dp/{product['ASIN']})")
            
            st.markdown(" | ".join(marketplace_links))
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning(f"ASIN {search_asin_detail} non trovato nei dati analizzati.")

# Aggiungi un pulsante per ripristinare le impostazioni predefinite
with st.sidebar:
    st.markdown("---")
    reset_btn = st.button("Ripristina Impostazioni", use_container_width=True)
    
    if reset_btn:
        st.session_state['marketplace_data'] = {}
        st.session_state['all_asins'] = None
        st.session_state['all_opportunities'] = None
        st.session_state['last_update'] = None
        st.experimental_rerun()