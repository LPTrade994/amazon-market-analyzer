# app.py
import streamlit as st
from keepa import Keepa
import pandas as pd
import plotly.express as px
from cryptography.fernet import Fernet
import os
import re
import csv
from datetime import datetime

# Configurazione iniziale
st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

# Gestione sicura API Key
def setup_encryption():
    if not os.path.exists('.fernet_key'):
        key = Fernet.generate_key()
        with open('.fernet_key', 'wb') as f:
            f.write(key)
    with open('.fernet_key', 'rb') as f:
        return Fernet(f.read())

fernet = setup_encryption()

# Funzioni di gestione API Key
def save_api_key(key):
    encrypted = fernet.encrypt(key.encode()).decode()
    with open('.encrypted_key', 'w') as f:
        f.write(encrypted)

def load_api_key():
    if os.path.exists('.encrypted_key'):
        with open('.encrypted_key', 'r') as f:
            return fernet.decrypt(f.read().encode()).decode()
    return None

# Cache locale
CACHE_FILE = "market_cache.csv"
def save_cache(data):
    data.to_csv(CACHE_FILE, index=False)

def load_cache():
    if os.path.exists(CACHE_FILE):
        return pd.read_csv(CACHE_FILE)
    return None

# Configurazione Paesi
COUNTRIES = {
    "IT": 10, "ES": 8, "DE": 3, "FR": 4,
    "US": 1, "UK": 2, "JP": 6, "CA": 7
}

# UI - Sidebar
with st.sidebar:
    st.header("⚙️ Configurazione")
    
    # Sezione API Key
    api_key = load_api_key() or os.getenv("KEEPA_API_KEY")
    if not api_key:
        api_input = st.text_input("Inserisci API Key Keepa", type="password")
        if st.button("Salva API Key"):
            if re.match(r'^[A-Za-z0-9]{64}$', api_input.strip()):
                save_api_key(api_input)
                st.rerun()
            else:
                st.error("Formato API Key non valido (64 caratteri alfanumerici)")
    
    # Selezione Paesi
    target_country = st.selectbox("Paese Target", list(COUNTRIES.keys()))
    compare_countries = st.multiselect("Paesi Confronto", list(COUNTRIES.keys()))
    
    st.header("🔍 Filtri Ricerca")
    min_rank = st.slider("Sales Rank Minimo", 0, 100000, 50000)
    price_range = st.slider("Range Prezzo (€)", 0, 500, (0, 200))
    category = st.text_input("Categoria Prodotto")
    
    # Contatore Richieste
    try:
        with open('request_count.txt', 'r') as f:
            count, date = f.read().split(',')
            if datetime.now().strftime('%Y-%m-%d') == date:
                st.info(f"📊 Richieste rimaste: {250 - int(count)}/250")
    except:
        pass

# Main UI
st.title("Amazon Market Analyzer 📊")

# Modalità Demo
if not api_key:
    st.warning("Modalità demo - Dati mock")
    df = pd.DataFrame({
        'ASIN': ['B08N5K5C2K', 'B07PGL8ZYS'],
        'Prodotto': ['Prodotto Demo 1', 'Prodotto Demo 2'],
        'SalesRank': [150, 300],
        'Prezzo': [49.99, 89.99],
        'Categoria': ['Elettronica', 'Libri']
    })
    st.dataframe(df.sort_values('SalesRank'))
    st.plotly_chart(px.bar(df, x='Prodotto', y='Prezzo', color='Categoria'))
    st.stop()

# Logica Principale
@st.cache_data(ttl=3600)
def fetch_data():
    cached = load_cache()
    if cached is not None:
        return cached
    
    try:
        api = Keepa(api_key)
        criteria = {
            'domain': COUNTRIES[target_country],
            'current_SALES_RANK': [min_rank, 999999],
            'current_NEW': [price_range[0]*100, price_range[1]*100]
        }
        if category:
            criteria['category'] = category
            
        products = api.product_finder(criteria, product=True)
        data = []
        
        for p in products:
            prices = {}
            for country in [target_country] + compare_countries:
                domain = COUNTRIES[country]
                prices[f'Prezzo_{country}'] = p['data'].get(domain, {}).get('New', 0)/100
            
            data.append({
                'ASIN': p['asin'],
                'Prodotto': p.get('title', 'N/A'),
                'SalesRank': p['data'][COUNTRIES[target_country]].get('SalesRank', 0),
                'Categoria': p.get('category', 'N/A'),
                **prices
            })
            
        df = pd.DataFrame(data)
        save_cache(df)
        return df
        
    except Exception as e:
        st.error(f"Errore API: {str(e)}")
        return pd.DataFrame()

# Esecuzione e Visualizzazione
if st.sidebar.button("Test Connessione"):
    try:
        Keepa(api_key).status()
        st.success("Connessione API riuscita!")
    except Exception as e:
        st.error(f"Errore connessione: {str(e)}")

df = fetch_data()

if not df.empty:
    st.header("Risultati")
    st.dataframe(df.sort_values('SalesRank'))
    
    # Preparazione dati grafico
    price_cols = [c for c in df.columns if c.startswith('Prezzo_')]
    plot_df = df.melt(id_vars=['ASIN', 'Prodotto'], 
                     value_vars=price_cols,
                     var_name='Paese', value_name='Prezzo')
    
    st.plotly_chart(px.bar(plot_df, x='Prodotto', y='Prezzo', 
                          color='Paese', barmode='group',
                          hover_data=['ASIN', 'Categoria']))
else:
    st.warning("Nessun risultato trovato con i filtri selezionati")

# Aggiornamento contatore richieste
try:
    with open('request_count.txt', 'r') as f:
        count, date = f.read().split(',')
        count = int(count) + 1
except:
    count = 1
    date = datetime.now().strftime('%Y-%m-%d')

if count <= 250:
    with open('request_count.txt', 'w') as f:
        f.write(f"{count},{date}")
else:
    st.error("Limite giornaliero richieste API raggiunto!")