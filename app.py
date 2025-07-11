import streamlit as st

# QUESTO DEVE ESSERE IL PRIMO COMANDO STREAMLIT
# Prima di qualsiasi altra importazione che potrebbe contenere comandi Streamlit
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ora possiamo importare altri moduli
import pandas as pd
import numpy as np
import re
import altair as alt
import io
from streamlit_extras.colored_header import colored_header
from streamlit_extras.metric_cards import style_metric_cards

# CSS personalizzato per tema dark
st.markdown("""
<style>
    /* Tema dark globale */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    
    /* Sidebar dark */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
        border-right: 1px solid #333;
    }
    
    /* Titoli e intestazioni */
    .main-header {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #e0e0e0;
        font-size: 2.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #0d6efd;
        margin-bottom: 1.5rem;
    }
    .subheader {
        color: #cccccc;
        font-size: 1.5rem;
        padding-top: 1rem;
    }
    
    /* Cards e contenitori */
    .card {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        padding: 1.5rem;
        background-color: #1e1e1e;
        margin-bottom: 1rem;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    .result-container {
        background-color: #1e1e1e;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        padding: 1.5rem;
        margin-top: 2rem;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    .filter-group {
        background-color: #252525;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    
    /* Pulsanti e interazioni */
    .stButton>button {
        background-color: #0d6efd;
        color: white;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0b5ed7;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
    }
    
    /* Tag colorati */
    .success-tag {
        background-color: #198754;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .warning-tag {
        background-color: #fd7e14;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .danger-tag {
        background-color: #dc3545;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    
    /* Input e form controls */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color: #333;
        color: #e0e0e0;
        border: 1px solid #444;
    }
    .stTextInput>label, .stSelectbox>label, .stNumberInput>label, .stSlider>label {
        color: #cccccc !important;
    }
    
    /* Slider */
    .stSlider>div>div {
        background-color: #444;
    }
    .stSlider>div>div>div>div {
        background-color: #0d6efd;
    }
    
    /* Testo generale */
    p, span, div, td, th, label {
        color: #e0e0e0 !important;
    }
    
    /* Links */
    a {
        color: #0d6efd !important;
    }
    a:hover {
        color: #0b5ed7 !important;
        text-decoration: underline;
    }
    
    /* Schede */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 0 0 10px 10px;
        color: #e0e0e0;
        border-left: 1px solid #333;
        border-right: 1px solid #333;
        border-bottom: 1px solid #333;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #252525;
        color: #cccccc;
        border-radius: 5px 5px 0 0;
        margin-right: 2px;
        border: 1px solid #333;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e1e1e;
        border-top: 2px solid #0d6efd;
        border-bottom: none;
        color: #e0e0e0;
    }
    
    /* DataFrames e tabelle */
    .stDataFrame {
        border: 1px solid #333;
    }
    .stDataFrame th {
        background-color: #252525 !important;
        color: #e0e0e0 !important;
        border-bottom: 1px solid #444 !important;
    }
    .stDataFrame td {
        color: #e0e0e0 !important;
        background-color: #1e1e1e !important;
        border-bottom: 1px solid #333 !important;
    }
    .css-o1jpvw {
        color: #e0e0e0 !important;
    }
    
    /* Area di testo e input multilinea */
    .stTextArea>div>div>textarea {
        background-color: #333;
        color: #e0e0e0;
        border: 1px solid #444;
    }
    
    /* Metriche */
    [data-testid="stMetricValue"] {
        background-color: #252525;
        color: #e0e0e0 !important;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #333;
    }
    [data-testid="stMetricLabel"] {
        color: #aaaaaa !important;
    }
    [data-testid="stMetricDelta"] {
        color: #0d6efd !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #252525 !important;
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
    }
    .streamlit-expanderContent {
        background-color: #1e1e1e !important;
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #252525 !important;
        border: 1px dashed #444 !important;
    }
    [data-testid="stFileUploader"] div {
        color: #cccccc !important;
    }
    
    /* Divisori */
    hr {
        border-color: #333 !important;
    }

    /* Button personalizzato */
    .copy-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #0d6efd;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 16px;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        margin-top: 10px;
        width: 100%;
    }
    
    .copy-button:hover {
        background-color: #0b5ed7;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-1px);
    }
    
    .copy-button:active {
        transform: translateY(1px);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    }
    
    .copy-button svg {
        margin-right: 8px;
    }
    
    /* Notifica di copia */
    #copy-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #198754;
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }
    
    .show-notification {
        opacity: 1 !important;
    }
    
    /* Shipping calculator card */
    .shipping-card {
        background-color: #252525;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #444;
        margin-bottom: 15px;
    }
    
    .shipping-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 10px;
        color: #e0e0e0;
    }
</style>

<!-- Elementi extra UI -->
<div id="copy-notification">ASINs copiati negli appunti! ✓</div>

<!-- Script per la copia negli appunti -->
<script>
function copyASINsToClipboard() {
    const asinsText = document.getElementById('asins-content').value;
    
    // Usa l'API Clipboard moderna
    navigator.clipboard.writeText(asinsText)
        .then(() => {
            // Mostra la notifica
            const notification = document.getElementById('copy-notification');
            notification.classList.add('show-notification');
            
            // Nascondi la notifica dopo 2 secondi
            setTimeout(() => {
                notification.classList.remove('show-notification');
            }, 2000);
        })
        .catch(err => {
            console.error('Errore nella copia: ', err);
            alert('Non è stato possibile copiare gli ASIN. Prova a selezionarli manualmente.');
        });
}
</script>
""", unsafe_allow_html=True)

# Inizializzazione delle "ricette" in session_state
if 'recipes' not in st.session_state:
    st.session_state['recipes'] = {}

# Inizializzazione dei dati filtrati per la sessione
if 'filtered_data' not in st.session_state:
    st.session_state['filtered_data'] = None

st.markdown('<h1 class="main-header">📊 Amazon Market Analyzer - Arbitraggio Multi-Mercato</h1>', unsafe_allow_html=True)

# Definizione del listino costi di spedizione (Italia)
SHIPPING_COSTS = {
    3: 5.14,   # Fino a 3 kg
    4: 6.41,   # Fino a 4 kg
    5: 6.95,   # Fino a 5 kg
    10: 8.54,  # Fino a 10 kg
    25: 12.51, # Fino a 25 kg
    50: 21.66, # Fino a 50 kg
    100: 34.16 # Fino a 100 kg
}

# Aliquote IVA per paese (codice mercato -> percentuale)
VAT_RATES = {
    "IT": 22,
    "DE": 19,
    "FR": 20,
    "ES": 21,
    "UK": 20,
}

# Funzione per calcolare il costo di spedizione in base al peso
def calculate_shipping_cost(weight_kg):
    """
    Calcola il costo di spedizione in base al peso in kg
    
    Args:
        weight_kg (float): Peso in kg
        
    Returns:
        float: Costo di spedizione
    """
    if pd.isna(weight_kg) or weight_kg <= 0:
        return 0.0
    
    # Trova la categoria di peso appropriata
    for weight_limit, cost in sorted(SHIPPING_COSTS.items()):
        if weight_kg <= weight_limit:
            return cost
    
    # Se superiore al limite massimo, utilizza il costo massimo
    return SHIPPING_COSTS[100]

#################################
# Sidebar: Caricamento file, Prezzo di riferimento, Sconto, Impostazioni e Ricette
#################################
with st.sidebar:
    colored_header(label="🔄 Caricamento Dati", description="Carica i file dei mercati", color_name="blue-70")
    
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

    colored_header(label="💰 Impostazioni Prezzi", description="Configurazione prezzi", color_name="blue-70")
    price_options = ["Buy Box 🚚: Current", "Amazon: Current", "New: Current"]
    ref_price_base = st.selectbox(
        "Per la Lista di Origine",
        price_options
    )
    ref_price_comp = st.selectbox(
        "Per la Lista di Confronto",
        price_options
    )

    colored_header(label="🏷️ Sconto", description="Parametri finanziari", color_name="blue-70")
    discount_percent = st.number_input("Sconto sugli acquisti (%)", min_value=0.0, value=st.session_state.get("discount_percent", 20.0), step=0.1, key="discount_percent")
    discount = discount_percent / 100.0  # convertiamo in frazione
    
    
    # Sezione per i costi di spedizione
    colored_header(label="🚚 Spedizione", description="Calcolo costi di spedizione", color_name="blue-70")
    
    # Visualizzazione dei costi di spedizione
    st.markdown('<div class="shipping-card">', unsafe_allow_html=True)
    st.markdown('<div class="shipping-title">📦 Listino Costi di Spedizione (Italia)</div>', unsafe_allow_html=True)
    
    # Creare una tabella per il listino
    shipping_table = pd.DataFrame({
        "Peso (kg)": ["Fino a 3", "Fino a 4", "Fino a 5", "Fino a 10", "Fino a 25", "Fino a 50", "Fino a 100"],
        "Costo (€)": [SHIPPING_COSTS[3], SHIPPING_COSTS[4], SHIPPING_COSTS[5], SHIPPING_COSTS[10], 
                      SHIPPING_COSTS[25], SHIPPING_COSTS[50], SHIPPING_COSTS[100]]
    })
    st.dataframe(shipping_table, hide_index=True, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Includi costi di spedizione nel calcolo
    include_shipping = st.checkbox("Calcola margine netto con spedizione", value=True)
    
    colored_header(label="📈 Opportunity Score", description="Pesi e parametri", color_name="blue-70")
    
    tab1, tab2 = st.tabs(["Parametri Base", "Parametri Avanzati"])
    
    with tab1:
        alpha = st.slider("Peso per Sales Rank (penalità)", 0.0, 5.0, st.session_state.get("alpha", 1.0), step=0.1, key="alpha")
        beta = st.slider("Peso per 'Bought in past month'", 0.0, 5.0, st.session_state.get("beta", 1.0), step=0.1, key="beta")
        delta = st.slider("Peso penalizzante per Offer Count", 0.0, 5.0, st.session_state.get("delta", 1.0), step=0.1, key="delta")
        epsilon = st.slider("Peso per il Margine (%)", 0.0, 10.0, st.session_state.get("epsilon", 3.0), step=0.1, key="epsilon")  # Valore predefinito aumentato
        zeta = st.slider("Peso per Trend Sales Rank", 0.0, 5.0, st.session_state.get("zeta", 1.0), step=0.1, key="zeta")
    
    with tab2:
        gamma = st.slider("Peso per volume di vendita", 0.0, 5.0, st.session_state.get("gamma", 2.0), step=0.1, key="gamma")
        theta = st.slider("Peso per margine assoluto (€)", 0.0, 5.0, st.session_state.get("theta", 1.5), step=0.1, key="theta")
        min_margin_multiplier = st.slider("Moltiplicatore margine minimo", 1.0, 3.0, st.session_state.get("min_margin_multiplier", 1.2), step=0.1, key="min_margin_multiplier")
    
    colored_header(label="🔍 Filtri Avanzati", description="Limita i risultati", color_name="blue-70")
    max_sales_rank = st.number_input("Sales Rank massimo", min_value=1, value=999999)
    max_offer_count = st.number_input("Offer Count massimo", min_value=1, value=30)  # Valore predefinito più realistico
    min_buybox_price = st.number_input("Prezzo minimo (€)", min_value=0.0, value=15.0)  # Valore predefinito più realistico
    max_buybox_price = st.number_input("Prezzo massimo (€)", min_value=0.0, value=200.0)  # Valore predefinito più realistico
    min_margin_pct = st.number_input("Margine minimo (%)", min_value=0.0, value=15.0)  # Nuovo filtro
    min_margin_abs = st.number_input("Margine minimo (€)", min_value=0.0, value=5.0)  # Nuovo filtro
    
    colored_header(label="📋 Ricette", description="Salva e carica configurazioni", color_name="blue-70")
    selected_recipe = st.selectbox("Carica Ricetta", options=["-- Nessuna --"] + list(st.session_state['recipes'].keys()))
    if selected_recipe != "-- Nessuna --":
        recipe = st.session_state['recipes'][selected_recipe]
        st.session_state["alpha"] = recipe.get("alpha", 1.0)
        st.session_state["beta"] = recipe.get("beta", 1.0)
        st.session_state["delta"] = recipe.get("delta", 1.0)
        st.session_state["epsilon"] = recipe.get("epsilon", 3.0)
        st.session_state["zeta"] = recipe.get("zeta", 1.0)
        st.session_state["gamma"] = recipe.get("gamma", 2.0)
        st.session_state["theta"] = recipe.get("theta", 1.5)
        st.session_state["min_margin_multiplier"] = recipe.get("min_margin_multiplier", 1.2)
        st.session_state["discount_percent"] = recipe.get("discount_percent", 20.0)
    
    new_recipe_name = st.text_input("Nome Nuova Ricetta")
    if st.button("💾 Salva Ricetta"):
        if new_recipe_name:
            st.session_state['recipes'][new_recipe_name] = {
                "alpha": st.session_state.get("alpha", 1.0),
                "beta": st.session_state.get("beta", 1.0),
                "delta": st.session_state.get("delta", 1.0),
                "epsilon": st.session_state.get("epsilon", 3.0),
                "zeta": st.session_state.get("zeta", 1.0),
                "gamma": st.session_state.get("gamma", 2.0),
                "theta": st.session_state.get("theta", 1.5),
                "min_margin_multiplier": st.session_state.get("min_margin_multiplier", 1.2),
                "discount_percent": st.session_state.get("discount_percent", 20.0)
            }
            st.success(f"Ricetta '{new_recipe_name}' salvata!")
        else:
            st.error("Inserisci un nome valido per la ricetta.")

    st.markdown("---")
    avvia = st.button("🚀 Calcola Opportunity Score", use_container_width=True)

#################################
# Funzioni di Caricamento e Parsing
#################################
def load_data(uploaded_file):
    """Carica dati da CSV o XLSX in un DataFrame."""
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    if fname.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str)
    else:
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df

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

# Funzione per parsare il peso dagli attributi
def parse_weight(x):
    """Estrae il peso in kg dai campi di attributo."""
    if not isinstance(x, str):
        return np.nan

    # Cerca pattern come "0.5 kg" o "500 g"
    kg_match = re.search(r'(\d+\.?\d*)\s*kg', x.lower())
    g_match = re.search(r'(\d+\.?\d*)\s*g', x.lower())

    if kg_match:
        return float(kg_match.group(1))
    elif g_match:
        return float(g_match.group(1)) / 1000  # converti grammi in kg
    else:
        # Se la stringa è puramente numerica, interpretala come kg
        numeric_match = re.fullmatch(r'\s*(\d+\.?\d*)\s*', x)
        if numeric_match:
            try:
                return float(numeric_match.group(1))
            except ValueError:
                return np.nan
        return np.nan

# Funzione per formattare il Trend in base al valore di Trend_Bonus
def format_trend(trend):
    if pd.isna(trend):
        return "N/D"
    if trend > 0.1:
        return "🔼 Crescente"
    elif trend < -0.1:
        return "🔽 Decrescente"
    else:
        return "➖ Stabile"

# Funzione per classificare l'Opportunity Score
def classify_opportunity(score):
    if score > 100:
        return "Eccellente", "success-tag"
    elif score > 50:
        return "Buona", "success-tag"
    elif score > 20:
        return "Discreta", "warning-tag"
    else:
        return "Bassa", "danger-tag"

#################################
# Visualizzazione Immediata degli ASIN dalla Lista di Origine
#################################
tab_main1, tab_main2, tab_main3 = st.tabs(["📋 ASIN Caricati", "📊 Analisi Opportunità", "📎 Risultati Dettagliati"])

with tab_main1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
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
                st.success(f"Lista unificata di ASIN dalla Lista di Origine: {len(unique_asins)} prodotti")
                col1, col2 = st.columns([3, 1])
                with col1:
                    asin_text = "\n".join(unique_asins)
                    st.text_area("ASIN disponibili:", asin_text, height=200, key="asins-content", label_visibility="collapsed")
                    
                    # Pulsante migliorato per copiare gli ASIN
                    st.markdown(f"""
                    <button 
                        onclick="copyASINsToClipboard()" 
                        class="copy-button">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                            <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                        </svg>
                        Copia ASINs negli appunti
                    </button>
                    """, unsafe_allow_html=True)
                with col2:
                    st.metric("Totale ASIN", len(unique_asins))
                    if "Brand (base)" in df_base.columns:
                        st.metric("Brand Unici", df_base["Brand (base)"].nunique())
            else:
                st.warning("I file di origine non contengono la colonna ASIN.")
        else:
            st.info("Carica la Lista di Origine per vedere gli ASIN unificati.")
    else:
        st.info("👆 Carica i file nella barra laterale per iniziare l'analisi")
    
    st.markdown('</div>', unsafe_allow_html=True)

#################################
# Funzione per Calcolare il Prezzo d'Acquisto Netto - AGGIORNATA con IVA variabile
#################################
def calc_final_purchase_price(row, discount):
    """
    Calcola il prezzo d'acquisto netto, IVA esclusa e scontato, in base al paese.
    
    Params:
      row: la riga del dataframe
      discount: percentuale di sconto (in formato decimale, es. 0.2 per 20%)
      Determina automaticamente l'aliquota IVA in base al mercato di origine
    
    Returns:
      Il prezzo di acquisto netto (IVA esclusa e scontato)
    """
    gross = row["Price_Base"]
    if pd.isna(gross):
        return np.nan
    
    # Calcolo prezzo netto (senza IVA)
    locale = row.get("Locale (base)", "")
    vat_rate = VAT_RATES.get(locale, 0) / 100.0
    net_price = gross / (1 + vat_rate)
    
    # Calcolo prezzo scontato
    discounted_price = net_price * (1 - discount)
    
    return discounted_price

#################################
# Elaborazione Completa e Calcolo Opportunity Score
#################################
if avvia:
    # Controllo file di confronto
    if not comparison_files:
        with tab_main1:
            st.error("Carica almeno un file di Liste di Confronto.")
        st.stop()
    
    # Elaborazione Liste di Confronto
    comp_list = []
    for f in comparison_files:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            comp_list.append(df_temp)
        else:
            with tab_main1:
                st.warning(f"Il file di confronto {f.name} è vuoto o non valido.")
    if not comp_list:
        with tab_main1:
            st.error("Nessun file di confronto valido caricato.")
        st.stop()
    df_comp = pd.concat(comp_list, ignore_index=True)
    
    # Verifica della presenza della colonna ASIN in entrambi i dataset
    if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
        with tab_main1:
            st.error("Assicurati che entrambi i file (origine e confronto) contengano la colonna ASIN.")
        st.stop()
    
    # Normalizza gli ASIN rimuovendo spazi e usando il maiuscolo
    df_base["ASIN"] = df_base["ASIN"].str.strip().str.upper()
    df_comp["ASIN"] = df_comp["ASIN"].str.strip().str.upper()

    # Merge tra base e confronto sulla colonna ASIN
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        with tab_main1:
            st.error("Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto.")
        st.stop()
    
    # Utilizza le colonne di prezzo selezionate dalla sidebar
    price_col_base = f"{ref_price_base} (base)"
    price_col_comp = f"{ref_price_comp} (comp)"
    df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(parse_float)
    df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(parse_float)
    
    # Conversione dei dati dal mercato di confronto per le altre metriche
    df_merged["SalesRank_Comp"] = df_merged.get("Sales Rank: Current (comp)", pd.Series(np.nan)).apply(parse_int)
    df_merged["Bought_Comp"] = df_merged.get("Bought in past month (comp)", pd.Series(np.nan)).apply(parse_int)
    df_merged["NewOffer_Comp"] = df_merged.get("New Offer Count: Current (comp)", pd.Series(np.nan)).apply(parse_int)
    # Leggi anche il Sales Rank a 30 giorni, se presente
    df_merged["SalesRank_30d"] = df_merged.get("Sales Rank: 30 days avg. (comp)", pd.Series(np.nan)).apply(parse_int)
    
    # Estrai informazioni sul peso
    # Cerca in varie colonne che potrebbero contenere informazioni sul peso
    possible_weight_cols = [
        "Weight (base)",
        "Item Weight (base)",
        "Package: Weight (kg) (base)",
        "Package: Weight (g) (base)",
        "Product details (base)",
        "Features (base)"
    ]
    
    # Inizializza colonna peso
    df_merged["Weight_kg"] = np.nan
    
    # Cerca nelle possibili colonne di peso
    for col in possible_weight_cols:
        if col in df_merged.columns:
            if "(g)" in col:
                # Valori espressi in grammi
                def to_kg(val):
                    if pd.isna(val):
                        return np.nan
                    try:
                        num = re.search(r'(\d+\.?\d*)', str(val))
                        return float(num.group(1)) / 1000 if num else np.nan
                    except Exception:
                        return np.nan
                weight_data = df_merged[col].apply(to_kg)
            else:
                weight_data = df_merged[col].apply(parse_weight)
            # Aggiorna solo i valori mancanti
            df_merged.loc[df_merged["Weight_kg"].isna(), "Weight_kg"] = weight_data.loc[df_merged["Weight_kg"].isna()]
    
    # Se non ci sono informazioni sul peso, imposta un valore predefinito
    df_merged["Weight_kg"] = df_merged["Weight_kg"].fillna(1.0)  # Assume 1kg come predefinito
    
    # Calcola il costo di spedizione per ogni prodotto
    df_merged["Shipping_Cost"] = df_merged["Weight_kg"].apply(calculate_shipping_cost)
    
    # Calcolo del prezzo d'acquisto netto per ogni prodotto dalla lista di origine
    # Utilizzo della funzione aggiornata con IVA variabile
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount), axis=1)
    
    # NUOVA LOGICA: Calcolo del margine stimato considerando IVA correttamente
    # 1. Prezzo nel mercato di confronto (lordo IVA)
    # 2. Prezzo di acquisto netto (già senza IVA)
    # 3. Margine = Prezzo confronto / (1 + IVA) - Prezzo acquisto netto
    
    # Calcolo del prezzo netto di vendita nel mercato di confronto (senza IVA)
    df_merged["Vendita_Netto"] = df_merged.apply(lambda row: row["Price_Comp"] / (1 + VAT_RATES.get(row.get("Locale (comp)", ""), 0) / 100.0), axis=1)
    
    # Calcolo del margine stimato corretto (in valore assoluto e percentuale)
    df_merged["Margine_Stimato"] = df_merged["Vendita_Netto"] - df_merged["Acquisto_Netto"]
    df_merged["Margine_%"] = (df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]) * 100
    
    # Calcolo del margine netto con costi di spedizione
    if include_shipping:
        df_merged["Margine_Netto"] = df_merged["Margine_Stimato"] - df_merged["Shipping_Cost"]
        df_merged["Margine_Netto_%"] = (df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]) * 100
    else:
        df_merged["Margine_Netto"] = df_merged["Margine_Stimato"]
        df_merged["Margine_Netto_%"] = df_merged["Margine_%"]
    
    # Nuovo calcolo del margine percentuale tra i prezzi lordi (solo per riferimento)
    df_merged["Margin_Pct_Lordo"] = (df_merged["Price_Comp"] - df_merged["Price_Base"]) / df_merged["Price_Base"] * 100
    
    # Filtro sui prodotti con margine positivo
    df_merged = df_merged[df_merged["Margine_Netto_%"] > min_margin_pct]
    df_merged = df_merged[df_merged["Margine_Netto"] > min_margin_abs]
    
    # Applicazione dei filtri avanzati (sul mercato di confronto)
    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged = df_merged[df_merged["SalesRank_Comp"] <= max_sales_rank]
    
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    df_merged = df_merged[df_merged["NewOffer_Comp"] <= max_offer_count]
    
    df_merged["Price_Comp"] = df_merged["Price_Comp"].fillna(0)
    df_merged = df_merged[df_merged["Price_Comp"].between(min_buybox_price, max_buybox_price)]
    
    # Calcolo del bonus/penalità per il Trend del Sales Rank
    df_merged["Trend_Bonus"] = np.log((df_merged["SalesRank_30d"].fillna(df_merged["SalesRank_Comp"]) + 1) / (df_merged["SalesRank_Comp"] + 1))
    # Formattiamo il trend in una stringa con icona
    df_merged["Trend"] = df_merged["Trend_Bonus"].apply(format_trend)
    
    # NUOVA FORMULA per l'Opportunity Score
    # Normalizzazione rank per evitare divisioni per zero o valori negativi
    df_merged["Norm_Rank"] = np.log(df_merged["SalesRank_Comp"].fillna(999999) + 10)
    
    # Calcoliamo il volume stimato di vendite (inversamente proporzionale al rank)
    df_merged["Volume_Score"] = 1000 / df_merged["Norm_Rank"]
    
    # Calcolo del fattore di ROI (Return on Investment)
    df_merged["ROI_Factor"] = df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]
    
    # Calcolo del nuovo Opportunity Score (ora basato sul margine netto)
    df_merged["Opportunity_Score"] = (
        epsilon * df_merged["Margine_Netto_%"] +
        theta * df_merged["Margine_Netto"] +
        beta * np.log(1 + df_merged["Bought_Comp"].fillna(0)) -
        delta * np.minimum(df_merged["NewOffer_Comp"].fillna(0), 10) -
        alpha * df_merged["Norm_Rank"] +
        zeta * df_merged["Trend_Bonus"] +
        gamma * df_merged["Volume_Score"]
    )
    
    # Fattore di penalizzazione per margini troppo bassi
    min_margin_threshold = min_margin_abs * min_margin_multiplier
    df_merged.loc[df_merged["Margine_Netto"] < min_margin_threshold, "Opportunity_Score"] *= (df_merged["Margine_Netto"] / min_margin_threshold)
    
    # Normalizzazione dei punteggi per renderli più leggibili (0-100 scala)
    max_score = df_merged["Opportunity_Score"].max()
    if not np.isnan(max_score) and max_score > 0:
        df_merged["Opportunity_Score"] = (df_merged["Opportunity_Score"] / max_score) * 100
    
    # Classificazione dell'opportunità - Correzione dell'errore
    # Invece di assegnare una Series a due colonne, creiamo le colonne separatamente
    df_merged["Opportunity_Class"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[0]  # Solo il primo elemento della tupla
    )
    df_merged["Opportunity_Tag"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[1]  # Solo il secondo elemento della tupla
    )
    
    # Aggiunta dell'informazione sulle aliquote IVA utilizzate
    df_merged["IVA_Origine"] = df_merged["Locale (base)"].map(lambda x: f"{VAT_RATES.get(x, 0)}%")
    df_merged["IVA_Confronto"] = df_merged["Locale (comp)"].map(lambda x: f"{VAT_RATES.get(x, 0)}%")
    
    # Ordiniamo i risultati per Opportunity Score decrescente
    df_merged = df_merged.sort_values("Opportunity_Score", ascending=False)
    
    # Selezione delle colonne finali da visualizzare
    cols_final = [
        "Locale (base)", "Locale (comp)", "Title (base)", "ASIN",
        "Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto",
        "Margine_Stimato", "Shipping_Cost", "Margine_Netto", "Margine_Netto_%", 
        "Weight_kg", "SalesRank_Comp", "SalesRank_30d",
        "Trend", "Bought_Comp", "NewOffer_Comp", "Volume_Score",
        "Opportunity_Score", "Opportunity_Class", "IVA_Origine", "IVA_Confronto",
        "Brand (base)", "Package: Dimension (cm³) (base)"
    ]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    
    # Arrotonda i valori numerici principali a 2 decimali
    cols_to_round = ["Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto", 
                     "Margine_Stimato", "Shipping_Cost", "Margine_Netto", "Margine_Netto_%", 
                     "Margine_%", "Opportunity_Score", "Volume_Score", "Weight_kg"]
    for col in cols_to_round:
        if col in df_finale.columns:
            df_finale[col] = df_finale[col].round(2)
    
    # Salviamo i dati nella sessione per i filtri interattivi
    st.session_state['filtered_data'] = df_finale
    
    #################################
    # Dashboard Interattiva
    #################################
    with tab_main2:
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        st.subheader("📊 Dashboard delle Opportunità")
        
        # Metriche principali
        if not df_finale.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Prodotti Trovati", len(df_finale))
            with col2:
                st.metric("Margine Netto Medio (%)", f"{df_finale['Margine_Netto_%'].mean():.2f}%")
            with col3:
                st.metric("Margine Netto Medio (€)", f"{df_finale['Margine_Netto'].mean():.2f}€")
            with col4:
                st.metric("Opportunity Score Massimo", f"{df_finale['Opportunity_Score'].max():.2f}")
            
            # Riepilogo impostazioni
            st.info('Aliquote IVA determinate automaticamente per ogni riga | ' + ('✅ Spedizione Inclusa' if include_shipping else '❌ Spedizione Esclusa'))
            
            # Configura i colori per il tema dark in Altair
            dark_colors = {
                "Eccellente": "#2ecc71",
                "Buona": "#27ae60",
                "Discreta": "#f39c12",
                "Bassa": "#e74c3c"
            }
            
            # Grafico di distribuzione degli Opportunity Score
            st.subheader("Distribuzione Opportunity Score")
            hist = alt.Chart(df_finale.reset_index()).mark_bar().encode(
                alt.X("Opportunity_Score:Q", bin=alt.Bin(maxbins=20), title="Opportunity Score"),
                alt.Y("count()", title="Numero di Prodotti"),
                color=alt.Color("Opportunity_Class:N", 
                               scale=alt.Scale(domain=list(dark_colors.keys()),
                                              range=list(dark_colors.values())))
            ).properties(height=250)
            st.altair_chart(hist, use_container_width=True)
            
            # Grafico Scatter: Margine Netto (%) vs Opportunity Score con dimensione per Volume
            st.subheader("Analisi Multifattoriale")
            chart = alt.Chart(df_finale.reset_index()).mark_circle().encode(
                x=alt.X("Margine_Netto_%:Q", title="Margine Netto (%)"),
                y=alt.Y("Opportunity_Score:Q", title="Opportunity Score"),
                size=alt.Size("Volume_Score:Q", title="Volume Stimato", scale=alt.Scale(range=[20, 200])),
                color=alt.Color("Locale (comp):N", title="Mercato Confronto", scale=alt.Scale(scheme='category10')),
                tooltip=["Title (base)", "ASIN", "Margine_Netto_%", "Margine_Netto", "Shipping_Cost", "SalesRank_Comp", "Opportunity_Score", "Trend"]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
            
            # Analisi per Mercato di Confronto
            st.subheader("Analisi per Mercato")
            if "Locale (comp)" in df_finale.columns:
                market_analysis = df_finale.groupby("Locale (comp)").agg({
                    "ASIN": "count",
                    "Margine_Netto_%": "mean",
                    "Margine_Netto": "mean",
                    "Shipping_Cost": "mean",
                    "Opportunity_Score": "mean"
                }).reset_index()
                market_analysis.columns = ["Mercato", "Prodotti", "Margine Netto Medio (%)", 
                                          "Margine Netto Medio (€)", "Costo Spedizione Medio (€)",
                                          "Opportunity Score Medio"]
                market_analysis = market_analysis.round(2)
                st.dataframe(market_analysis, use_container_width=True)
                
                # Grafico a barre per confronto mercati
                market_chart = alt.Chart(market_analysis).mark_bar().encode(
                    x="Mercato:N",
                    y="Opportunity Score Medio:Q",
                    color=alt.Color("Mercato:N", scale=alt.Scale(scheme='category10')),
                    tooltip=["Mercato", "Prodotti", "Margine Netto Medio (%)", 
                            "Margine Netto Medio (€)", "Costo Spedizione Medio (€)", 
                            "Opportunity Score Medio"]
                ).properties(height=300)
                st.altair_chart(market_chart, use_container_width=True)
        else:
            st.info("Nessun prodotto trovato con i filtri applicati.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Risultati dettagliati e filtri interattivi
    with tab_main3:
        if st.session_state['filtered_data'] is not None and not st.session_state['filtered_data'].empty:
            st.markdown('<div class="result-container">', unsafe_allow_html=True)
            st.subheader("🔍 Esplora i Risultati")
            
            # Filtri interattivi
            st.markdown('<div class="filter-group">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            
            filtered_df = st.session_state['filtered_data'].copy()
            
            with col1:
                if "Locale (comp)" in filtered_df.columns:
                    markets = ["Tutti"] + sorted(filtered_df["Locale (comp)"].unique().tolist())
                    selected_market = st.selectbox("Filtra per Mercato", markets)
                    if selected_market != "Tutti":
                        filtered_df = filtered_df[filtered_df["Locale (comp)"] == selected_market]
            
            with col2:
                if "Brand (base)" in filtered_df.columns:
                    brands = ["Tutti"] + sorted(filtered_df["Brand (base)"].unique().tolist())
                    selected_brand = st.selectbox("Filtra per Brand", brands)
                    if selected_brand != "Tutti":
                        filtered_df = filtered_df[filtered_df["Brand (base)"] == selected_brand]
            
            with col3:
                if "Opportunity_Class" in filtered_df.columns:
                    classes = ["Tutti"] + sorted(filtered_df["Opportunity_Class"].unique().tolist())
                    selected_class = st.selectbox("Filtra per Qualità Opportunità", classes)
                    if selected_class != "Tutti":
                        filtered_df = filtered_df[filtered_df["Opportunity_Class"] == selected_class]
            
            col1, col2 = st.columns(2)
            with col1:
                min_op_score = st.slider("Opportunity Score Minimo", 
                                         min_value=float(filtered_df["Opportunity_Score"].min()),
                                         max_value=float(filtered_df["Opportunity_Score"].max()),
                                         value=float(filtered_df["Opportunity_Score"].min()))
                filtered_df = filtered_df[filtered_df["Opportunity_Score"] >= min_op_score]
            
            with col2:
                min_margin = st.slider("Margine Netto Minimo (€)", 
                                      min_value=float(filtered_df["Margine_Netto"].min()),
                                      max_value=float(filtered_df["Margine_Netto"].max()),
                                      value=float(filtered_df["Margine_Netto"].min()))
                filtered_df = filtered_df[filtered_df["Margine_Netto"] >= min_margin]
            
            # Cerca per ASIN o titolo
            search_term = st.text_input("Cerca per ASIN o Titolo")
            if search_term:
                mask = (
                    filtered_df["ASIN"].str.contains(search_term, case=False, na=False) | 
                    filtered_df["Title (base)"].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Visualizzazione dei risultati filtrati
            if not filtered_df.empty:
                # Formato personalizzato per la tabella dei risultati in tema dark
                def highlight_opportunity(val):
                    if val == "Eccellente":
                        return 'background-color: #153d2e; color: #2ecc71; font-weight: bold'
                    elif val == "Buona":
                        return 'background-color: #14432d; color: #27ae60; font-weight: bold'
                    elif val == "Discreta":
                        return 'background-color: #402d10; color: #f39c12; font-weight: bold'
                    else:
                        return 'background-color: #3d1a15; color: #e74c3c; font-weight: bold'
                
                # Aggiungi la formattazione HTML per le classi di opportunity
                def format_with_html(df):
                    styled = df.style.map(  # Cambiato da applymap a map (deprecato)
                        lambda x: highlight_opportunity(x) if x in ["Eccellente", "Buona", "Discreta", "Bassa"] else '',
                        subset=["Opportunity_Class"]
                    )
                    return styled.format({
                        "Price_Base": "€{:.2f}",
                        "Acquisto_Netto": "€{:.2f}",
                        "Price_Comp": "€{:.2f}",
                        "Vendita_Netto": "€{:.2f}",
                        "Margine_Stimato": "€{:.2f}",
                        "Shipping_Cost": "€{:.2f}",
                        "Margine_Netto": "€{:.2f}",
                        "Margine_Netto_%": "{:.2f}%",
                        "Opportunity_Score": "{:.2f}",
                        "Volume_Score": "{:.2f}",
                        "Weight_kg": "{:.2f} kg"
                    })
                
                # Visualizzazione dei risultati - SENZA PAGINAZIONE
                st.markdown(f"**{len(filtered_df)} prodotti trovati**")
                
                # Selezione delle colonne da visualizzare
                display_cols = [col for col in filtered_df.columns if col not in ["Opportunity_Tag", "SalesRank_30d"]]
                
                # Mostra la tabella completa (senza paginazione)
                st.dataframe(
                    format_with_html(filtered_df[display_cols]),
                    height=600,  # Altezza fissa per visualizzare più righe
                    use_container_width=True
                )
                
                # Esportazione dati
                csv_data = filtered_df.to_csv(index=False, sep=";").encode("utf-8")
                excel_data = io.BytesIO()
                filtered_df.to_excel(excel_data, index=False)
                excel_data.seek(0)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Scarica CSV",
                        data=csv_data,
                        file_name="risultato_opportunity_arbitrage.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col2:
                    st.download_button(
                        label="📥 Scarica Excel",
                        data=excel_data,
                        file_name="risultato_opportunity_arbitrage.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.warning("Nessun prodotto corrisponde ai filtri selezionati.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("👈 Clicca su 'Calcola Opportunity Score' nella barra laterale per visualizzare i risultati.")

# Aggiunta dell'help
with st.expander("ℹ️ Come funziona l'Opportunity Score"):
    st.markdown("""
    ### Calcolo dell'Opportunity Score
    
    L'Opportunity Score è un punteggio che combina diversi fattori per identificare le migliori opportunità di arbitraggio. 
    La formula considera:
    
    - **Margine netto percentuale**: Quanto margine percentuale ottieni dopo aver sottratto i costi di spedizione
    - **Margine netto assoluto**: Quanto guadagno in euro ottieni per ogni vendita dopo i costi di spedizione
    - **Volume di vendita**: Stimato tramite il Sales Rank (più basso = più vendite)
    - **Trend**: Se il prodotto sta migliorando o peggiorando nel ranking
    - **Competizione**: Quante altre offerte ci sono per lo stesso prodotto
    - **Acquisti recenti**: Quanti acquisti sono stati fatti nell'ultimo mese
    
    ### Calcolo del Margine
    
    Il margine viene calcolato considerando:
    1. **Prezzo di acquisto netto**: Prezzo base scontato e senza IVA (usando l'aliquota IVA del mercato di origine)
    2. **Prezzo di vendita netto**: Prezzo di confronto senza IVA (usando l'aliquota IVA del mercato di confronto)
    3. **Margine stimato**: Differenza tra prezzo di vendita netto e prezzo di acquisto netto
    4. **Costi di spedizione**: Calcolati in base al peso del prodotto secondo il listino
    5. **Margine netto**: Margine stimato meno i costi di spedizione
    
    ### Calcolo dei Costi di Spedizione
    
    I costi di spedizione vengono calcolati in base al peso del prodotto secondo questo listino:
    - Fino a 3 kg: €5.14
    - Fino a 4 kg: €6.41
    - Fino a 5 kg: €6.95
    - Fino a 10 kg: €8.54
    - Fino a 25 kg: €12.51
    - Fino a 50 kg: €21.66
    - Fino a 100 kg: €34.16
    
    ### Note sull'IVA
    
    L'applicazione gestisce correttamente l'IVA dei diversi paesi, sia per il mercato di origine che per quello di confronto:
    - Italia: 22%
    - Germania: 19%
    - Francia: 20%
    - Spagna: 21%
    - Regno Unito: 20%
    
    Il margine stimato tiene conto di queste differenze, permettendoti di calcolare correttamente il potenziale guadagno anche quando il mercato di origine è diverso da quello italiano.
    """)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #333; color: #aaa;">
    Amazon Market Analyzer - Arbitraggio Multi-Mercato © 2025<br>
    Versione 2.0
</div>
""", unsafe_allow_html=True)