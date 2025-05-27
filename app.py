import streamlit as st

# QUESTO DEVE ESSERE IL PRIMO COMANDO STREAMLIT
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INIZIO COSTANTI PER NOMI COLONNE ---
COL_ASIN = "ASIN"
COL_BRAND_BASE = "Brand (base)"
COL_LOCALE_BASE = "Locale (base)"
COL_LOCALE_COMP = "Locale (comp)"
COL_TITLE_BASE = "Title (base)"
COL_PACKAGE_DIMENSION_BASE = "Package: Dimension (cm³) (base)"

# Colonne di input per i prezzi (esempi, i nomi completi sono costruiti dinamicamente)
# REF_PRICE_BUYBOX = "Buy Box: Current"
# REF_PRICE_AMAZON = "Amazon: Current"
# REF_PRICE_NEW = "New: Current"

COL_SALES_RANK_CURRENT_COMP = "Sales Rank: Current (comp)"
COL_BOUGHT_PAST_MONTH_COMP = "Bought in past month (comp)"
COL_NEW_OFFER_COUNT_COMP = "New Offer Count: Current (comp)"
COL_SALES_RANK_90D_AVG_COMP = "Sales Rank: 90 days avg. (comp)"

# Colonne per il peso (esempi)
COL_WEIGHT_BASE = "Weight (base)"
COL_ITEM_WEIGHT_BASE = "Item Weight (base)"
COL_PACKAGE_WEIGHT_KG_BASE = "Package: Weight (kg) (base)"
COL_PRODUCT_DETAILS_BASE = "Product details (base)"
COL_FEATURES_BASE = "Features (base)"

# Colonne calcolate internamente
COL_PRICE_BASE = "Price_Base"
COL_PRICE_COMP = "Price_Comp"
COL_SALES_RANK_COMP = "SalesRank_Comp"
COL_BOUGHT_COMP = "Bought_Comp"
COL_NEW_OFFER_COMP = "NewOffer_Comp"
COL_SALES_RANK_90D = "SalesRank_90d"
COL_WEIGHT_KG = "Weight_kg"
COL_SHIPPING_COST = "Shipping_Cost"
COL_ACQUISTO_NETTO = "Acquisto_Netto"
COL_VENDITA_NETTO = "Vendita_Netto"
COL_MARGINE_STIMATO = "Margine_Stimato"
COL_MARGINE_PERCENT = "Margine_%"
COL_MARGINE_NETTO = "Margine_Netto"
COL_MARGINE_NETTO_PERCENT = "Margine_Netto_%"
COL_TREND_BONUS = "Trend_Bonus"
COL_TREND = "Trend"
COL_NORM_RANK = "Norm_Rank"
COL_VOLUME_SCORE = "Volume_Score"
# COL_ROI_FACTOR = "ROI_Factor" # Non usata direttamente nell'opportunity score finale ma calcolata
COL_OPPORTUNITY_SCORE = "Opportunity_Score"
COL_OPPORTUNITY_CLASS = "Opportunity_Class"
COL_OPPORTUNITY_TAG = "Opportunity_Tag" # Non usata per visualizzazione tabella, ma per grafici sì
COL_IVA_ORIGINE = "IVA_Origine"
COL_IVA_CONFRONTO = "IVA_Confronto"
# --- FINE COSTANTI PER NOMI COLONNE ---

# Ora possiamo importare altri moduli
import pandas as pd
import numpy as np
import re
import altair as alt
import io
from streamlit_extras.colored_header import colored_header
# from streamlit_extras.metric_cards import style_metric_cards # Non usato, CSS personalizzato gestisce le metriche

# Funzione per caricare CSS locale
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"File CSS '{file_name}' non trovato. Assicurati che sia nella stessa directory dello script.")

# Applica CSS personalizzato da file esterno
local_css("style.css")


st.markdown("""
<!-- Elementi extra UI -->
<div id="copy-notification">ASINs copiati negli appunti! ✓</div>

<!-- Script per la copia negli appunti -->
<script>
function copyASINsToClipboard() {
    const asinsText = document.getElementById('asins-content').value;
    if (!asinsText) {
        alert('Nessun ASIN da copiare.');
        return;
    }
    navigator.clipboard.writeText(asinsText)
        .then(() => {
            const notification = document.getElementById('copy-notification');
            notification.classList.add('show-notification');
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

# Definizione del listino costi di spedizione (Italia) - reso un parametro per le funzioni
SHIPPING_COSTS_IT = {
    3: 5.14, 4: 6.41, 5: 6.95, 10: 8.54, 25: 12.51, 50: 21.66, 100: 34.16
}

# Funzione per calcolare il costo di spedizione in base al peso
def calculate_shipping_cost(weight_kg, shipping_rates):
    if pd.isna(weight_kg) or weight_kg <= 0:
        return 0.0
    for weight_limit, cost in sorted(shipping_rates.items()):
        if weight_kg <= weight_limit:
            return cost
    return shipping_rates.get(max(shipping_rates.keys()), 0.0) # Costo massimo o 0 se vuoto


#################################
# Sidebar: Caricamento file, Prezzo di riferimento, Sconto, Impostazioni e Ricette
#################################
with st.sidebar:
    colored_header(label="🔄 Caricamento Dati", description="Carica i file dei mercati", color_name="blue-70")
    
    files_base_uploaded = st.file_uploader(
        "Lista di Origine (Mercato Base)", type=["csv", "xlsx"], accept_multiple_files=True
    )
    comparison_files_uploaded = st.file_uploader(
        "Liste di Confronto (Mercati di Confronto)", type=["csv", "xlsx"], accept_multiple_files=True
    )

    colored_header(label="💰 Impostazioni Prezzi", description="Configurazione prezzi", color_name="blue-70")
    ref_price_base_option = st.selectbox(
        "Per la Lista di Origine", ["Buy Box: Current", "Amazon: Current", "New: Current"], key="ref_price_base_key"
    )
    ref_price_comp_option = st.selectbox(
        "Per la Lista di Confronto", ["Buy Box: Current", "Amazon: Current", "New: Current"], key="ref_price_comp_key"
    )

    colored_header(label="🏷️ Sconto & IVA", description="Parametri finanziari", color_name="blue-70")
    discount_percent_val = st.number_input("Sconto sugli acquisti (%)", min_value=0.0, value=st.session_state.get("discount_percent", 20.0), step=0.1, key="discount_percent")
    
    st.markdown("**IVA per calcolo del margine**")
    paesi_iva = [("Italia", 22), ("Germania", 19), ("Francia", 20), ("Spagna", 21), ("Regno Unito", 20)]
    
    col1_sidebar, col2_sidebar = st.columns(2)
    with col1_sidebar:
        st.markdown("**Mercato Origine**")
        iva_base_tuple = st.selectbox("IVA mercato origine", paesi_iva, format_func=lambda x: f"{x[0]} ({x[1]}%)", key="iva_base")
    with col2_sidebar:
        st.markdown("**Mercato Confronto**")
        iva_comp_tuple = st.selectbox("IVA mercato confronto", paesi_iva, format_func=lambda x: f"{x[0]} ({x[1]}%)", key="iva_comp")

    colored_header(label="🚚 Spedizione", description="Calcolo costi di spedizione", color_name="blue-70")
    st.markdown('<div class="shipping-card">', unsafe_allow_html=True)
    st.markdown('<div class="shipping-title">📦 Listino Costi di Spedizione (Italia)</div>', unsafe_allow_html=True)
    shipping_table_data = [{"Peso (kg)": f"Fino a {k}", "Costo (€)": v} for k, v in SHIPPING_COSTS_IT.items()]
    st.dataframe(pd.DataFrame(shipping_table_data), hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    include_shipping_calc = st.checkbox("Calcola margine netto con spedizione", value=True, key="include_shipping_key")
    
    colored_header(label="📈 Opportunity Score", description="Pesi e parametri", color_name="blue-70")
    tab1_score, tab2_score = st.tabs(["Parametri Base", "Parametri Avanzati"])
    with tab1_score:
        alpha_val = st.slider("Peso per Sales Rank (penalità)", 0.0, 5.0, st.session_state.get("alpha", 1.0), step=0.1, key="alpha", help="Un valore più alto penalizza maggiormente i prodotti con Sales Rank elevato.")
        beta_val = st.slider("Peso per 'Bought in past month'", 0.0, 5.0, st.session_state.get("beta", 1.0), step=0.1, key="beta", help="Un valore più alto premia i prodotti con più acquisti recenti.")
        delta_val = st.slider("Peso penalizzante per Offer Count", 0.0, 5.0, st.session_state.get("delta", 1.0), step=0.1, key="delta", help="Un valore più alto penalizza maggiormente i prodotti con molte offerte (alta competizione).")
        epsilon_val = st.slider("Peso per il Margine (%)", 0.0, 10.0, st.session_state.get("epsilon", 3.0), step=0.1, key="epsilon", help="Un valore più alto dà più importanza al margine percentuale.")
        zeta_val = st.slider("Peso per Trend Sales Rank", 0.0, 5.0, st.session_state.get("zeta", 1.0), step=0.1, key="zeta", help="Un valore più alto premia i prodotti con un trend di Sales Rank in miglioramento.")
    with tab2_score:
        gamma_val = st.slider("Peso per volume di vendita", 0.0, 5.0, st.session_state.get("gamma", 2.0), step=0.1, key="gamma", help="Un valore più alto premia prodotti con stima di volume vendite più alto (derivato da Sales Rank).")
        theta_val = st.slider("Peso per margine assoluto (€)", 0.0, 5.0, st.session_state.get("theta", 1.5), step=0.1, key="theta", help="Un valore più alto dà più importanza al margine assoluto in valuta.")
        min_margin_multiplier_val = st.slider("Moltiplicatore margine minimo", 1.0, 3.0, st.session_state.get("min_margin_multiplier", 1.2), step=0.1, key="min_margin_multiplier", help="Usato per penalizzare ulteriormente gli score di prodotti con margini assoluti molto bassi.")
    
    colored_header(label="🔍 Filtri Avanzati", description="Limita i risultati", color_name="blue-70")
    max_sales_rank_val = st.number_input("Sales Rank massimo", min_value=1, value=st.session_state.get("max_sales_rank", 999999), key="max_sales_rank")
    max_offer_count_val = st.number_input("Offer Count massimo", min_value=1, value=st.session_state.get("max_offer_count", 30), key="max_offer_count")
    min_buybox_price_val = st.number_input("Prezzo minimo (€)", min_value=0.0, value=st.session_state.get("min_buybox_price", 15.0), key="min_buybox_price")
    max_buybox_price_val = st.number_input("Prezzo massimo (€)", min_value=0.0, value=st.session_state.get("max_buybox_price", 200.0), key="max_buybox_price")
    min_margin_pct_val = st.number_input("Margine netto minimo (%)", min_value=0.0, value=st.session_state.get("min_margin_pct", 15.0), key="min_margin_pct")
    min_margin_abs_val = st.number_input("Margine netto minimo (€)", min_value=0.0, value=st.session_state.get("min_margin_abs", 5.0), key="min_margin_abs")
    
    colored_header(label="📋 Ricette", description="Salva e carica configurazioni", color_name="blue-70")
    recipe_options = ["-- Nessuna --"] + list(st.session_state.get('recipes', {}).keys())
    selected_recipe_name = st.selectbox("Carica Ricetta", options=recipe_options)

    if selected_recipe_name != "-- Nessuna --" and selected_recipe_name in st.session_state.get('recipes', {}):
        recipe = st.session_state['recipes'][selected_recipe_name]
        # Sovrascrivi i valori in session_state con quelli della ricetta
        # Questo aggiornerà i widget al prossimo rerun (che Streamlit farà)
        for key, default_value in [
            ("alpha", 1.0), ("beta", 1.0), ("delta", 1.0), ("epsilon", 3.0), ("zeta", 1.0),
            ("gamma", 2.0), ("theta", 1.5), ("min_margin_multiplier", 1.2),
            ("discount_percent", 20.0), ("max_sales_rank", 999999),
            ("max_offer_count", 30), ("min_buybox_price", 15.0), ("max_buybox_price", 200.0),
            ("min_margin_pct", 15.0), ("min_margin_abs", 5.0)
        ]:
            st.session_state[key] = recipe.get(key, st.session_state.get(key, default_value))

        # Gestione IVA
        loaded_iva_base = recipe.get("iva_base")
        if loaded_iva_base and loaded_iva_base in paesi_iva:
            st.session_state.iva_base = loaded_iva_base
        elif loaded_iva_base:
            st.warning(f"IVA origine salvata ({loaded_iva_base}) non valida. Mantenuta selezione corrente o default.")

        loaded_iva_comp = recipe.get("iva_comp")
        if loaded_iva_comp and loaded_iva_comp in paesi_iva:
            st.session_state.iva_comp = loaded_iva_comp
        elif loaded_iva_comp:
            st.warning(f"IVA confronto salvata ({loaded_iva_comp}) non valida. Mantenuta selezione corrente o default.")
        
        # Forzare un rerun per applicare i valori ai widget se non lo fa automaticamente
        # st.experimental_rerun() # Usare con cautela, di solito non serve se i key sono usati correttamente

    new_recipe_name_val = st.text_input("Nome Nuova Ricetta")
    if st.button("💾 Salva Ricetta"):
        if new_recipe_name_val:
            st.session_state['recipes'][new_recipe_name_val] = {
                "alpha": alpha_val, "beta": beta_val, "delta": delta_val, "epsilon": epsilon_val,
                "zeta": zeta_val, "gamma": gamma_val, "theta": theta_val,
                "min_margin_multiplier": min_margin_multiplier_val,
                "discount_percent": discount_percent_val,
                "iva_base": iva_base_tuple, "iva_comp": iva_comp_tuple,
                "max_sales_rank": max_sales_rank_val, "max_offer_count": max_offer_count_val,
                "min_buybox_price": min_buybox_price_val, "max_buybox_price": max_buybox_price_val,
                "min_margin_pct": min_margin_pct_val, "min_margin_abs": min_margin_abs_val
            }
            st.success(f"Ricetta '{new_recipe_name_val}' salvata!")
            selected_recipe_name = new_recipe_name_val # Aggiorna il selectbox alla ricetta appena salvata
            st.experimental_rerun() # Rerun per aggiornare la lista delle ricette e la selezione
        else:
            st.error("Inserisci un nome valido per la ricetta.")

    st.markdown("---")
    avvia_button = st.button("🚀 Calcola Opportunity Score", use_container_width=True)

#################################
# Funzioni di Helper (Parsing, Calcoli)
#################################
def load_data_from_file(uploaded_file_obj):
    if not uploaded_file_obj: return None
    fname = uploaded_file_obj.name.lower()
    try:
        if fname.endswith(".xlsx"):
            return pd.read_excel(uploaded_file_obj, dtype=str)
        elif fname.endswith(".csv"):
            # Prova con ; poi con ,
            try:
                return pd.read_csv(uploaded_file_obj, sep=";", dtype=str)
            except pd.errors.ParserError:
                uploaded_file_obj.seek(0)
                return pd.read_csv(uploaded_file_obj, sep=",", dtype=str)
        else:
            st.warning(f"Formato file non supportato: {fname}")
            return None
    except Exception as e:
        st.error(f"Errore nel caricamento del file {fname}: {e}")
        return None

def parse_float_val(x):
    if not isinstance(x, str): return np.nan
    x_clean = x.replace("€", "").replace(",", ".").strip()
    try: return float(x_clean)
    except: return np.nan

def parse_int_val(x):
    if not isinstance(x, str): return np.nan
    try: return int(x.strip())
    except: return np.nan

def parse_weight_val(x):
    if not isinstance(x, str): return np.nan
    kg_match = re.search(r'(\d+\.?\d*)\s*kg', x.lower())
    g_match = re.search(r'(\d+\.?\d*)\s*g', x.lower())
    if kg_match: return float(kg_match.group(1))
    if g_match: return float(g_match.group(1)) / 1000
    return np.nan

def format_trend_display(trend_bonus_val):
    if pd.isna(trend_bonus_val): return "N/D"
    if trend_bonus_val > 0.1: return "🔼 Crescente"
    if trend_bonus_val < -0.1: return "🔽 Decrescente"
    return "➖ Stabile"

def classify_opportunity_display(score_val):
    if score_val > 100: return "Eccellente", "success-tag" # Teoricamente normalizzato a 100 max
    if score_val > 75: return "Eccellente", "success-tag" # Soglie aggiustate per la normalizzazione
    elif score_val > 50: return "Buona", "success-tag"
    elif score_val > 20: return "Discreta", "warning-tag"
    return "Bassa", "danger-tag"

def calc_final_purchase_price_val(price_base_val, discount_rate, iva_base_rate_val):
    if pd.isna(price_base_val): return np.nan
    net_price = price_base_val / (1 + iva_base_rate_val)
    return net_price * (1 - discount_rate)

#################################
# Funzioni di Elaborazione Principale
#################################
def load_and_validate_datasets(uploaded_base_files, uploaded_comp_files):
    if not uploaded_base_files:
        st.error("🚨 Carica almeno un file per la Lista di Origine.")
        return None, None
    
    base_dfs = [load_data_from_file(f) for f in uploaded_base_files]
    base_dfs = [df for df in base_dfs if df is not None and not df.empty]
    if not base_dfs:
        st.error("🚨 Nessun dato valido trovato nei file della Lista di Origine.")
        return None, None
    df_base_full = pd.concat(base_dfs, ignore_index=True)
    if COL_ASIN not in df_base_full.columns:
        st.error(f"🚨 La colonna '{COL_ASIN}' manca nei file della Lista di Origine.")
        return None, None

    if not uploaded_comp_files:
        st.error("🚨 Carica almeno un file per le Liste di Confronto.")
        return df_base_full, None
        
    comp_dfs = [load_data_from_file(f) for f in uploaded_comp_files]
    comp_dfs = [df for df in comp_dfs if df is not None and not df.empty]
    if not comp_dfs:
        st.error("🚨 Nessun dato valido trovato nei file delle Liste di Confronto.")
        return df_base_full, None
    df_comp_full = pd.concat(comp_dfs, ignore_index=True)
    if COL_ASIN not in df_comp_full.columns:
        st.error(f"🚨 La colonna '{COL_ASIN}' manca nei file delle Liste di Confronto.")
        return df_base_full, None
        
    return df_base_full, df_comp_full

def merge_and_parse_base_data(df_base_data, df_comp_data, ref_price_base_col, ref_price_comp_col):
    df_merged = pd.merge(df_base_data, df_comp_data, on=COL_ASIN, how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        st.info("Nessuna corrispondenza ASIN trovata tra Lista di Origine e Liste di Confronto.")
        return None

    df_merged[COL_PRICE_BASE] = df_merged.get(f"{ref_price_base_col} (base)", pd.Series(dtype='float64')).apply(parse_float_val)
    df_merged[COL_PRICE_COMP] = df_merged.get(f"{ref_price_comp_col} (comp)", pd.Series(dtype='float64')).apply(parse_float_val)
    
    df_merged[COL_SALES_RANK_COMP] = df_merged.get(COL_SALES_RANK_CURRENT_COMP, pd.Series(dtype='float64')).apply(parse_int_val)
    df_merged[COL_BOUGHT_COMP] = df_merged.get(COL_BOUGHT_PAST_MONTH_COMP, pd.Series(dtype='float64')).apply(parse_int_val)
    df_merged[COL_NEW_OFFER_COMP] = df_merged.get(COL_NEW_OFFER_COUNT_COMP, pd.Series(dtype='float64')).apply(parse_int_val)
    df_merged[COL_SALES_RANK_90D] = df_merged.get(COL_SALES_RANK_90D_AVG_COMP, pd.Series(dtype='float64')).apply(parse_int_val)

    df_merged[COL_WEIGHT_KG] = np.nan
    possible_weight_cols_list = [COL_WEIGHT_BASE, COL_ITEM_WEIGHT_BASE, COL_PACKAGE_WEIGHT_KG_BASE, COL_PRODUCT_DETAILS_BASE, COL_FEATURES_BASE]
    for col in possible_weight_cols_list:
        if col in df_merged.columns:
            weight_data = df_merged[col].apply(parse_weight_val)
            df_merged[COL_WEIGHT_KG] = df_merged[COL_WEIGHT_KG].fillna(weight_data)
    df_merged[COL_WEIGHT_KG] = df_merged[COL_WEIGHT_KG].fillna(1.0) # Default 1kg
    return df_merged

def calculate_financial_metrics(df, discount_val, iva_base_rate_val, iva_comp_rate_val, include_shipping, shipping_cost_rates):
    df_calc = df.copy()
    df_calc[COL_SHIPPING_COST] = df_calc[COL_WEIGHT_KG].apply(lambda w: calculate_shipping_cost(w, shipping_cost_rates))
    
    # Uso di .loc per assegnare nuove colonne per evitare SettingWithCopyWarning
    df_calc.loc[:, COL_ACQUISTO_NETTO] = df_calc.apply(
        lambda row: calc_final_purchase_price_val(row[COL_PRICE_BASE], discount_val, iva_base_rate_val), axis=1
    )
    df_calc.loc[:, COL_VENDITA_NETTO] = df_calc[COL_PRICE_COMP] / (1 + iva_comp_rate_val)
    df_calc.loc[:, COL_MARGINE_STIMATO] = df_calc[COL_VENDITA_NETTO] - df_calc[COL_ACQUISTO_NETTO]
    
    # Evita divisione per zero o NaN in Acquisto_Netto per Margine_%
    df_calc.loc[:, COL_MARGINE_PERCENT] = np.where(
        (df_calc[COL_ACQUISTO_NETTO].notna()) & (df_calc[COL_ACQUISTO_NETTO] != 0),
        (df_calc[COL_MARGINE_STIMATO] / df_calc[COL_ACQUISTO_NETTO]) * 100,
        np.nan
    )

    if include_shipping:
        df_calc.loc[:, COL_MARGINE_NETTO] = df_calc[COL_MARGINE_STIMATO] - df_calc[COL_SHIPPING_COST]
        df_calc.loc[:, COL_MARGINE_NETTO_PERCENT] = np.where(
             (df_calc[COL_ACQUISTO_NETTO].notna()) & (df_calc[COL_ACQUISTO_NETTO] != 0),
            (df_calc[COL_MARGINE_NETTO] / df_calc[COL_ACQUISTO_NETTO]) * 100,
            np.nan
        )
    else:
        df_calc.loc[:, COL_MARGINE_NETTO] = df_calc[COL_MARGINE_STIMATO]
        df_calc.loc[:, COL_MARGINE_NETTO_PERCENT] = df_calc[COL_MARGINE_PERCENT]
    return df_calc

def apply_filters_and_calc_score(df, filters, score_params):
    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered[COL_MARGINE_NETTO_PERCENT].fillna(-1) > filters["min_margin_pct"]]
    df_filtered = df_filtered[df_filtered[COL_MARGINE_NETTO].fillna(-1) > filters["min_margin_abs"]]
    
    df_filtered[COL_SALES_RANK_COMP] = df_filtered[COL_SALES_RANK_COMP].fillna(9999999) # Alto valore per NaN
    df_filtered = df_filtered[df_filtered[COL_SALES_RANK_COMP] <= filters["max_sales_rank"]]
    
    df_filtered[COL_NEW_OFFER_COMP] = df_filtered[COL_NEW_OFFER_COMP].fillna(0)
    df_filtered = df_filtered[df_filtered[COL_NEW_OFFER_COMP] <= filters["max_offer_count"]]
    
    df_filtered[COL_PRICE_COMP] = df_filtered[COL_PRICE_COMP].fillna(0)
    df_filtered = df_filtered[
        df_filtered[COL_PRICE_COMP].between(filters["min_buybox_price"], filters["max_buybox_price"])
    ]

    if df_filtered.empty: return df_filtered

    # Calcoli per Opportunity Score
    df_filtered[COL_TREND_BONUS] = np.log(
        (df_filtered[COL_SALES_RANK_90D].fillna(df_filtered[COL_SALES_RANK_COMP]) + 1) / 
        (df_filtered[COL_SALES_RANK_COMP] + 1)
    )
    df_filtered[COL_TREND] = df_filtered[COL_TREND_BONUS].apply(format_trend_display)
    df_filtered[COL_NORM_RANK] = np.log(df_filtered[COL_SALES_RANK_COMP] + 10) # +10 evita log di num piccoli
    df_filtered[COL_VOLUME_SCORE] = 1000 / df_filtered[COL_NORM_RANK]
    
    # df_filtered[COL_ROI_FACTOR] = df_filtered[COL_MARGINE_NETTO] / df_filtered[COL_ACQUISTO_NETTO] # Non usato direttamente nello score

    df_filtered[COL_OPPORTUNITY_SCORE] = (
        score_params["epsilon"] * df_filtered[COL_MARGINE_NETTO_PERCENT].fillna(0) +
        score_params["theta"] * df_filtered[COL_MARGINE_NETTO].fillna(0) +
        score_params["beta"] * np.log(1 + df_filtered[COL_BOUGHT_COMP].fillna(0)) -
        score_params["delta"] * np.minimum(df_filtered[COL_NEW_OFFER_COMP].fillna(0), 10) - # Penalità limitata
        score_params["alpha"] * df_filtered[COL_NORM_RANK] +
        score_params["zeta"] * df_filtered[COL_TREND_BONUS].fillna(0) +
        score_params["gamma"] * df_filtered[COL_VOLUME_SCORE].fillna(0)
    )
    
    min_margin_threshold = filters["min_margin_abs"] * score_params["min_margin_multiplier"]
    df_filtered.loc[df_filtered[COL_MARGINE_NETTO] < min_margin_threshold, COL_OPPORTUNITY_SCORE] *= \
        (df_filtered[COL_MARGINE_NETTO] / min_margin_threshold)

    max_score = df_filtered[COL_OPPORTUNITY_SCORE].max()
    min_score = df_filtered[COL_OPPORTUNITY_SCORE].min()

    if not df_filtered.empty and max_score > min_score : # Evita divisione per zero se tutti gli score sono uguali
         # Normalizzazione a 0-100 (o quasi, se ci sono negativi)
        df_filtered[COL_OPPORTUNITY_SCORE] = 100 * (df_filtered[COL_OPPORTUNITY_SCORE] - min_score) / (max_score - min_score)
    elif not df_filtered.empty: # Tutti gli score sono uguali (o c'è un solo prodotto)
        df_filtered[COL_OPPORTUNITY_SCORE] = 50 # Assegna un punteggio medio

    df_filtered[COL_OPPORTUNITY_SCORE] = df_filtered[COL_OPPORTUNITY_SCORE].fillna(0) # Punteggio 0 per NaN residui

    opportunity_class_tag = df_filtered[COL_OPPORTUNITY_SCORE].apply(classify_opportunity_display)
    df_filtered[COL_OPPORTUNITY_CLASS] = [item[0] for item in opportunity_class_tag]
    df_filtered[COL_OPPORTUNITY_TAG] = [item[1] for item in opportunity_class_tag]
    
    return df_filtered

def prepare_final_display_df(df_processed, iva_base_info_str, iva_comp_info_str):
    if df_processed is None or df_processed.empty:
        return pd.DataFrame()

    df_final = df_processed.copy()
    df_final[COL_IVA_ORIGINE] = iva_base_info_str
    df_final[COL_IVA_CONFRONTO] = iva_comp_info_str
    
    df_final = df_final.sort_values(COL_OPPORTUNITY_SCORE, ascending=False)
    
    cols_to_display = [
        COL_LOCALE_BASE, COL_LOCALE_COMP, COL_TITLE_BASE, COL_ASIN,
        COL_PRICE_BASE, COL_ACQUISTO_NETTO, COL_PRICE_COMP, COL_VENDITA_NETTO,
        COL_MARGINE_STIMATO, COL_SHIPPING_COST, COL_MARGINE_NETTO, COL_MARGINE_NETTO_PERCENT, 
        COL_WEIGHT_KG, COL_SALES_RANK_COMP, COL_SALES_RANK_90D,
        COL_TREND, COL_BOUGHT_COMP, COL_NEW_OFFER_COMP, COL_VOLUME_SCORE,
        COL_OPPORTUNITY_SCORE, COL_OPPORTUNITY_CLASS, COL_IVA_ORIGINE, COL_IVA_CONFRONTO,
        COL_BRAND_BASE, COL_PACKAGE_DIMENSION_BASE
    ]
    # Mantieni solo le colonne effettivamente presenti
    cols_final_present = [c for c in cols_to_display if c in df_final.columns]
    df_to_show = df_final[cols_final_present]
    
    cols_to_round_list = [
        COL_PRICE_BASE, COL_ACQUISTO_NETTO, COL_PRICE_COMP, COL_VENDITA_NETTO, 
        COL_MARGINE_STIMATO, COL_SHIPPING_COST, COL_MARGINE_NETTO, COL_MARGINE_NETTO_PERCENT, 
        COL_MARGINE_PERCENT, COL_OPPORTUNITY_SCORE, COL_VOLUME_SCORE, COL_WEIGHT_KG
    ]
    for col in cols_to_round_list:
        if col in df_to_show.columns:
            df_to_show[col] = df_to_show[col].round(2)
            
    return df_to_show

#################################
# Visualizzazione Tab Principali
#################################
tab_main1, tab_main2, tab_main3 = st.tabs(["📋 ASIN Caricati", "📊 Analisi Opportunità", "📎 Risultati Dettagliati"])

with tab_main1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if files_base_uploaded:
        # Carica solo per visualizzare ASIN, non per l'analisi completa qui
        temp_base_dfs = [load_data_from_file(f) for f in files_base_uploaded]
        temp_base_dfs = [df for df in temp_base_dfs if df is not None and not df.empty]
        if temp_base_dfs:
            df_base_temp = pd.concat(temp_base_dfs, ignore_index=True)
            if COL_ASIN in df_base_temp.columns:
                unique_asins_list = df_base_temp[COL_ASIN].dropna().unique()
                st.success(f"Lista unificata di ASIN dalla Lista di Origine: {len(unique_asins_list)} prodotti")
                col1_tab1, col2_tab1 = st.columns([3, 1])
                with col1_tab1:
                    asin_text_content = "\n".join(unique_asins_list)
                    st.text_area("ASIN disponibili:", asin_text_content, height=200, key="asins-content", label_visibility="collapsed")
                    st.markdown("""
                    <button onclick="copyASINsToClipboard()" class="copy-button">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                            <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                        </svg>Copia ASINs negli appunti</button>""", unsafe_allow_html=True)
                with col2_tab1:
                    st.metric("Totale ASIN", len(unique_asins_list))
                    if COL_BRAND_BASE in df_base_temp.columns:
                        st.metric("Brand Unici", df_base_temp[COL_BRAND_BASE].nunique())
            else: st.warning(f"I file di origine non contengono la colonna '{COL_ASIN}'.")
        else: st.info("Nessun dato valido trovato nei file di origine caricati.")
    else: st.info("👆 Carica i file nella barra laterale per iniziare l'analisi")
    st.markdown('</div>', unsafe_allow_html=True)


if avvia_button:
    with st.spinner("⏳ Elaborazione dati in corso... Potrebbe richiedere alcuni minuti..."):
        # 1. Caricamento e Validazione Dati
        df_base, df_comp = load_and_validate_datasets(files_base_uploaded, comparison_files_uploaded)
        
        if df_base is None or df_comp is None: # Errori già mostrati dalle funzioni
            st.stop()

        # 2. Merge e Parsing Iniziale
        # Nomi colonne prezzo completi
        price_col_base_selected = f"{ref_price_base_option} (base)"
        price_col_comp_selected = f"{ref_price_comp_option} (comp)"
        
        df_merged_data = merge_and_parse_base_data(df_base, df_comp, ref_price_base_option, ref_price_comp_option)
        if df_merged_data is None or df_merged_data.empty:
            st.warning("Nessun prodotto comune trovato o errore nel merge.")
            st.stop()

        # 3. Calcoli Finanziari
        current_discount_rate = discount_percent_val / 100.0
        current_iva_base_rate = iva_base_tuple[1] / 100.0
        current_iva_comp_rate = iva_comp_tuple[1] / 100.0
        
        df_financials = calculate_financial_metrics(
            df_merged_data, current_discount_rate, current_iva_base_rate, current_iva_comp_rate, 
            include_shipping_calc, SHIPPING_COSTS_IT
        )

        # 4. Filtri e Calcolo Opportunity Score
        filter_parameters = {
            "min_margin_pct": min_margin_pct_val, "min_margin_abs": min_margin_abs_val,
            "max_sales_rank": max_sales_rank_val, "max_offer_count": max_offer_count_val,
            "min_buybox_price": min_buybox_price_val, "max_buybox_price": max_buybox_price_val
        }
        score_parameters = {
            "alpha": alpha_val, "beta": beta_val, "delta": delta_val, "epsilon": epsilon_val, 
            "zeta": zeta_val, "gamma": gamma_val, "theta": theta_val, 
            "min_margin_multiplier": min_margin_multiplier_val
        }
        df_scored = apply_filters_and_calc_score(df_financials, filter_parameters, score_parameters)

        if df_scored.empty:
            with tab_main2: # Mostra il messaggio nel tab analisi
                 st.info("ℹ️ Nessun prodotto trovato che soddisfa tutti i filtri e i criteri di margine.")
            st.session_state['filtered_data'] = pd.DataFrame() # Pulisce i vecchi risultati
            st.stop()

        # 5. Preparazione DataFrame Finale per Display
        iva_base_str = f"{iva_base_tuple[0]} ({iva_base_tuple[1]}%)"
        iva_comp_str = f"{iva_comp_tuple[0]} ({iva_comp_tuple[1]}%)"
        df_final_display = prepare_final_display_df(df_scored, iva_base_str, iva_comp_str)
        
        st.session_state['filtered_data'] = df_final_display
    
    st.success("🎉 Calcolo completato! Visualizza i risultati nei tab 'Analisi Opportunità' e 'Risultati Dettagliati'.")
    # Non serve st.experimental_rerun() qui, i widget nei tab successivi verranno aggiornati
    # quando Streamlit riesegue lo script a causa dell'aggiornamento di st.session_state['filtered_data']


# Questo blocco viene eseguito SEMPRE dopo il potenziale calcolo,
# quindi i tab 2 e 3 mostrano i dati da st.session_state['filtered_data']
df_to_analyze = st.session_state.get('filtered_data', pd.DataFrame())

with tab_main2:
    st.markdown('<div class="result-container">', unsafe_allow_html=True)
    st.subheader("📊 Dashboard delle Opportunità")
    
    if not df_to_analyze.empty:
        col1_dash, col2_dash, col3_dash, col4_dash = st.columns(4)
        with col1_dash: st.metric("Prodotti Trovati", len(df_to_analyze))
        with col2_dash: st.metric("Margine Netto Medio (%)", f"{df_to_analyze[COL_MARGINE_NETTO_PERCENT].mean():.2f}%" if COL_MARGINE_NETTO_PERCENT in df_to_analyze else "N/A")
        with col3_dash: st.metric("Margine Netto Medio (€)", f"{df_to_analyze[COL_MARGINE_NETTO].mean():.2f}€" if COL_MARGINE_NETTO in df_to_analyze else "N/A")
        with col4_dash: st.metric("Opportunity Score Massimo", f"{df_to_analyze[COL_OPPORTUNITY_SCORE].max():.2f}" if COL_OPPORTUNITY_SCORE in df_to_analyze else "N/A")
        
        # Riepilogo impostazioni IVA e Spedizione (recuperati dalla session state o dai widget correnti)
        iva_base_info_disp = f"{st.session_state.get('iva_base', ('N/D',0))[0]} ({st.session_state.get('iva_base', ('N/D',0))[1]}%)"
        iva_comp_info_disp = f"{st.session_state.get('iva_comp', ('N/D',0))[0]} ({st.session_state.get('iva_comp', ('N/D',0))[1]}%)"
        sped_info_disp = '✅ Spedizione Inclusa' if st.session_state.get('include_shipping_key', True) else '❌ Spedizione Esclusa'
        st.info(f"IVA Origine: {iva_base_info_disp} | IVA Confronto: {iva_comp_info_disp} | {sped_info_disp}")
        
        dark_colors_map = {"Eccellente": "#2ecc71", "Buona": "#27ae60", "Discreta": "#f39c12", "Bassa": "#e74c3c"}
        
        if COL_OPPORTUNITY_SCORE in df_to_analyze.columns and COL_OPPORTUNITY_CLASS in df_to_analyze.columns:
            st.subheader("Distribuzione Opportunity Score")
            hist = alt.Chart(df_to_analyze.reset_index()).mark_bar().encode(
                alt.X(f"{COL_OPPORTUNITY_SCORE}:Q", bin=alt.Bin(maxbins=20), title="Opportunity Score"),
                alt.Y("count()", title="Numero di Prodotti"),
                color=alt.Color(f"{COL_OPPORTUNITY_CLASS}:N", scale=alt.Scale(domain=list(dark_colors_map.keys()), range=list(dark_colors_map.values())))
            ).properties(height=250)
            st.altair_chart(hist, use_container_width=True)

        if all(c in df_to_analyze.columns for c in [COL_MARGINE_NETTO_PERCENT, COL_OPPORTUNITY_SCORE, COL_VOLUME_SCORE, COL_LOCALE_COMP]):
            st.subheader("Analisi Multifattoriale")
            scatter_chart = alt.Chart(df_to_analyze.reset_index()).mark_circle().encode(
                x=alt.X(f"{COL_MARGINE_NETTO_PERCENT}:Q", title="Margine Netto (%)"),
                y=alt.Y(f"{COL_OPPORTUNITY_SCORE}:Q", title="Opportunity Score"),
                size=alt.Size(f"{COL_VOLUME_SCORE}:Q", title="Volume Stimato", scale=alt.Scale(range=[20, 200])),
                color=alt.Color(f"{COL_LOCALE_COMP}:N", title="Mercato Confronto", scale=alt.Scale(scheme='category10')),
                tooltip=[COL_TITLE_BASE, COL_ASIN, COL_MARGINE_NETTO_PERCENT, COL_MARGINE_NETTO, COL_SHIPPING_COST, COL_SALES_RANK_COMP, COL_OPPORTUNITY_SCORE, COL_TREND]
            ).interactive()
            st.altair_chart(scatter_chart, use_container_width=True)
        
        if COL_LOCALE_COMP in df_to_analyze.columns:
            st.subheader("Analisi per Mercato")
            market_analysis_df = df_to_analyze.groupby(COL_LOCALE_COMP).agg(
                Prodotti=(COL_ASIN, "count"),
                Margine_Netto_Medio_Pct=(COL_MARGINE_NETTO_PERCENT, "mean"),
                Margine_Netto_Medio_Eur=(COL_MARGINE_NETTO, "mean"),
                Costo_Spedizione_Medio_Eur=(COL_SHIPPING_COST, "mean"),
                Opportunity_Score_Medio=(COL_OPPORTUNITY_SCORE, "mean")
            ).reset_index()
            market_analysis_df.columns = ["Mercato", "Prodotti", "Margine Netto Medio (%)", "Margine Netto Medio (€)", "Costo Spedizione Medio (€)", "Opportunity Score Medio"]
            st.dataframe(market_analysis_df.round(2), use_container_width=True)
            
            market_bar_chart = alt.Chart(market_analysis_df).mark_bar().encode(
                x="Mercato:N", y="Opportunity Score Medio:Q", color=alt.Color("Mercato:N", scale=alt.Scale(scheme='category10')),
                tooltip=list(market_analysis_df.columns)
            ).properties(height=300)
            st.altair_chart(market_bar_chart, use_container_width=True)
    else:
        st.info("Nessun dato da analizzare. Clicca su 'Calcola Opportunity Score' nella sidebar dopo aver caricato i file.")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_main3:
    st.markdown('<div class="result-container">', unsafe_allow_html=True)
    st.subheader("🔍 Esplora i Risultati")

    if df_to_analyze is not None and not df_to_analyze.empty:
        filtered_display_df = df_to_analyze.copy()
        
        st.markdown('<div class="filter-group">', unsafe_allow_html=True)
        col1_filt, col2_filt, col3_filt = st.columns(3)
        
        with col1_filt:
            if COL_LOCALE_COMP in filtered_display_df.columns:
                markets_list = ["Tutti"] + sorted(filtered_display_df[COL_LOCALE_COMP].unique().tolist())
                selected_market_filter = st.selectbox("Filtra per Mercato", markets_list, key="market_filter")
                if selected_market_filter != "Tutti":
                    filtered_display_df = filtered_display_df[filtered_display_df[COL_LOCALE_COMP] == selected_market_filter]
        with col2_filt:
            if COL_BRAND_BASE in filtered_display_df.columns and filtered_display_df[COL_BRAND_BASE].nunique() > 0 :
                brands_list = ["Tutti"] + sorted(filtered_display_df[COL_BRAND_BASE].dropna().unique().tolist())
                selected_brand_filter = st.selectbox("Filtra per Brand", brands_list, key="brand_filter")
                if selected_brand_filter != "Tutti":
                    filtered_display_df = filtered_display_df[filtered_display_df[COL_BRAND_BASE] == selected_brand_filter]
            else: st.text("N/A")
        with col3_filt:
            if COL_OPPORTUNITY_CLASS in filtered_display_df.columns:
                classes_list = ["Tutti"] + sorted(filtered_display_df[COL_OPPORTUNITY_CLASS].unique().tolist())
                selected_class_filter = st.selectbox("Filtra per Qualità Opportunità", classes_list, key="class_filter")
                if selected_class_filter != "Tutti":
                    filtered_display_df = filtered_display_df[filtered_display_df[COL_OPPORTUNITY_CLASS] == selected_class_filter]

        col1_slider_filt, col2_slider_filt = st.columns(2)
        with col1_slider_filt:
            if COL_OPPORTUNITY_SCORE in filtered_display_df.columns and not filtered_display_df.empty:
                min_val_os = float(filtered_display_df[COL_OPPORTUNITY_SCORE].min())
                max_val_os = float(filtered_display_df[COL_OPPORTUNITY_SCORE].max())
                if min_val_os < max_val_os: # Slider ha bisogno di min < max
                    selected_min_op_score = st.slider("Opportunity Score Minimo", min_val_os, max_val_os, min_val_os, key="op_score_slider")
                    filtered_display_df = filtered_display_df[filtered_display_df[COL_OPPORTUNITY_SCORE] >= selected_min_op_score]
                else: # Se tutti i valori sono uguali o un solo valore
                    st.text(f"Opportunity Score: {min_val_os:.2f} (valore unico)")


        with col2_slider_filt:
            if COL_MARGINE_NETTO in filtered_display_df.columns and not filtered_display_df.empty:
                min_val_mn = float(filtered_display_df[COL_MARGINE_NETTO].min())
                max_val_mn = float(filtered_display_df[COL_MARGINE_NETTO].max())
                if min_val_mn < max_val_mn:
                    selected_min_margin = st.slider("Margine Netto Minimo (€)", min_val_mn, max_val_mn, min_val_mn, key="margin_slider")
                    filtered_display_df = filtered_display_df[filtered_display_df[COL_MARGINE_NETTO] >= selected_min_margin]
                else:
                    st.text(f"Margine Netto (€): {min_val_mn:.2f} (valore unico)")


        search_term_val = st.text_input("Cerca per ASIN o Titolo", key="search_term_results")
        if search_term_val:
            mask_search = (
                filtered_display_df[COL_ASIN].str.contains(search_term_val, case=False, na=False) | 
                filtered_display_df[COL_TITLE_BASE].str.contains(search_term_val, case=False, na=False)
            )
            filtered_display_df = filtered_display_df[mask_search]
        st.markdown('</div>', unsafe_allow_html=True) # Fine filter-group
        
        if not filtered_display_df.empty:
            st.markdown(f"**{len(filtered_display_df)} prodotti trovati con i filtri applicati**")
            
            def highlight_opportunity_style(val): # Styler function
                class_color_map = {
                    "Eccellente": ('#153d2e', '#2ecc71'), "Buona": ('#14432d', '#27ae60'),
                    "Discreta": ('#402d10', '#f39c12'), "Bassa": ('#3d1a15', '#e74c3c')
                }
                if val in class_color_map:
                    bg, color = class_color_map[val]
                    return f'background-color: {bg}; color: {color}; font-weight: bold;'
                return ''

            styled_df = filtered_display_df.style.map(
                highlight_opportunity_style, subset=[COL_OPPORTUNITY_CLASS]
            ).format({
                COL_PRICE_BASE: "€{:.2f}", COL_ACQUISTO_NETTO: "€{:.2f}",
                COL_PRICE_COMP: "€{:.2f}", COL_VENDITA_NETTO: "€{:.2f}",
                COL_MARGINE_STIMATO: "€{:.2f}", COL_SHIPPING_COST: "€{:.2f}",
                COL_MARGINE_NETTO: "€{:.2f}", COL_MARGINE_NETTO_PERCENT: "{:.2f}%",
                COL_OPPORTUNITY_SCORE: "{:.2f}", COL_VOLUME_SCORE: "{:.2f}",
                COL_WEIGHT_KG: "{:.2f} kg"
            }, na_rep='N/D')
            
            # Rimuovi colonne non utili per il display finale
            cols_to_drop_from_view = [COL_OPPORTUNITY_TAG, COL_SALES_RANK_90D] # Esempio
            display_cols_final = [col for col in filtered_display_df.columns if col not in cols_to_drop_from_view]

            st.dataframe(styled_df, column_order=display_cols_final, height=600, use_container_width=True)
            
            csv_export_data = filtered_display_df.to_csv(index=False, sep=";").encode("utf-8")
            excel_export_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_export_buffer, engine='openpyxl') as writer:
                filtered_display_df.to_excel(writer, index=False, sheet_name='Risultati')
            excel_export_data = excel_export_buffer.getvalue()

            col1_export, col2_export = st.columns(2)
            with col1_export:
                st.download_button("📥 Scarica CSV", csv_export_data, "risultati_arbitraggio.csv", "text/csv", use_container_width=True)
            with col2_export:
                st.download_button("📥 Scarica Excel", excel_export_data, "risultati_arbitraggio.xlsx", 
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            st.warning("Nessun prodotto corrisponde ai filtri selezionati.")
    else:
        st.info("👈 Clicca su 'Calcola Opportunity Score' per visualizzare i risultati, oppure carica dei file se non l'hai ancora fatto.")
    st.markdown('</div>', unsafe_allow_html=True) # Fine result-container

# Footer e Help
with st.expander("ℹ️ Guida e Dettagli Calcoli", expanded=False):
    st.markdown("""
    ### Calcolo dell'Opportunity Score
    L'Opportunity Score è un punteggio normalizzato (0-100) che combina diversi fattori:
    - **Margine Netto Percentuale e Assoluto**: Profitto dopo costi, spedizione e IVA.
    - **Volume di Vendita Stimato**: Basato sull'inverso del logaritmo del Sales Rank.
    - **Trend Sales Rank**: Variazione del ranking (90gg vs attuale).
    - **Competizione (Offer Count)**: Penalità per troppe offerte.
    - **Acquisti Recenti**: Numero di unità vendute nel mese precedente.
    I pesi di questi fattori sono configurabili nella sidebar.

    ### Calcolo del Margine Netto
    1.  **Prezzo Acquisto Lordo (Origine)**: Prezzo selezionato dal file base.
    2.  **Prezzo Acquisto Netto (Origine)**: Prezzo lordo / (1 + IVA Origine), poi scontato.
    3.  **Prezzo Vendita Lordo (Confronto)**: Prezzo selezionato dal file confronto.
    4.  **Prezzo Vendita Netto (Confronto)**: Prezzo lordo / (1 + IVA Confronto).
    5.  **Margine Lordo Stimato**: Prezzo Vendita Netto (Confronto) - Prezzo Acquisto Netto (Origine).
    6.  **Costi Spedizione**: Calcolati in base al peso (vedi listino) e inclusi se l'opzione è attiva.
    7.  **Margine Netto Finale**: Margine Lordo Stimato - Costi Spedizione (se inclusi).

    ### Listino Costi di Spedizione (Esempio Italia)
    Il listino è visualizzato nella sidebar. Il peso del prodotto viene estratto automaticamente se disponibile, altrimenti si assume 1kg (modificabile implicitamente tramite i dati di input).
    
    ### Gestione IVA
    L'app permette di selezionare le aliquote IVA per il mercato di origine e di confronto. Questo è cruciale per un calcolo accurato dei margini netti.
    Aliquote predefinite: Italia (22%), Germania (19%), Francia (20%), Spagna (21%), Regno Unito (20%).
    """)

st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #333; color: #aaa;">
    Amazon Market Analyzer - Arbitraggio Multi-Mercato © 2025<br>
    Versione 2.1 (Refactored)
</div>
""", unsafe_allow_html=True)