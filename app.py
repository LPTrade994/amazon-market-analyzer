import streamlit as st
import pandas as pd
import numpy as np
import re
import altair as alt
from streamlit_extras.colored_header import colored_header
from streamlit_extras.metric_cards import style_metric_cards
import streamlit_shadcn_ui as ui

# Tema e stile personalizzato
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato per migliorare l'aspetto
st.markdown("""
<style>
    .stApp {
        background-color: #f5f7f9;
    }
    .main-header {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #2c3e50;
        font-size: 2.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        margin-bottom: 1.5rem;
    }
    .subheader {
        color: #34495e;
        font-size: 1.5rem;
        padding-top: 1rem;
    }
    .card {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        background-color: white;
        margin-bottom: 1rem;
    }
    .result-container {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        margin-top: 2rem;
    }
    .filter-group {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2980b9;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }
    .success-tag {
        background-color: #2ecc71;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .warning-tag {
        background-color: #f39c12;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .danger-tag {
        background-color: #e74c3c;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
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
    
    # Aggiunta del selettore per l'IVA di riferimento per i mercati di confronto
    st.markdown("**IVA per calcolo del margine**")
    iva_comp = st.selectbox(
        "IVA mercato di confronto",
        [("Italia", 22), ("Germania", 19), ("Francia", 20), ("Spagna", 21), ("Regno Unito", 20)],
        format_func=lambda x: f"{x[0]} ({x[1]}%)"
    )
    iva_comp_rate = iva_comp[1] / 100.0
    
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
                    st.text_area("Copia qui:", "\n".join(unique_asins), height=200)
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
# Funzione per Calcolare il Prezzo d'Acquisto Netto
#################################
def calc_final_purchase_price(row, discount):
    """
    Calcola il prezzo d'acquisto netto, IVA esclusa e scontato, in base al paese.
    Se il prodotto è acquistato in Italia (Locale "it"):
      final = (prezzo lordo / 1.22) - (prezzo lordo * discount)
    Altrimenti (es. Germania, IVA 19%):
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
    # Leggi anche il Sales Rank a 90 giorni, se presente
    df_merged["SalesRank_90d"] = df_merged.get("Sales Rank: 90 days avg. (comp)", pd.Series(np.nan)).apply(parse_int)
    
    # Calcolo del prezzo d'acquisto netto per ogni prodotto dalla lista di origine
    df_merged["Acquisto_Netto"] = df_merged.apply(lambda row: calc_final_purchase_price(row, discount), axis=1)
    
    # NUOVA LOGICA: Calcolo del margine stimato considerando IVA correttamente
    # 1. Prezzo nel mercato di confronto (lordo IVA)
    # 2. Prezzo di acquisto netto (già senza IVA)
    # 3. Margine = Prezzo confronto / (1 + IVA) - Prezzo acquisto netto
    
    # Calcolo del prezzo netto di vendita nel mercato di confronto (senza IVA)
    df_merged["Vendita_Netto"] = df_merged["Price_Comp"] / (1 + iva_comp_rate)
    
    # Calcolo del margine stimato corretto (in valore assoluto e percentuale)
    df_merged["Margine_Stimato"] = df_merged["Vendita_Netto"] - df_merged["Acquisto_Netto"]
    df_merged["Margine_%"] = (df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]) * 100
    
    # Nuovo calcolo del margine percentuale tra i prezzi lordi (solo per riferimento)
    df_merged["Margin_Pct_Lordo"] = (df_merged["Price_Comp"] - df_merged["Price_Base"]) / df_merged["Price_Base"] * 100
    
    # Filtro sui prodotti con margine positivo
    df_merged = df_merged[df_merged["Margine_%"] > min_margin_pct]
    df_merged = df_merged[df_merged["Margine_Stimato"] > min_margin_abs]
    
    # Applicazione dei filtri avanzati (sul mercato di confronto)
    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged = df_merged[df_merged["SalesRank_Comp"] <= max_sales_rank]
    
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    df_merged = df_merged[df_merged["NewOffer_Comp"] <= max_offer_count]
    
    df_merged["Price_Comp"] = df_merged["Price_Comp"].fillna(0)
    df_merged = df_merged[df_merged["Price_Comp"].between(min_buybox_price, max_buybox_price)]
    
    # Calcolo del bonus/penalità per il Trend del Sales Rank
    df_merged["Trend_Bonus"] = np.log((df_merged["SalesRank_90d"].fillna(df_merged["SalesRank_Comp"]) + 1) / (df_merged["SalesRank_Comp"] + 1))
    # Formattiamo il trend in una stringa con icona
    df_merged["Trend"] = df_merged["Trend_Bonus"].apply(format_trend)
    
    # NUOVA FORMULA per l'Opportunity Score
    # Opportunity_Score = 
    #   ε * Margine_% +
    #   θ * Margine_Stimato +
    #   β * log(1 + Bought_Comp) -
    #   δ * min(NewOffer_Comp, 10) -  # cap su NewOffer_Comp
    #   α * log(SalesRank_Comp + 1) +
    #   ζ * Trend_Bonus +
    #   γ * (1 / log(SalesRank_Comp + 10))  # nuovo fattore per volume vendite
    
    # Normalizzazione rank per evitare divisioni per zero o valori negativi
    df_merged["Norm_Rank"] = np.log(df_merged["SalesRank_Comp"].fillna(999999) + 10)
    
    # Calcoliamo il volume stimato di vendite (inversamente proporzionale al rank)
    df_merged["Volume_Score"] = 1000 / df_merged["Norm_Rank"]
    
    # Calcolo del fattore di ROI (Return on Investment)
    df_merged["ROI_Factor"] = df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]
    
    # Calcolo del nuovo Opportunity Score
    df_merged["Opportunity_Score"] = (
        epsilon * df_merged["Margine_%"] +
        theta * df_merged["Margine_Stimato"] +
        beta * np.log(1 + df_merged["Bought_Comp"].fillna(0)) -
        delta * np.minimum(df_merged["NewOffer_Comp"].fillna(0), 10) -
        alpha * df_merged["Norm_Rank"] +
        zeta * df_merged["Trend_Bonus"] +
        gamma * df_merged["Volume_Score"]
    )
    
    # Fattore di penalizzazione per margini troppo bassi
    min_margin_threshold = min_margin_abs * min_margin_multiplier
    df_merged.loc[df_merged["Margine_Stimato"] < min_margin_threshold, "Opportunity_Score"] *= (df_merged["Margine_Stimato"] / min_margin_threshold)
    
    # Normalizzazione dei punteggi per renderli più leggibili (0-100 scala)
    max_score = df_merged["Opportunity_Score"].max()
    if not np.isnan(max_score) and max_score > 0:
        df_merged["Opportunity_Score"] = (df_merged["Opportunity_Score"] / max_score) * 100
    
    # Classificazione dell'opportunità
    df_merged[["Opportunity_Class", "Opportunity_Tag"]] = df_merged.apply(
        lambda row: pd.Series(classify_opportunity(row["Opportunity_Score"])), axis=1
    )
    
    # Ordiniamo i risultati per Opportunity Score decrescente
    df_merged = df_merged.sort_values("Opportunity_Score", ascending=False)
    
    # Selezione delle colonne finali da visualizzare
    cols_final = [
        "Locale (base)", "Locale (comp)", "Title (base)", "ASIN",
        "Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto",
        "Margine_Stimato", "Margine_%", "SalesRank_Comp", "SalesRank_90d",
        "Trend", "Bought_Comp", "NewOffer_Comp", "Volume_Score",
        "Opportunity_Score", "Opportunity_Class", "Brand (base)", "Package: Dimension (cm³) (base)"
    ]
    cols_final = [c for c in cols_final if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()
    
    # Arrotonda i valori numerici principali a 2 decimali
    cols_to_round = ["Price_Base", "Acquisto_Netto", "Price_Comp", "Vendita_Netto", 
                     "Margine_Stimato", "Margine_%", "Opportunity_Score", "Volume_Score"]
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
                st.metric("Margine Medio (%)", f"{df_finale['Margine_%'].mean():.2f}%")
            with col3:
                st.metric("Margine Medio (€)", f"{df_finale['Margine_Stimato'].mean():.2f}€")
            with col4:
                st.metric("Opportunity Score Massimo", f"{df_finale['Opportunity_Score'].max():.2f}")
            
            # Grafico di distribuzione degli Opportunity Score
            st.subheader("Distribuzione Opportunity Score")
            hist = alt.Chart(df_finale.reset_index()).mark_bar().encode(
                alt.X("Opportunity_Score:Q", bin=alt.Bin(maxbins=20), title="Opportunity Score"),
                alt.Y("count()", title="Numero di Prodotti"),
                color=alt.Color("Opportunity_Class:N", 
                               scale=alt.Scale(domain=["Eccellente", "Buona", "Discreta", "Bassa"],
                                              range=["#2ecc71", "#27ae60", "#f39c12", "#e74c3c"]))
            ).properties(height=250)
            st.altair_chart(hist, use_container_width=True)
            
            # Grafico Scatter: Margine (%) vs Opportunity Score con dimensione per Volume
            st.subheader("Analisi Multifattoriale")
            chart = alt.Chart(df_finale.reset_index()).mark_circle().encode(
                x=alt.X("Margine_%:Q", title="Margine (%)"),
                y=alt.Y("Opportunity_Score:Q", title="Opportunity Score"),
                size=alt.Size("Volume_Score:Q", title="Volume Stimato", scale=alt.Scale(range=[20, 200])),
                color=alt.Color("Locale (comp):N", title="Mercato Confronto"),
                tooltip=["Title (base)", "ASIN", "Margine_%", "Margine_Stimato", "SalesRank_Comp", "Opportunity_Score", "Trend"]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
            
            # Analisi per Mercato di Confronto
            st.subheader("Analisi per Mercato")
            if "Locale (comp)" in df_finale.columns:
                market_analysis = df_finale.groupby("Locale (comp)").agg({
                    "ASIN": "count",
                    "Margine_%": "mean",
                    "Margine_Stimato": "mean",
                    "Opportunity_Score": "mean"
                }).reset_index()
                market_analysis.columns = ["Mercato", "Prodotti", "Margine Medio (%)", "Margine Medio (€)", "Opportunity Score Medio"]
                market_analysis = market_analysis.round(2)
                market_analysis = market_analysis.round(2)
                st.dataframe(market_analysis, use_container_width=True)
                
                # Grafico a barre per confronto mercati
                market_chart = alt.Chart(market_analysis).mark_bar().encode(
                    x="Mercato:N",
                    y="Opportunity Score Medio:Q",
                    color=alt.Color("Mercato:N", scale=alt.Scale(scheme='category10')),
                    tooltip=["Mercato", "Prodotti", "Margine Medio (%)", "Margine Medio (€)", "Opportunity Score Medio"]
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
                min_margin = st.slider("Margine Minimo (€)", 
                                      min_value=float(filtered_df["Margine_Stimato"].min()),
                                      max_value=float(filtered_df["Margine_Stimato"].max()),
                                      value=float(filtered_df["Margine_Stimato"].min()))
                filtered_df = filtered_df[filtered_df["Margine_Stimato"] >= min_margin]
            
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
                # Formato personalizzato per la tabella dei risultati
                def highlight_opportunity(val):
                    if val == "Eccellente":
                        return 'background-color: #d5f5e3; color: #27ae60; font-weight: bold'
                    elif val == "Buona":
                        return 'background-color: #eafaf1; color: #2ecc71; font-weight: bold'
                    elif val == "Discreta":
                        return 'background-color: #fef9e7; color: #f39c12; font-weight: bold'
                    else:
                        return 'background-color: #fdedec; color: #e74c3c'
                
                # Aggiungi la formattazione HTML per le classi di opportunity
                def format_with_html(df):
                    styled = df.style.applymap(
                        lambda x: highlight_opportunity(x) if x in ["Eccellente", "Buona", "Discreta", "Bassa"] else '',
                        subset=["Opportunity_Class"]
                    )
                    return styled.format({
                        "Price_Base": "€{:.2f}",
                        "Acquisto_Netto": "€{:.2f}",
                        "Price_Comp": "€{:.2f}",
                        "Vendita_Netto": "€{:.2f}",
                        "Margine_Stimato": "€{:.2f}",
                        "Margine_%": "{:.2f}%",
                        "Opportunity_Score": "{:.2f}",
                        "Volume_Score": "{:.2f}"
                    })
                
                # Visualizzazione dei risultati con paginazione
                st.markdown(f"**{len(filtered_df)} prodotti trovati**")
                results_per_page = st.select_slider("Risultati per pagina", options=[10, 25, 50, 100], value=25)
                
                # Imposta la paginazione
                if 'page_number' not in st.session_state:
                    st.session_state.page_number = 0
                
                def next_page():
                    st.session_state.page_number += 1
                
                def prev_page():
                    st.session_state.page_number -= 1
                
                total_pages = len(filtered_df) // results_per_page + (1 if len(filtered_df) % results_per_page != 0 else 0)
                
                # Assicuriamoci che la pagina corrente sia valida
                if st.session_state.page_number >= total_pages:
                    st.session_state.page_number = total_pages - 1
                if st.session_state.page_number < 0:
                    st.session_state.page_number = 0
                
                # Selezione delle colonne da visualizzare (rimozione di alcune colonne per chiarezza)
                display_cols = [col for col in filtered_df.columns if col not in ["Opportunity_Tag", "SalesRank_90d"]]
                
                # Calcola gli indici per la pagina corrente
                start_idx = st.session_state.page_number * results_per_page
                end_idx = min(start_idx + results_per_page, len(filtered_df))
                
                # Mostra la tabella paginata
                st.dataframe(
                    format_with_html(filtered_df[display_cols].iloc[start_idx:end_idx]),
                    height=min(53 * results_per_page, 600),
                    use_container_width=True
                )
                
                # Controlli di paginazione
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if st.session_state.page_number > 0:
                        st.button("⬅️ Precedente", on_click=prev_page)
                
                with col2:
                    st.write(f"Pagina {st.session_state.page_number + 1} di {total_pages}")
                
                with col3:
                    if st.session_state.page_number < total_pages - 1:
                        st.button("Successiva ➡️", on_click=next_page)
                
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
    
    - **Margine percentuale**: Quanto margine percentuale ottieni 
    - **Margine assoluto**: Quanto guadagno in euro ottieni per ogni vendita
    - **Volume di vendita**: Stimato tramite il Sales Rank (più basso = più vendite)
    - **Trend**: Se il prodotto sta migliorando o peggiorando nel ranking
    - **Competizione**: Quante altre offerte ci sono per lo stesso prodotto
    - **Acquisti recenti**: Quanti acquisti sono stati fatti nell'ultimo mese
    
    ### Calcolo del Margine
    
    Il margine viene calcolato considerando:
    1. **Prezzo di acquisto netto**: Prezzo base scontato e senza IVA
    2. **Prezzo di vendita netto**: Prezzo di confronto senza IVA
    3. **Margine**: Differenza tra prezzo di vendita netto e prezzo di acquisto netto
    
    ### Note sull'IVA
    
    L'applicazione gestisce correttamente l'IVA dei diversi paesi:
    - Italia: 22%
    - Germania: 19%
    - Francia: 20%
    - Spagna: 21%
    - Regno Unito: 20%
    
    Il margine stimato tiene conto di queste differenze.
    """)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; color: #666;">
    Amazon Market Analyzer - Arbitraggio Multi-Mercato © 2025<br>
    Versione 2.0
</div>
""", unsafe_allow_html=True)