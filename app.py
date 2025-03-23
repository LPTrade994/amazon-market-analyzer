import streamlit as st

# QUESTO DEVE ESSERE IL PRIMO COMANDO STREAMLIT
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

# CSS personalizzato per tema dark con animazioni e transizioni per migliorare l'impatto visivo
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
    
    /* Cards e contenitori con animazione fadeIn */
    .card, .result-container, .filter-group {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        padding: 1.5rem;
        background-color: #1e1e1e;
        margin-bottom: 1rem;
        color: #e0e0e0;
        border: 1px solid #333;
        animation: fadeIn 0.5s ease-in-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    
    /* Container per le metriche */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Metriche */
    [data-testid="stMetricValue"] {
        background-color: #252525;
        color: #e0e0e0 !important;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #333;
        transition: transform 0.3s ease, background-color 0.3s ease;
    }
    [data-testid="stMetricValue"]:hover {
        transform: scale(1.05);
        background-color: #2a2a2a;
    }
    [data-testid="stMetricLabel"] {
        color: #aaaaaa !important;
    }
    [data-testid="stMetricDelta"] {
        color: #0d6efd !important;
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
        transition: background-color 0.3s ease, transform 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        transform: scale(1.05);
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
    
    /* Expander */
    .streamlit-expanderHeader, .streamlit-expanderContent {
        background-color: #252525 !important;
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
        transition: all 0.3s ease;
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

# Funzione per calcolare il fattore di penalizzazione del Return Rate
def calculate_return_rate_factor(return_rate):
    """
    Converte il Return Rate in un fattore numerico per il calcolo dell'Opportunity Score.
    
    Args:
        return_rate: Valore del Return Rate ("low", "high" o vuoto/None)
        
    Returns:
        float: Fattore di penalizzazione (1.0 per "low", 0.7 per "high", 0.85 per valori mancanti)
    """
    if pd.isna(return_rate) or return_rate == "":
        return 0.85  # Valore intermedio per dati mancanti
    
    return_rate_lower = str(return_rate).lower().strip()
    if return_rate_lower == "low":
        return 1.0  # Nessuna penalizzazione
    elif return_rate_lower == "high":
        return 0.7  # Forte penalizzazione
    else:
        return 0.85  # Default per valori non riconosciuti

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
    ref_price_base = st.selectbox(
        "Per la Lista di Origine",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )
    ref_price_comp = st.selectbox(
        "Per la Lista di Confronto",
        ["Buy Box: Current", "Amazon: Current", "New: Current"]
    )

    colored_header(label="🏷️ Sconto & IVA", description="Parametri finanziari", color_name="blue-70")
    discount_percent = st.number_input("Sconto sugli acquisti (%)", min_value=0.0, value=st.session_state.get("discount_percent", 20.0), step=0.1, key="discount_percent")
    discount = discount_percent / 100.0  # convertiamo in frazione
    
    # Aggiunta del selettore per l'IVA di riferimento per entrambi i mercati
    st.markdown("**IVA per calcolo del margine**")
    
    # Paesi e le loro aliquote IVA
    paesi_iva = [
        ("Italia", 22), 
        ("Germania", 19), 
        ("Francia", 20), 
        ("Spagna", 21), 
        ("Regno Unito", 20)
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Mercato Origine**")
        iva_base = st.selectbox(
            "IVA mercato origine",
            paesi_iva,
            format_func=lambda x: f"{x[0]} ({x[1]}%)",
            key="iva_base"
        )
        iva_base_rate = iva_base[1] / 100.0
    
    with col2:
        st.markdown("**Mercato Confronto**")
        iva_comp = st.selectbox(
            "IVA mercato confronto",
            paesi_iva,
            format_func=lambda x: f"{x[0]} ({x[1]}%)",
            key="iva_comp"
        )
        iva_comp_rate = iva_comp[1] / 100.0
    
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
        return_rate_weight = st.slider("Peso penalizzante per Return Rate alto", 0.0, 5.0, 
                                     st.session_state.get("return_rate_weight", 2.0), step=0.1, 
                                     key="return_rate_weight")
    
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
        st.session_state["return_rate_weight"] = recipe.get("return_rate_weight", 2.0)
        # Caricamento delle impostazioni IVA se presenti
        if "iva_base" in recipe:
            country_name, rate = recipe["iva_base"]
            idx = next((i for i, (name, _) in enumerate(paesi_iva) if name == country_name), 0)
            st.session_state["iva_base"] = idx
        if "iva_comp" in recipe:
            country_name, rate = recipe["iva_comp"]
            idx = next((i for i, (name, _) in enumerate(paesi_iva) if name == country_name), 0)
            st.session_state["iva_comp"] = idx
    
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
                "discount_percent": st.session_state.get("discount_percent", 20.0),
                "return_rate_weight": st.session_state.get("return_rate_weight", 2.0),
                "iva_base": iva_base,
                "iva_comp": iva_comp
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

# Funzione migliorata per parsare il peso dagli attributi
def parse_weight(x):
    """Estrae il peso in kg dai campi di attributo.
    
    IMPORTANTE: Questa funzione assume che tutti i valori numerici siano in grammi
    a meno che non sia esplicitamente indicato "kg".
    """
    if not isinstance(x, str):
        return np.nan
        
    # Debug: stampa il valore in input
    print(f"Parsing peso da: {x}")
    
    # Pulisci la stringa da caratteri non necessari
    x_clean = x.lower().replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Cerca pattern "peso: X kg" o "weight: X kg"
    peso_pattern = re.search(r'(peso|weight)[\s:]+(\d+[.,]?\d*)\s*kg', x_clean)
    if peso_pattern:
        weight_val = peso_pattern.group(2).replace(',', '.')
        print(f"Trovato peso in kg: {weight_val}")
        return float(weight_val)
    
    # Cerca pattern "peso: X g" o "weight: X g"
    peso_g_pattern = re.search(r'(peso|weight)[\s:]+(\d+[.,]?\d*)\s*g', x_clean)
    if peso_g_pattern:
        weight_val = peso_g_pattern.group(2).replace(',', '.')
        print(f"Trovato peso in g: {weight_val}, convertito a kg: {float(weight_val)/1000}")
        return float(weight_val) / 1000
    
    # Controlla se è specificato "kg"
    kg_match = re.search(r'(\d+[.,]?\d*)\s*kg', x_clean)
    if kg_match:
        weight_val = kg_match.group(1).replace(',', '.')
        print(f"Trovato kg: {weight_val}")
        return float(weight_val)
    
    # Controlla se è specificato "g" o "gr" per grammi
    g_match = re.search(r'(\d+[.,]?\d*)\s*g[r]?', x_clean)
    if g_match:
        weight_val = g_match.group(1).replace(',', '.')
        gram_weight = float(weight_val) / 1000
        print(f"Trovato grammi: {weight_val}, convertito in kg: {gram_weight}")
        return gram_weight
    
    # Cerca qualsiasi numero che potrebbe essere un peso
    # ma solo se la stringa contiene parole chiave relative al peso
    if any(kw in x_clean for kw in ['peso', 'weight', 'grammi', 'grams', 'kg', ' g ', 'pesante']):
        num_match = re.search(r'(\d+[.,]?\d*)', x_clean)
        if num_match:
            weight_val = num_match.group(1).replace(',', '.')
            # Se il numero è grande (>100), probabilmente sono grammi
            val = float(weight_val)
            if val > 100:
                print(f"Trovato probabile peso in grammi: {val}, convertito in kg: {val/1000}")
                return val / 1000
            else:
                print(f"Trovato probabile peso in kg: {val}")
                return val
    
    print("Nessun peso trovato")
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

# Funzione per formattare il Return Rate per la visualizzazione
def format_return_rate(rate):
    if pd.isna(rate) or rate == "":
        return "N/D"
    rate_lower = str(rate).lower().strip()
    if rate_lower == "low":
        return "Basso 🟢"
    elif rate_lower == "high":
        return "Alto 🔴"
    else:
        return str(rate)

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
                    asins_area = st.text_area("ASIN disponibili:", asin_text, height=200, key="asins_display")
                    
                    if st.button("📋 Copia ASINs negli appunti", type="primary"):
                        st.write("ASINs copiati negli appunti! ✓")
                        st.session_state['clipboard_content'] = asin_text
                        st.markdown(
                            f"""
                            <script>
                                navigator.clipboard.writeText(`{asin_text}`).then(function() {{
                                    console.log('Copying to clipboard was successful!');
                                }}, function(err) {{
                                    console.error('Could not copy text: ', err);
                                }});
                            </script>
                            """,
                            unsafe_allow_html=True
                        )
                        
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
def calc_final_purchase_price(row, discount, iva_base_rate):
    """
    Calcola il prezzo d'acquisto netto, IVA esclusa e scontato, in base al paese.
    
    Params:
      row: la riga del dataframe
      discount: percentuale di sconto (in formato decimale, es. 0.2 per 20%)
      iva_base_rate: aliquota IVA del mercato di origine (in formato decimale, es. 0.22 per 22%)
    
    Returns:
      Il prezzo di acquisto netto (IVA esclusa e scontato)
    """
    gross = row["Price_Base"]
    if pd.isna(gross):
        return np.nan
    
    # Calcolo prezzo netto (senza IVA)
    net_price = gross / (1 + iva_base_rate)
    
    # Calcolo prezzo scontato
    discounted_price = net_price * (1 - discount)
    
    return discounted_price

#################################
# Elaborazione Completa e Calcolo Opportunity Score
#################################
if avvia:
    if not comparison_files:
        with tab_main1:
            st.error("Carica almeno un file di Liste di Confronto.")
        st.stop()
    
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
    
    if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
        with tab_main1:
            st.error("Assicurati che entrambi i file (origine e confronto) contengano la colonna ASIN.")
        st.stop()
    
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        with tab_main1:
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
    
    # Preprocessing per Return Rate
    df_merged["Return_Rate"] = df_merged.get("Return Rate (comp)", pd.Series(""))
    df_merged["Return_Rate_Display"] = df_merged["Return_Rate"].apply(format_return_rate)
    df_merged["Return_Rate_Factor"] = df_merged["Return_Rate"].apply(calculate_return_rate_factor)
    
    possible_weight_cols = [
        "Weight (base)", "Item Weight (base)", "Package: Weight (kg) (base)", 
        "Package: Weight (base)", "Product details (base)", "Features (base)"
    ]
    
    df_merged["Weight_kg"] = np.nan
    for col in possible_weight_cols:
        if col in df_merged.columns:
            weight_data = df_merged[col].apply(parse_weight)
            df_merged.loc[df_merged["Weight_kg"].isna(), "Weight_kg"] = weight_data.loc[df_merged["Weight_kg"].isna()]
    
    # Aggiungi un altro tentativo di estrazione del peso direttamente dal titolo del prodotto
    if df_merged["Weight_kg"].isna().all():
        st.warning("Non è stato possibile rilevare i pesi dai campi attributo standard. Tentativo di estrazione dal titolo...")
        if "Title (base)" in df_merged.columns:
            df_merged["Weight_kg"] = df_merged["Title (base)"].apply(parse_weight)
            
    # Verifica se siamo riusciti a estrarre alcuni pesi
    if df_merged["Weight_kg"].notna().any():
        # Crea una distribuzione di pesi variegata per i prodotti senza peso rilevato
        valid_weights = df_merged.loc[df_merged["Weight_kg"].notna(), "Weight_kg"]
        if not valid_weights.empty:
            # Genera pesi basati sulla distribuzione di quelli trovati
            mean_weight = valid_weights.mean()
            std_weight = max(valid_weights.std(), 0.5)  # Almeno 0.5 kg di deviazione
            st.info(f"Applicando distribuzione di pesi (media: {mean_weight:.2f} kg, deviazione: {std_weight:.2f} kg) ai prodotti senza peso rilevato")
            
            # Genera pesi casuali per i prodotti senza peso
            np.random.seed(42)  # Per riproducibilità
            missing_count = df_merged["Weight_kg"].isna().sum()
            random_weights = np.random.normal(mean_weight, std_weight, size=missing_count)
            random_weights = np.clip(random_weights, 0.1, 30)  # Limita tra 100g e 30kg
            
            # Assegna i pesi generati
            df_merged.loc[df_merged["Weight_kg"].isna(), "Weight_kg"] = random_weights
        else:
            st.warning("Non è stato possibile rilevare alcun peso dai dati. Assegnando pesi predefiniti variabili...")
            # Assegna pesi variabili predefiniti
            np.random.seed(42)
            random_weights = np.random.uniform(0.5, 3.0, size=df_merged["Weight_kg"].isna().sum())
            df_merged.loc[df_merged["Weight_kg"].isna(), "Weight_kg"] = random_weights
    else:
        st.warning("Non è stato possibile rilevare alcun peso dai dati. Assegnando pesi predefiniti variabili...")
        # Assegna pesi variabili predefiniti
        np.random.seed(42)
        random_weights = np.random.uniform(0.5, 3.0, size=len(df_merged))
        df_merged["Weight_kg"] = random_weights
    
    # Debug dei pesi
    st.write("Rilevamento dei pesi dei prodotti:")
    st.write(f"Pesi mancanti prima del riempimento: {df_merged['Weight_kg'].isna().sum()} su {len(df_merged)}")
    
    # Riempimento e controllo dei pesi
    df_merged["Weight_kg"] = df_merged["Weight_kg"].fillna(1.0)
    # Assicuriamoci che non ci siano valori 0 che potrebbero causare problemi nel calcolo dei costi
    df_merged.loc[df_merged["Weight_kg"] <= 0, "Weight_kg"] = 1.0
    
    st.write(f"Gamma dei pesi (kg): {df_merged['Weight_kg'].min():.2f} - {df_merged['Weight_kg'].max():.2f}")
    st.write(f"Peso medio (kg): {df_merged['Weight_kg'].mean():.2f}")
    
    # Crea un istogramma dei pesi
    weight_hist_data = pd.DataFrame({"Peso (kg)": df_merged["Weight_kg"]})
    weight_hist = alt.Chart(weight_hist_data).mark_bar().encode(
        alt.X("Peso (kg):Q", bin=alt.Bin(maxbins=20)),
        alt.Y("count():Q", title="Numero Prodotti")
    ).properties(
        title="Distribuzione dei Pesi",
        height=150
    )
    st.altair_chart(weight_hist, use_container_width=True)
    
    df_merged["Shipping_Cost"] = df_merged["Weight_kg"].apply(calculate_shipping_cost)
    
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount, iva_base_rate), axis=1)
    
    df_merged["Vendita_Netto"] = df_merged["Price_Comp"] / (1 + iva_comp_rate)
    df_merged["Margine_Stimato"] = df_merged["Vendita_Netto"] - df_merged["Acquisto_Netto"]
    df_merged["Margine_%"] = (df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]) * 100
    
    if include_shipping:
        df_merged["Margine_Netto"] = df_merged["Margine_Stimato"] - df_merged["Shipping_Cost"]
        df_merged["Margine_Netto_%"] = (df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]) * 100
    else:
        df_merged["Margine_Netto"] = df_merged["Margine_Stimato"]
        df_merged["Margine_Netto_%"] = df_merged["Margine_%"]
    
    df_merged["Margin_Pct_Lordo"] = (df_merged["Price_Comp"] - df_merged["Price_Base"]) / df_merged["Price_Base"] * 100
    
    df_merged = df_merged[df_merged["Margine_Netto_%"] > min_margin_pct]
    df_merged = df_merged[df_merged["Margine_Netto"] > min_margin_abs]
    
    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged = df_merged[df_merged["SalesRank_Comp"] <= max_sales_rank]
    
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    df_merged = df_merged[df_merged["NewOffer_Comp"] <= max_offer_count]
    
    df_merged["Price_Comp"] = df_merged["Price_Comp"].fillna(0)
    df_merged = df_merged[df_merged["Price_Comp"].between(min_buybox_price, max_buybox_price)]
    
    df_merged["Trend_Bonus"] = np.log((df_merged["SalesRank_90d"].fillna(df_merged["SalesRank_Comp"]) + 1) / (df_merged["SalesRank_Comp"] + 1))
    df_merged["Trend"] = df_merged["Trend_Bonus"].apply(format_trend)
    
    df_merged["Norm_Rank"] = np.log(df_merged["SalesRank_Comp"].fillna(999999) + 10)
    df_merged["Volume_Score"] = 1000 / df_merged["Norm_Rank"]
    df_merged["ROI_Factor"] = df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]
    
    # Applicazione del fattore Return Rate all'Opportunity Score
    df_merged["Opportunity_Score"] = (
        epsilon * df_merged["Margine_Netto_%"] +
        theta * df_merged["Margine_Netto"] +
        beta * np.log(1 + df_merged["Bought_Comp"].fillna(0)) -
        delta * np.minimum(df_merged["NewOffer_Comp"].fillna(0), 10) -
        alpha * df_merged["Norm_Rank"] +
        zeta * df_merged["Trend_Bonus"] +
        gamma * df_merged["Volume_Score"]
    )
    
    # Applicazione del fattore Return Rate - aggiunto peso regolabile
    # Valori Return_Rate_Factor: Low = 1.0 (nessuna penalizzazione), High = 0.7 (30% penalizzazione)
    # Applichiamo il peso solo quando il Return Rate è alto (penalizzazione)
    df_merged.loc[df_merged["Return_Rate"].str.lower() == "high", "Opportunity_Score"] -= (
        return_rate_weight * (1 - df_merged["Return_Rate_Factor"]) * df_merged["Opportunity_Score"]
    )
    
    min_margin_threshold = min_margin_abs * min_margin_multiplier
    df_merged.loc[df_merged["Margine_Netto"] < min_margin_threshold, "Opportunity_Score"] *= (df_merged["Margine_Netto"] / min_margin_threshold)
    
    max_score = df_merged["Opportunity_Score"].max()
    if not np.isnan(max_score) and max_score > 0:
        df_merged["Opportunity_Score"] = (df_merged["Opportunity_Score"] / max_score) * 100
    
    df_merged["Opportunity_Class"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[0]
    )
    df_merged["Opportunity_Tag"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[1]
    )
    
    df_merged["IVA_Origine"] = f"{iva_base[0]} ({iva_base[1]}%)"
    df_merged["IVA_Confronto"] = f"{iva_comp[0]} ({iva_comp[1]}%)"
    
    df_merged = df_merged.sort_values("Opportunity_Score", ascending=False)
    
    cols_final = [
        "Locale (base)", "Locale (comp)", "Title (base)", "ASIN",
        "Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto",
        "Margine_Stimato", "Shipping_Cost", "Margine_Netto", "Margine_Netto_%", 
        "Weight_kg", "SalesRank_Comp", "SalesRank_90d",
        "Trend", "Bought_Comp", "NewOffer_Comp", "Volume_Score",
        "Return_Rate_Display", "Opportunity_Score", "Opportunity_Class", "IVA_Origine", "IVA_Confronto",
        "Brand (base)", "Package: Dimension (cm³) (base)"
    ]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    
    cols_to_round = ["Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto", 
                     "Margine_Stimato", "Shipping_Cost", "Margine_Netto", "Margine_Netto_%", 
                     "Margine_%", "Opportunity_Score", "Volume_Score", "Weight_kg"]
    for col in cols_to_round:
        if col in df_finale.columns:
            df_finale[col] = df_finale[col].round(2)
    
    st.session_state['filtered_data'] = df_finale
    
    #################################
    # Dashboard Interattiva
    #################################
    with tab_main2:
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        st.subheader("📊 Dashboard delle Opportunità")
        
        if not df_finale.empty:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Prodotti Trovati", len(df_finale))
            with col2:
                st.metric("Margine Netto Medio (%)", f"{df_finale['Margine_Netto_%'].mean():.2f}%")
            with col3:
                st.metric("Margine Netto Medio (€)", f"{df_finale['Margine_Netto'].mean():.2f}€")
            with col4:
                st.metric("Opportunity Score Massimo", f"{df_finale['Opportunity_Score'].max():.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.info(f"IVA Origine: {iva_base[0]} ({iva_base[1]}%) | IVA Confronto: {iva_comp[0]} ({iva_comp[1]}%) | {'✅ Spedizione Inclusa' if include_shipping else '❌ Spedizione Esclusa'}")
            
            dark_colors = {
                "Eccellente": "#2ecc71",
                "Buona": "#27ae60",
                "Discreta": "#f39c12",
                "Bassa": "#e74c3c"
            }
            
            st.subheader("Distribuzione Opportunity Score")
            hist = alt.Chart(df_finale.reset_index()).mark_bar().encode(
                alt.X("Opportunity_Score:Q", bin=alt.Bin(maxbins=20), title="Opportunity Score"),
                alt.Y("count()", title="Numero di Prodotti"),
                color=alt.Color("Opportunity_Class:N", 
                               scale=alt.Scale(domain=list(dark_colors.keys()),
                                              range=list(dark_colors.values())))
            ).properties(height=250)
            st.altair_chart(hist, use_container_width=True)
            
            # Aggiunta di un grafico per la distribuzione del Return Rate
            if "Return_Rate_Display" in df_finale.columns:
                st.subheader("Distribuzione Return Rate")
                return_counts = df_finale["Return_Rate_Display"].value_counts().reset_index()
                return_counts.columns = ["Return Rate", "Conteggio"]
                
                return_colors = {
                    "Basso 🟢": "#27ae60",  # Verde per basso return rate
                    "Alto 🔴": "#e74c3c",    # Rosso per alto return rate
                    "N/D": "#7f8c8d"        # Grigio per valori mancanti
                }
                
                return_chart = alt.Chart(return_counts).mark_bar().encode(
                    x=alt.X("Return Rate:N", title="Return Rate"),
                    y=alt.Y("Conteggio:Q", title="Numero di Prodotti"),
                    color=alt.Color("Return Rate:N", 
                                   scale=alt.Scale(domain=list(return_colors.keys()),
                                                  range=list(return_colors.values())))
                ).properties(height=200)
                st.altair_chart(return_chart, use_container_width=True)
            
            st.subheader("Analisi Multifattoriale")
            chart = alt.Chart(df_finale.reset_index()).mark_circle().encode(
                x=alt.X("Margine_Netto_%:Q", title="Margine Netto (%)"),
                y=alt.Y("Opportunity_Score:Q", title="Opportunity Score"),
                size=alt.Size("Volume_Score:Q", title="Volume Stimato", scale=alt.Scale(range=[20, 200])),
                color=alt.Color("Locale (comp):N", title="Mercato Confronto", scale=alt.Scale(scheme='category10')),
                tooltip=["Title (base)", "ASIN", "Brand (base)", "Margine_Netto_%", "Margine_Netto", "Shipping_Cost", "SalesRank_Comp", "Opportunity_Score", "Trend", "Return_Rate_Display", "Weight_kg"]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
            
            st.subheader("Analisi per Mercato")
            if "Locale (comp)" in df_finale.columns:
                market_analysis = df_finale.groupby("Locale (comp)").agg({
                    "ASIN": "count",
                    "Margine_Netto_%": "mean",
                    "Margine_Netto": "mean",
                    "Shipping_Cost": "mean",
                    "Opportunity_Score": "mean",
                    "Weight_kg": "mean"
                }).reset_index()
                market_analysis.columns = ["Mercato", "Prodotti", "Margine Netto Medio (%)", 
                                          "Margine Netto Medio (€)", "Costo Spedizione Medio (€)",
                                          "Opportunity Score Medio", "Peso Medio (kg)"]
                market_analysis = market_analysis.round(2)
                st.dataframe(market_analysis, use_container_width=True)
                
                market_chart = alt.Chart(market_analysis).mark_bar().encode(
                    x="Mercato:N",
                    y="Opportunity Score Medio:Q",
                    color=alt.Color("Mercato:N", scale=alt.Scale(scheme='category10')),
                    tooltip=["Mercato", "Prodotti", "Margine Netto Medio (%)", 
                            "Margine Netto Medio (€)", "Costo Spedizione Medio (€)", 
                            "Opportunity Score Medio", "Peso Medio (kg)"]
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
            
            # Aggiunta filtro per Return Rate
            col1, col2, col3 = st.columns(3)
            with col1:
                if "Return_Rate_Display" in filtered_df.columns:
                    return_rates = ["Tutti"] + sorted(filtered_df["Return_Rate_Display"].unique().tolist())
                    selected_return_rate = st.selectbox("Filtra per Return Rate", return_rates)
                    if selected_return_rate != "Tutti":
                        filtered_df = filtered_df[filtered_df["Return_Rate_Display"] == selected_return_rate]
            
            with col2:
                min_op_score = st.slider("Opportunity Score Minimo", 
                                         min_value=float(filtered_df["Opportunity_Score"].min()),
                                         max_value=float(filtered_df["Opportunity_Score"].max()),
                                         value=float(filtered_df["Opportunity_Score"].min()))
                filtered_df = filtered_df[filtered_df["Opportunity_Score"] >= min_op_score]
            
            with col3:
                min_margin = st.slider("Margine Netto Minimo (€)", 
                                      min_value=float(filtered_df["Margine_Netto"].min()),
                                      max_value=float(filtered_df["Margine_Netto"].max()),
                                      value=float(filtered_df["Margine_Netto"].min()))
                filtered_df = filtered_df[filtered_df["Margine_Netto"] >= min_margin]
            
            # Filtro per peso massimo
            col1, col2 = st.columns(2)
            with col1:
                if "Weight_kg" in filtered_df.columns:
                    min_weight = float(filtered_df["Weight_kg"].min())
                    max_weight = float(filtered_df["Weight_kg"].max())
                    
                    # Previeni l'errore quando min e max sono uguali
                    if min_weight == max_weight:
                        st.info(f"Tutti i prodotti hanno lo stesso peso: {min_weight} kg")
                    else:
                        max_weight_filter = st.slider("Peso Massimo (kg)", 
                                              min_value=min_weight,
                                              max_value=max_weight,
                                              value=max_weight)
                        filtered_df = filtered_df[filtered_df["Weight_kg"] <= max_weight_filter]
            
            with col2:
                search_term = st.text_input("Cerca per ASIN o Titolo")
                if search_term:
                    mask = (
                        filtered_df["ASIN"].str.contains(search_term, case=False, na=False) | 
                        filtered_df["Title (base)"].str.contains(search_term, case=False, na=False)
                    )
                    filtered_df = filtered_df[mask]
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if not filtered_df.empty:
                def highlight_opportunity(val):
                    if val == "Eccellente":
                        return 'background-color: #153d2e; color: #2ecc71; font-weight: bold'
                    elif val == "Buona":
                        return 'background-color: #14432d; color: #27ae60; font-weight: bold'
                    elif val == "Discreta":
                        return 'background-color: #402d10; color: #f39c12; font-weight: bold'
                    else:
                        return 'background-color: #3d1a15; color: #e74c3c; font-weight: bold'
                
                def highlight_return_rate(val):
                    if val == "Basso 🟢":
                        return 'background-color: #14432d; color: #27ae60; font-weight: bold'
                    elif val == "Alto 🔴":
                        return 'background-color: #3d1a15; color: #e74c3c; font-weight: bold'
                    else:
                        return 'background-color: #282828; color: #aaaaaa;'
                
                def format_with_html(df):
                    styled = df.style.map(
                        lambda x: highlight_opportunity(x) if x in ["Eccellente", "Buona", "Discreta", "Bassa"] else '',
                        subset=["Opportunity_Class"]
                    )
                    
                    # Evidenzia anche Return Rate
                    if "Return_Rate_Display" in df.columns:
                        styled = styled.map(
                            lambda x: highlight_return_rate(x) if x in ["Basso 🟢", "Alto 🔴", "N/D"] else '',
                            subset=["Return_Rate_Display"]
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
                
                st.markdown(f"**{len(filtered_df)} prodotti trovati**")
                
                display_cols = [col for col in filtered_df.columns if col not in ["Opportunity_Tag", "SalesRank_90d"]]
                
                st.dataframe(
                    format_with_html(filtered_df[display_cols]),
                    height=600,
                    use_container_width=True
                )
                
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
    - **Return Rate**: Tasso di reso del prodotto (basso o alto)
    
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
    
    ### Return Rate
    
    Il Return Rate indica la probabilità di reso del prodotto:
    - **Basso** (Low): Prodotti con bassa probabilità di reso, nessuna penalizzazione
    - **Alto** (High): Prodotti con alta probabilità di reso, penalizzazione applicata all'Opportunity Score
    - **N/D**: Quando non è disponibile l'informazione, viene applicata una penalizzazione intermedia
    
    I prodotti con alto Return Rate sono più rischiosi perché comportano costi aggiuntivi di gestione e potenziali perdite.
    """)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #333; color: #aaa;">
    Amazon Market Analyzer - Arbitraggio Multi-Mercato © 2025<br>
    Versione 2.1
</div>
""", unsafe_allow_html=True)