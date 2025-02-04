# app.py
import os
import re
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from keepa import Keepa
from datetime import datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Configurazione iniziale
st.set_page_config(
    page_title="Amazon Market Analyzer Pro",
    layout="wide",
    page_icon="📊"
)

# Costanti
API_LIMIT_DAILY = 250
CURRENCY_RATES = {
    'IT': {'code': 'EUR', 'rate': 1.0},
    'DE': {'code': 'EUR', 'rate': 1.0},
    'ES': {'code': 'EUR', 'rate': 1.0}
}

#############################
# Gestione API Key (Sicurezza Enhanced)
#############################
def initialize_fernet():
    key_path = "fernet.key"
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
    return Fernet(open(key_path, "rb").read())

def secure_api_key(api_key):
    fernet = initialize_fernet()
    encrypted_key = fernet.encrypt(api_key.encode())
    with open("api_key.enc", "wb") as key_file:
        key_file.write(encrypted_key)
    st.success("🔑 API Key salvata in modo sicuro!")

def load_api_key():
    try:
        if 'KEEPA_API_KEY' in st.secrets:
            return st.secrets['KEEPA_API_KEY']
        
        if os.getenv("KEEPA_API_KEY"):
            return os.getenv("KEEPA_API_KEY")
        
        if os.path.exists("api_key.enc"):
            fernet = initialize_fernet()
            with open("api_key.enc", "rb") as key_file:
                return fernet.decrypt(key_file.read()).decode()
        
        return None
    except Exception as e:
        st.error(f"Errore crittografia: {str(e)}")
        return None

#############################
# Gestione Limite API (Persistente)
#############################
def update_api_counter(requests_made):
    today = datetime.now().strftime("%Y-%m-%d")
    counter_file = "api_counter.json"
    
    try:
        if os.path.exists(counter_file):
            with open(counter_file, "r") as f:
                data = json.load(f)
                if data.get('date') == today:
                    data['count'] += requests_made
                else:
                    data = {'date': today, 'count': requests_made}
        else:
            data = {'date': today, 'count': requests_made}
        
        with open(counter_file, "w") as f:
            json.dump(data, f)
            
        return data['count']
    except Exception as e:
        st.error(f"Errore contatore API: {str(e)}")
        return 0

def get_api_usage():
    counter_file = "api_counter.json"
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            data = json.load(f)
            if data.get('date') == datetime.now().strftime("%Y-%m-%d"):
                return data['count']
    return 0

#############################
# Core Functions
#############################
@st.cache_data(ttl=3600, show_spinner="Recupero dati da Keepa...")
def fetch_keepa_data(_api, params, domain):
    try:
        return _api.product_finder(params, domain=domain)
    except Exception as e:
        st.error(f"Errore Keepa API: {str(e)}")
        return None

def parse_keepa_prices(csv_data):
    """Parsing corretto secondo documentazione Keepa"""
    try:
        return {
            'current': csv_data[3][-1] / 100 if csv_data[3] and csv_data[3][-1] > 0 else None,
            'buybox': csv_data[18][-1] / 100 if csv_data[18] and csv_data[18][-1] > 0 else None
        }
    except (IndexError, TypeError):
        return {'current': None, 'buybox': None}

def convert_currency(price, from_country, to_country):
    rate_from = CURRENCY_RATES[from_country]['rate']
    rate_to = CURRENCY_RATES[to_country]['rate']
    return (price / rate_from) * rate_to

#############################
# UI Configuration
#############################
def main():
    st.title("🛍️ Amazon Market Analyzer Pro")
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configurazione")
        api_key_input = st.text_input("Inserisci API Key Keepa", type="password")
        
        if api_key_input:
            if st.button("Salva API Key"):
                if re.match(r"^[A-Za-z0-9_-]{20,}$", api_key_input):
                    secure_api_key(api_key_input)
                else:
                    st.error("Formato API Key non valido!")
        
        st.markdown("---")
        purchase_country = st.selectbox("Paese Acquisto", ["IT", "DE", "ES"], index=0)
        comparison_country = st.selectbox("Paese Confronto", ["IT", "DE", "ES"], index=1)
        
        st.markdown("---")
        with st.expander("Filtri Avanzati"):
            min_sales = st.number_input("Vendite minime (30gg)", min_value=0, value=10)
            price_range = st.slider("Range Prezzo (€)", 1, 500, (20, 200))
            category_id = st.text_input("ID Categoria Keepa", "")
        
        st.markdown("---")
        if st.button("🔍 Avvia Analisi", type="primary"):
            st.session_state.analysis_triggered = True

    # Main Content
    api_key = load_api_key()
    
    if not api_key:
        st.warning("⚠️ Inserisci una API Key valida nella sidebar")
        st.stop()
    
    if get_api_usage() >= API_LIMIT_DAILY:
        st.error("❌ Limite giornaliero API raggiunto!")
        st.stop()
    
    if 'analysis_triggered' in st.session_state:
        with st.spinner("Analisi in corso..."):
            try:
                keepa_api = Keepa(api_key)
                
                # Recupera dati paese acquisto
                params = {
                    "categories": [category_id] if category_id else [],
                    "current_SALES_gte": min_sales,
                    "current_AMAZON_gte": price_range[0] * 100,
                    "current_AMAZON_lte": price_range[1] * 100
                }
                
                purchase_data = fetch_keepa_data(keepa_api, params, purchase_country)
                comparison_data = fetch_keepa_data(keepa_api, params, comparison_country)
                
                # CORREZIONE CRUCIALE: Gestione struttura dati corretta
                def process_api_response(data):
                    if isinstance(data, dict):
                        return data.get('products', [])
                    elif isinstance(data, list):
                        return data
                    return []
                
                purchase_products = process_api_response(purchase_data)
                comparison_products = process_api_response(comparison_data)
                
                processed_data = []
                for product in purchase_products:
                    if not isinstance(product, dict):
                        continue
                    
                    prices = parse_keepa_prices(product.get('csv', []))
                    
                    # Conversione valuta
                    converted_price = None
                    if prices['current'] is not None:
                        converted_price = convert_currency(
                            prices['current'],
                            purchase_country,
                            comparison_country
                        )
                    
                    processed_data.append({
                        'ASIN': product.get('asin'),
                        'Titolo': product.get('title'),
                        f'Prezzo {purchase_country}': prices['current'],
                        f'Prezzo {comparison_country}': converted_price,
                        'Buy Box': prices['buybox'],
                        'Vendite Ultimo Mese': product.get('salesLast30')
                    })
                
                update_api_counter(len(purchase_products))
                
                # Visualizza risultati
                df = pd.DataFrame(processed_data)
                if not df.empty:
                    st.success(f"🎯 {len(df)} prodotti trovati")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(df, use_container_width=True)
                    
                    with col2:
                        fig = px.bar(df, 
                            x='Titolo', 
                            y=[f'Prezzo {purchase_country}', f'Prezzo {comparison_country}'],
                            title="Confronto Prezzi",
                            labels={'value': 'Prezzo (€)', 'variable': 'Paese'},
                            barmode='group')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.metric("Token Rimasti", f"{API_LIMIT_DAILY - get_api_usage()}/{API_LIMIT_DAILY}")
                else:
                    st.warning("Nessun risultato trovato con i filtri selezionati")
            
            except Exception as e:
                st.error(f"Errore durante l'analisi: {str(e)}")

if __name__ == "__main__":
    main()