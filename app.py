import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #ddd;
        padding: 10px;
        background-color: #f5f5f5;
        border-radius: 5px;
        font-family: monospace;
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
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'base_asins' not in st.session_state:
    st.session_state['base_asins'] = None

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

def calc_final_purchase_price(row, discount, iva_rates):
    """
    Calcola il prezzo d'acquisto netto considerando lo sconto e l'IVA.
    Formula differente per mercato italiano rispetto agli altri.
    """
    locale = row.get("Locale (base)", "it").lower()
    gross_price = row["Price_Base"]
    
    if pd.isna(gross_price):
        return np.nan
    
    iva_rate = iva_rates.get(locale, 0.22)  # Default all'IVA italiana se non trovata
    net_price = gross_price / (1 + iva_rate)
    
    # Logica differente per l'Italia rispetto agli altri paesi
    if locale == "it":
        # Per Italia: lo sconto si applica al prezzo lordo, poi si toglie dal netto
        discount_amount = gross_price * discount
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

def rev_calc_revenue_metrics(row, shipping_cost_rev, market_type, iva_rates):
    """
    Calcola le metriche di redditività per un prodotto.
    """
    # Ottiene la categoria del prodotto
    category = row.get("Categories: Root (base)", "Altri prodotti")
    
    # Ottiene il prezzo e la località in base al tipo di mercato (base o confronto)
    if market_type == "base":
        price = row["Price_Base"]
        locale = row.get("Locale (base)", "it").lower()
    else:
        price = row["Price_Comp"]
        locale = row.get("Locale (comp)", "de").lower()
    
    # Se il prezzo non è disponibile, restituisce valori nulli
    if pd.isna(price):
        return pd.Series({
            "Margine_Netto (€)": np.nan,
            "Margine_Netto (%)": np.nan,
            "Commissioni": np.nan,
            "Prezzo_Netto": np.nan
        })
    
    # Ottiene l'aliquota IVA per la località
    iva_rate = iva_rates.get(locale, 0.22)
    
    # Calcola il prezzo al netto dell'IVA
    price_net = price / (1 + iva_rate)
    
    # Calcola le commissioni
    fees = rev_calc_fees(category, price)
    total_fees = fees["total_fees"]
    
    # Calcola i costi totali (commissioni + spedizione)
    total_costs = total_fees + shipping_cost_rev
    
    # Ottiene il prezzo d'acquisto netto
    purchase_net = row["Acquisto_Netto"]
    
    # Calcola il margine netto
    margin_net = price_net - total_costs - purchase_net
    
    # Calcola il margine in percentuale
    margin_pct = (margin_net / price) * 100 if price != 0 else np.nan
    
    return pd.Series({
        "Margine_Netto (€)": round(margin_net, 2),
        "Margine_Netto (%)": round(margin_pct, 2),
        "Commissioni": round(total_fees, 2),
        "Prezzo_Netto": round(price_net, 2)
    })

def calculate_opportunity_score(row):
    """
    Calcola un punteggio di opportunità per ogni prodotto.
    """
    try:
        margin_base = row["Margine_Netto (€)_Origine"]
        margin_comp = row["Margine_Netto (€)_Confronto"]
        
        if pd.isna(margin_base) or pd.isna(margin_comp):
            return 0
        
        # Calcola la differenza di margine tra i mercati
        margin_diff = margin_comp - margin_base
        
        # Calcola il punteggio di opportunità
        # Formula: Differenza di margine * Margine % nel mercato di confronto
        opportunity_score = margin_diff * row["Margine_Netto (%)_Confronto"] / 100
        
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

# Layout sidebar per i parametri di input
with st.sidebar:
    st.markdown("<h2 style='color:#FF9900'>Impostazioni</h2>", unsafe_allow_html=True)
    
    with st.expander("Caricamento File", expanded=True):
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
    
    with st.expander("Configurazione Prezzi", expanded=True):
        ref_price_base = st.selectbox(
            "Prezzo di riferimento (Origine)",
            ["Buy Box: Current", "Amazon: Current", "New: Current"]
        )
        ref_price_comp = st.selectbox(
            "Prezzo di riferimento (Confronto)",
            ["Buy Box: Current", "Amazon: Current", "New: Current"]
        )
    
    with st.expander("Parametri Finanziari", expanded=True):
        discount_percent = st.slider(
            "Sconto per gli acquisti (%)",
            min_value=0.0,
            max_value=50.0,
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
        
        min_margin_percent = st.slider(
            "Margine minimo (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0
        )
    
    calcola_btn = st.button("Calcola Opportunity Score", use_container_width=True)

# Funzione principale per l'elaborazione dei dati
def process_data():
    if not files_base or not comparison_files:
        st.warning("Carica almeno un file per la Lista di Origine e uno per le Liste di Confronto.")
        return None, None, None
    
    # Carica e combina i file base
    base_list = [load_data(f) for f in files_base if load_data(f) is not None and not load_data(f).empty]
    if not base_list:
        st.error("Nessun file di origine valido caricato.")
        return None, None, None
    df_base = pd.concat(base_list, ignore_index=True)
    
    # Estrai gli ASIN dal file base
    base_asins = extract_asins(df_base)
    
    # Carica e combina i file di confronto
    comp_list = [load_data(f) for f in comparison_files if load_data(f) is not None and not load_data(f).empty]
    if not comp_list:
        st.error("Nessun file di confronto valido caricato.")
        return None, None, base_asins
    df_comp = pd.concat(comp_list, ignore_index=True)
    
    # Verifica la presenza della colonna ASIN
    if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
        st.error("Assicurati che entrambi i file contengano la colonna ASIN.")
        return None, None, base_asins
    
    # Unisci i dataset sulla base degli ASIN
    df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)"))
    if df_merged.empty:
        st.error("Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto.")
        return None, None, base_asins
    
    # Estrai e prepara le colonne dei prezzi
    price_col_base = f"{ref_price_base} (base)"
    price_col_comp = f"{ref_price_comp} (comp)"
    df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(parse_float)
    df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(parse_float)
    
    # Calcola il prezzo d'acquisto netto
    df_merged["Acquisto_Netto"] = df_merged.apply(
        lambda row: calc_final_purchase_price(row, discount, IVA_RATES), 
        axis=1
    )
    
    # Calcola le metriche di revenue per il mercato base
    df_revenue_base = df_merged.apply(
        lambda row: rev_calc_revenue_metrics(row, shipping_cost_rev, "base", IVA_RATES), 
        axis=1
    )
    df_revenue_base = df_revenue_base.add_suffix("_Origine")
    
    # Calcola le metriche di revenue per il mercato di confronto
    df_revenue_comp = df_merged.apply(
        lambda row: rev_calc_revenue_metrics(row, shipping_cost_rev, "comp", IVA_RATES), 
        axis=1
    )
    df_revenue_comp = df_revenue_comp.add_suffix("_Confronto")
    
    # Crea il dataframe finale
    df_finale = pd.concat([
        df_merged[["Locale (base)", "Locale (comp)", "ASIN", "Title (base)", "Price_Base", "Price_Comp", "Acquisto_Netto"]],
        df_revenue_base,
        df_revenue_comp
    ], axis=1)
    
    # Calcola l'opportunity score
    df_finale["Opportunity_Score"] = df_finale.apply(calculate_opportunity_score, axis=1)
    
    # Filtra per opportunità positive
    df_opportunities = df_finale[df_finale["Margine_Netto (%)_Confronto"] >= min_margin_percent].copy()
    df_opportunities.sort_values("Opportunity_Score", ascending=False, inplace=True)
    
    return df_finale, df_opportunities, base_asins

# Esegui l'elaborazione quando il pulsante viene premuto
if calcola_btn:
    with st.spinner("Elaborazione in corso..."):
        df_finale, df_opportunities, base_asins = process_data()
        if df_finale is not None:
            st.session_state['processed_data'] = df_finale
            st.session_state['opportunity_scores'] = df_opportunities
            st.session_state['base_asins'] = base_asins
            st.session_state['last_update'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            st.success("Elaborazione completata!")

# Visualizza i risultati
if st.session_state['processed_data'] is not None:
    st.markdown("<h2 class='sub-header'>Risultati dell'Analisi</h2>", unsafe_allow_html=True)
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Prodotti Analizzati", len(st.session_state['processed_data']))
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Opportunità Trovate", len(st.session_state['opportunity_scores']) if st.session_state['opportunity_scores'] is not None else 0)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        if st.session_state['opportunity_scores'] is not None and not st.session_state['opportunity_scores'].empty:
            top_margin = st.session_state['opportunity_scores']["Margine_Netto (%)_Confronto"].max()
            top_margin_str = f"{top_margin:.2f}%" if not pd.isna(top_margin) else "N/A"
        else:
            top_margin_str = "N/A"
        st.metric("Miglior Margine", top_margin_str)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Ultimo Aggiornamento", st.session_state['last_update'])
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tabs per i diversi tipi di visualizzazione
    tab1, tab2, tab3, tab4 = st.tabs(["🔝 Migliori Opportunità", "📊 Analisi Grafica", "📋 Tutti i Risultati", "📑 Lista ASIN"])
    
    with tab1:
        if st.session_state['opportunity_scores'] is not None and not st.session_state['opportunity_scores'].empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("### Top Prodotti per Opportunità")
            
            top_opportunities = st.session_state['opportunity_scores'].head(10)
            
            # Visualizzazione migliorata delle opportunità
            for index, row in top_opportunities.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.markdown(f"**ASIN**: [{row['ASIN']}](https://www.amazon.{row['Locale (comp)']}/dp/{row['ASIN']})")
                        st.markdown(f"**Score**: {row['Opportunity_Score']:.2f}")
                    
                    with col2:
                        st.markdown(f"**{row['Title (base)']}**")
                        origin_market = f"🏠 Origine ({row['Locale (base)'].upper()}): €{row['Price_Base']:.2f} → Margine: {row['Margine_Netto (%)_Origine']:.2f}%"
                        dest_market = f"🚀 Destinazione ({row['Locale (comp)'].upper()}): €{row['Price_Comp']:.2f} → Margine: {row['Margine_Netto (%)_Confronto']:.2f}%"
                        
                        st.markdown(origin_market)
                        st.markdown(dest_market)
                    
                    st.markdown("---")
            
            # Pulsante per scaricare i risultati
            csv_data = st.session_state['opportunity_scores'].to_csv(index=False, sep=";").encode("utf-8")
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
        if st.session_state['processed_data'] is not None and not st.session_state['processed_data'].empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Filtro per mercato di destinazione
            all_dest_markets = st.session_state['processed_data']["Locale (comp)"].unique()
            selected_markets = st.multiselect(
                "Filtra per Mercato di Destinazione",
                options=all_dest_markets,
                default=all_dest_markets
            )
            
            filtered_data = st.session_state['processed_data']
            if selected_markets:
                filtered_data = filtered_data[filtered_data["Locale (comp)"].isin(selected_markets)]
            
            # Crea due grafici affiancati
            col1, col2 = st.columns(2)
            
            with col1:
                # Grafico distribuzione margini per mercato
                df_plot = filtered_data.dropna(subset=["Margine_Netto (%)_Confronto"])
                
                if not df_plot.empty:
                    fig = px.box(
                        df_plot,
                        x="Locale (comp)",
                        y="Margine_Netto (%)_Confronto",
                        color="Locale (comp)",
                        title="Distribuzione dei Margini per Mercato",
                        labels={"Locale (comp)": "Mercato di Destinazione", "Margine_Netto (%)_Confronto": "Margine (%)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Dati insufficienti per generare il grafico.")
            
            with col2:
                # Grafico a dispersione Prezzo vs Margine
                df_plot = filtered_data.dropna(subset=["Price_Comp", "Margine_Netto (%)_Confronto"])
                
                if not df_plot.empty:
                    fig = px.scatter(
                        df_plot,
                        x="Price_Comp",
                        y="Margine_Netto (%)_Confronto",
                        color="Locale (comp)",
                        hover_name="Title (base)",
                        hover_data=["ASIN", "Opportunity_Score"],
                        title="Relazione tra Prezzo e Margine",
                        labels={"Price_Comp": "Prezzo di Vendita (€)", "Margine_Netto (%)_Confronto": "Margine (%)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Dati insufficienti per generare il grafico.")
            
            # Grafico istogramma delle opportunità
            df_plot = filtered_data.dropna(subset=["Opportunity_Score"])
            df_plot = df_plot[df_plot["Opportunity_Score"] > 0]
            
            if not df_plot.empty:
                fig = px.histogram(
                    df_plot,
                    x="Opportunity_Score",
                    color="Locale (comp)",
                    nbins=20,
                    title="Distribuzione delle Opportunità",
                    labels={"Opportunity_Score": "Punteggio di Opportunità", "count": "Numero di Prodotti"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Nessuna opportunità positiva trovata per generare il grafico.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Nessun dato disponibile per l'analisi grafica.")
    
    with tab3:
        if st.session_state['processed_data'] is not None and not st.session_state['processed_data'].empty:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("### Tutti i Risultati")
            
            # Aggiungi filtri interattivi
            col1, col2, col3 = st.columns(3)
            with col1:
                min_price = st.number_input("Prezzo Min (€)", value=0.0)
            with col2:
                max_price = st.number_input("Prezzo Max (€)", value=1000.0)
            with col3:
                search_asin = st.text_input("Cerca ASIN", "")
            
            # Applica filtri
            df_display = st.session_state['processed_data'].copy()
            df_display = df_display[df_display["Price_Comp"] >= min_price]
            df_display = df_display[df_display["Price_Comp"] <= max_price]
            
            if search_asin:
                df_display = df_display[df_display["ASIN"].str.contains(search_asin, case=False)]
            
            # Mostra l'intero dataframe con colori condizionali
            st.dataframe(
                df_display.style.applymap(
                    lambda x: "color: green" if isinstance(x, (int, float)) and x > 0 else "color: red" if isinstance(x, (int, float)) and x < 0 else "",
                    subset=["Margine_Netto (€)_Origine", "Margine_Netto (€)_Confronto", "Opportunity_Score"]
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
    
    with tab4:
        if st.session_state['base_asins'] is not None and len(st.session_state['base_asins']) > 0:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("### Lista ASIN")
            
            # Formatta la lista ASIN
            asins = st.session_state['base_asins']
            asins_text = "\n".join(asins)
            
            # Visualizza la lista ASIN
            st.markdown("**ASIN dalla Lista di Origine:**")
            st.markdown(f"<div class='asin-list'>{asins_text}</div>", unsafe_allow_html=True)
            
            # Pulsante per copiare tutti gli ASIN
            st.download_button(
                label="📋 Copia tutti gli ASIN",
                data="\n".join(asins),
                file_name="asin_list.txt",
                mime="text/plain",
            )
            
            # Opzione per filtrare gli ASIN
            search_asin_filter = st.text_input("Filtra ASIN", "")
            if search_asin_filter:
                filtered_asins = [asin for asin in asins if search_asin_filter.upper() in asin]
                filtered_text = "\n".join(filtered_asins)
                st.markdown("**ASIN filtrati:**")
                st.markdown(f"<div class='asin-list'>{filtered_text}</div>", unsafe_allow_html=True)
                
                # Pulsante per copiare gli ASIN filtrati
                st.download_button(
                    label="📋 Copia ASIN filtrati",
                    data="\n".join(filtered_asins),
                    file_name="filtered_asin_list.txt",
                    mime="text/plain",
                    key="filtered_asins"
                )
            
            # Opzione per formattare gli ASIN in diversi modi
            format_options = st.selectbox(
                "Formato visualizzazione:",
                ["Uno per riga", "Separati da virgola", "Separati da tab", "Formato JSON"]
            )
            
            if format_options == "Uno per riga":
                formatted_asins = "\n".join(asins)
            elif format_options == "Separati da virgola":
                formatted_asins = ", ".join(asins)
            elif format_options == "Separati da tab":
                formatted_asins = "\t".join(asins)
            elif format_options == "Formato JSON":
                import json
                formatted_asins = json.dumps(asins)
            
            st.markdown("**ASIN nel formato selezionato:**")
            st.markdown(f"<div class='asin-list'>{formatted_asins}</div>", unsafe_allow_html=True)
            
            # Pulsante per copiare gli ASIN nel formato selezionato
            st.download_button(
                label=f"📋 Copia ASIN ({format_options})",
                data=formatted_asins,
                file_name=f"formatted_asin_list.txt",
                mime="text/plain",
                key="formatted_asins"
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Nessun ASIN disponibile. Carica prima i file di origine.")
else:
    # Pagina iniziale quando non ci sono dati
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("""
    ### 👋 Benvenuto nell'Amazon European Marketplace Arbitrage Calculator!
    
    Questa applicazione ti aiuta a identificare opportunità di arbitraggio tra i diversi marketplace Amazon europei.
    
    #### Come utilizzare l'app:
    
    1. **Carica i file** nella barra laterale:
       - Lista di Origine: file CSV/Excel del mercato base (es. Amazon.it)
       - Liste di Confronto: file CSV/Excel dei mercati di confronto (es. Amazon.de, Amazon.fr)
    
    2. **Configura i parametri**:
       - Seleziona i prezzi di riferimento per origine e confronto
       - Imposta lo sconto per gli acquisti
       - Definisci il costo di spedizione
       - Stabilisci il margine minimo desiderato
    
    3. **Calcola le opportunità** e visualizza i risultati.
    
    #### Funzionalità principali:
    
    - **Analisi Revenue Calculator**: Calcolo preciso di costi e margini secondo il modello ufficiale Amazon
    - **Opportunity Score**: Ranking intelligente delle migliori opportunità di arbitraggio
    - **Visualizzazioni grafiche**: Analisi visiva della distribuzione dei margini e delle opportunità
    - **Esportazione dati**: Scarica i risultati in formato CSV per ulteriori analisi
    - **Gestione ASIN**: Visualizza e copia facilmente la lista degli ASIN per ulteriori analisi
    
    #### Tips per massimizzare i risultati:
    
    - Usa i file più recenti dai marketplace Amazon
    - Confronta lo stesso tipo di prezzo (es. Buy Box vs Buy Box)
    - Considera i costi aggiuntivi per mercati specifici
    - Filtra per un margine minimo adeguato per coprire i rischi
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Mostra esempio/guida
    with st.expander("Guida rapida al formato dei file"):
        st.markdown("""
        ### Formato dei file richiesto
        
        I file CSV/Excel devono contenere almeno le seguenti colonne:
        
        - **ASIN**: codice prodotto Amazon (obbligatorio per il matching)
        - **Title**: titolo del prodotto
        - **Buy Box: Current**: prezzo attuale nella Buy Box
        - **Amazon: Current**: prezzo attuale di Amazon
        - **New: Current**: prezzo attuale del prodotto nuovo
        - **Locale**: codice del marketplace (it, de, fr, es, ecc.)
        - **Categories: Root**: categoria principale del prodotto
        
        **Nota**: Puoi ottenere questi file utilizzando strumenti di scraping o API Amazon.
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

# Funzione Helper per applicare colori condizionali ai margini
def color_negative_red(val):
    """
    Prende un valore scalare e restituisce un colore rosso se negativo, verde se positivo.
    """
    if isinstance(val, (int, float)) and not pd.isna(val):
        if val < 0:
            return 'color: red'
        elif val > 0:
            return 'color: green'
    return ''

# Aggiungi una sezione FAQ
with st.expander("❓ Domande Frequenti"):
    st.markdown("""
    #### Come vengono calcolate le commissioni Amazon?
    Le commissioni vengono calcolate in base alla categoria del prodotto, con percentuali che vanno dal 7% al 15%. Utilizziamo le stesse formule del Revenue Calculator ufficiale di Amazon, inclusa l'imposta sui servizi digitali del 3%.
    
    #### Come funziona il calcolo dello sconto?
    Per i prodotti su Amazon.it, lo sconto viene applicato al prezzo lordo e poi sottratto dal prezzo netto. Per gli altri marketplace, lo sconto viene applicato direttamente al prezzo netto.
    
    #### Cosa significa "Opportunity Score"?
    È un valore calcolato che combina la differenza di margine tra i mercati e il margine percentuale nel mercato di confronto. Un punteggio più alto indica un'opportunità di arbitraggio più vantaggiosa.
    
    #### Posso aggiungere altri marketplace oltre a quelli predefiniti?
    Sì, puoi aggiungere altri marketplace europei nei file di input. Assicurati solo che il codice del marketplace (locale) sia corretto.
    
    #### Quali costi vengono considerati nel calcolo?
    Vengono considerati:
    - Prezzo d'acquisto (con sconto applicato)
    - Commissioni Amazon per categoria
    - Imposta sui servizi digitali
    - Costi di spedizione
    - IVA specifica per ogni marketplace
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
    differenza_margine = margine_confronto - margine_origine
    opportunity_score = differenza_margine * (margine_percentuale_confronto / 100)
    ```
    """)

# Aggiungi statistiche di utilizzo nella sidebar
if 'processed_data' in st.session_state and st.session_state['processed_data'] is not None:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 Statistiche")
        
        total_products = len(st.session_state['processed_data'])
        opportunities_count = len(st.session_state['opportunity_scores']) if st.session_state['opportunity_scores'] is not None else 0
        
        st.markdown(f"**Prodotti analizzati:** {total_products}")
        st.markdown(f"**Opportunità trovate:** {opportunities_count}")
        
        if opportunities_count > 0:
            opportunity_rate = (opportunities_count / total_products) * 100
            st.markdown(f"**Tasso di opportunità:** {opportunity_rate:.1f}%")
            
            # Mostra i mercati più profittevoli
            if st.session_state['opportunity_scores'] is not None and not st.session_state['opportunity_scores'].empty:
                market_stats = st.session_state['opportunity_scores'].groupby("Locale (comp)").agg({
                    "Margine_Netto (%)_Confronto": "mean",
                    "ASIN": "count"
                }).rename(columns={"ASIN": "Count"})
                
                st.markdown("**Mercati più profittevoli:**")
                for locale, stats in market_stats.sort_values("Margine_Netto (%)_Confronto", ascending=False).iterrows():
                    st.markdown(f"- {locale.upper()}: {stats['Margine_Netto (%)_Confronto']:.1f}% (n={stats['Count']})")

# Aggiungi un footer
st.markdown("""
<div class="footer">
    <p>Amazon EU Arbitrage Calculator v1.0</p>
    <p>Sviluppato per l'arbitraggio tra marketplace Amazon europei</p>
    <p>Ultimo aggiornamento: Marzo 2025</p>
</div>
""", unsafe_allow_html=True)

# Aggiungi funzionalità per visualizzare dettagli di un singolo prodotto
if 'processed_data' in st.session_state and st.session_state['processed_data'] is not None:
    with st.expander("🔍 Analisi dettagliata per ASIN"):
        search_asin_detail = st.text_input("Inserisci ASIN da analizzare", "")
        
        if search_asin_detail:
            product_data = st.session_state['processed_data'][st.session_state['processed_data']["ASIN"] == search_asin_detail]
            
            if not product_data.empty:
                product = product_data.iloc[0]
                
                st.markdown(f"## {product['Title (base)']}")
                st.markdown(f"**ASIN:** {product['ASIN']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"### Mercato Origine: {product['Locale (base)'].upper()}")
                    st.markdown(f"**Prezzo di vendita:** €{product['Price_Base']:.2f}")
                    st.markdown(f"**Prezzo netto (IVA esclusa):** €{product['Prezzo_Netto_Origine']:.2f}")
                    st.markdown(f"**Commissioni Amazon:** €{product['Commissioni_Origine']:.2f}")
                    st.markdown(f"**Margine netto:** €{product['Margine_Netto (€)_Origine']:.2f}")
                    st.markdown(f"**Margine percentuale:** {product['Margine_Netto (%)_Origine']:.2f}%")
                
                with col2:
                    st.markdown(f"### Mercato Confronto: {product['Locale (comp)'].upper()}")
                    st.markdown(f"**Prezzo di vendita:** €{product['Price_Comp']:.2f}")
                    st.markdown(f"**Prezzo netto (IVA esclusa):** €{product['Prezzo_Netto_Confronto']:.2f}")
                    st.markdown(f"**Commissioni Amazon:** €{product['Commissioni_Confronto']:.2f}")
                    st.markdown(f"**Margine netto:** €{product['Margine_Netto (€)_Confronto']:.2f}")
                    st.markdown(f"**Margine percentuale:** {product['Margine_Netto (%)_Confronto']:.2f}%")
                
                st.markdown("---")
                st.markdown(f"**Prezzo d'acquisto netto:** €{product['Acquisto_Netto']:.2f}")
                st.markdown(f"**Opportunity Score:** {product['Opportunity_Score']:.2f}")
                
                # Calcola e mostra la differenza di margine
                margin_diff = product['Margine_Netto (€)_Confronto'] - product['Margine_Netto (€)_Origine']
                margin_diff_pct = product['Margine_Netto (%)_Confronto'] - product['Margine_Netto (%)_Origine']
                
                st.markdown(f"**Differenza margine:** €{margin_diff:.2f} ({margin_diff_pct:.2f}%)")
                
                # Aggiungi link ad Amazon
                st.markdown(f"[Vedi su Amazon.{product['Locale (base)'].lower()}](https://www.amazon.{product['Locale (base)'].lower()}/dp/{product['ASIN']})")
                st.markdown(f"[Vedi su Amazon.{product['Locale (comp)'].lower()}](https://www.amazon.{product['Locale (comp)'].lower()}/dp/{product['ASIN']})")
                
                # Visualizza il breakdown dei costi in un grafico
                data_origin = {
                    'Componente': ['Prezzo Netto', 'IVA', 'Commissione', 'Imposta Servizi Digitali'],
                    'Valore': [
                        product['Prezzo_Netto_Origine'],
                        product['Price_Base'] - product['Prezzo_Netto_Origine'],
                        product['Commissioni_Origine'] * 0.97,  # Commissione esclusa imposta
                        product['Commissioni_Origine'] * 0.03   # Imposta servizi digitali
                    ]
                }
                
                data_comp = {
                    'Componente': ['Prezzo Netto', 'IVA', 'Commissione', 'Imposta Servizi Digitali'],
                    'Valore': [
                        product['Prezzo_Netto_Confronto'],
                        product['Price_Comp'] - product['Prezzo_Netto_Confronto'],
                        product['Commissioni_Confronto'] * 0.97,  # Commissione esclusa imposta
                        product['Commissioni_Confronto'] * 0.03   # Imposta servizi digitali
                    ]
                }
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    name=f'Origine ({product["Locale (base)"].upper()})',
                    x=data_origin['Componente'],
                    y=data_origin['Valore'],
                    marker_color='royalblue'
                ))
                
                fig.add_trace(go.Bar(
                    name=f'Confronto ({product["Locale (comp)"].upper()})',
                    x=data_comp['Componente'],
                    y=data_comp['Valore'],
                    marker_color='indianred'
                ))
                
                fig.update_layout(
                    title='Breakdown dei Costi',
                    xaxis_title='Componente',
                    yaxis_title='Euro (€)',
                    barmode='group'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"ASIN {search_asin_detail} non trovato nei dati analizzati.")

# Aggiungi un pulsante per ripristinare le impostazioni predefinite
with st.sidebar:
    st.markdown("---")
    reset_btn = st.button("Ripristina Impostazioni", use_container_width=True)
    
    if reset_btn:
        st.session_state['processed_data'] = None
        st.session_state['opportunity_scores'] = None
        st.session_state['last_update'] = None
        st.session_state['base_asins'] = None
        st.experimental_rerun()