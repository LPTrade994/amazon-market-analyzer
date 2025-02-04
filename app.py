import streamlit as st
from keepa import Keepa
import pandas as pd
import plotly.express as px
from cryptography.fernet import Fernet
import os
import re
from datetime import datetime

# Configurazione iniziale
st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

# Mappatura paesi-domini
country_domain_map = {
    "IT": 10, "ES": 8, "DE": 3, "FR": 4,
    "US": 1, "UK": 2, "JP": 6, "CA": 7
}

# Gestione chiave Fernet
if not os.path.exists('.fernet_key'):
    key = Fernet.generate_key()
    with open('.fernet_key', 'wb') as f:
        f.write(key)
else:
    with open('.fernet_key', 'rb') as f:
        key = f.read()
fernet = Fernet(key)

def encrypt_key(api_key):
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_key(encrypted_key):
    return fernet.decrypt(encrypted_key.encode()).decode()

# Caricamento API Key
api_key = None
if 'KEEPA_API_KEY' in os.environ:
    api_key = os.environ['KEEPA_API_KEY']
elif os.path.exists('.encrypted_key'):
    with open('.encrypted_key', 'r') as f:
        encrypted = f.read()
        api_key = decrypt_key(encrypted)[:64]  # Forza lunghezza corretta
elif 'KEEPA_API_KEY' in st.secrets:
    api_key = st.secrets.KEEPA_API_KEY

# Interfaccia utente
with st.sidebar:
    st.header("⚙️ Configurazione")
    
    # Input API Key
    if not api_key:
        api_input = st.text_input("Inserisci API Key Keepa", type="password")
        if api_input:
            # Pulizia input
            cleaned_key = api_input.strip().replace('-', '').replace(' ', '')
            
            # Validazione corretta (64 caratteri alfanumerici)
            if re.match(r'^[A-Za-z0-9]{64}$', cleaned_key):
                with open('.encrypted_key', 'w') as f:
                    f.write(encrypt_key(cleaned_key))
                st.rerun()
            else:
                st.error("Formato API Key non valido!")
                st.error("Deve contenere esattamente 64 caratteri alfanumerici")
                st.error("Esempio: 1nf5mcc4mb9li5hc2l9bnuo2oscq0io4f7h26vfeekb9fccr6e9q6hve5aqcbca4")

    # Selezione paesi
    target_country = st.selectbox("Paese Target", list(country_domain_map.keys()))
    compare_countries = st.multiselect("Paesi Confronto", list(country_domain_map.keys()), default=["DE", "FR"])
    
    # Contatore richieste
    try:
        with open('request_count.txt', 'r') as f:
            count, date = f.read().split(',')
            if datetime.now().strftime('%Y-%m-%d') == date:
                st.info(f"📊 Richieste oggi: {count}/250")
    except:
        pass

# Modalità demo se manca API Key
if not api_key:
    st.warning("Modalità demo - Dati mock")
    df = pd.DataFrame({
        'ASIN': ['B08N5K5C2K', 'B07PGL8ZYS'],
        'Titolo': ['Prodotto Demo 1', 'Prodotto Demo 2'],
        'SalesRank': [150, 300],
        'Prezzo_IT': [49.99, 89.99],
        'Prezzo_DE': [54.99, 84.99]
    })
    st.dataframe(df)
    st.plotly_chart(px.bar(df, x='ASIN', y=['Prezzo_IT', 'Prezzo_DE'], barmode='group'))
    st.stop()

# Logica principale
@st.cache_data(ttl=3600)
def fetch_data(target_domain, compare_domains, filters):
    api = Keepa(api_key)
    
    # Costruzione criteri
    criteria = {'domain': target_domain}
    if filters['min_rank']: criteria['current_SALES_RANK'] = [filters['min_rank'], 999999]
    if filters['price_range']: criteria['current_NEW'] = [filters['price_range'][0], filters['price_range'][1]]
    
    try:
        products = api.product_finder(criteria, product=True)
    except Exception as e:
        st.error(f"Errore API: {str(e)}")
        return pd.DataFrame()

    # Elaborazione risultati
    data = []
    for product in products:
        p_data = {
            'ASIN': product['asin'],
            'Titolo': product.get('title', 'N/A'),
            'SalesRank': product['data'][target_domain].get('SalesRank', 0)
        }
        
        for domain in [target_domain] + compare_domains:
            p_data[f'Prezzo_{domain}'] = product['data'].get(domain, {}).get('New', 0) / 100
        
        data.append(p_data)
    
    return pd.DataFrame(data)

# Filtri ricerca
st.header("🔍 Filtri Ricerca")
min_rank = st.slider("Sales Rank Minimo", 0, 100000, 50000)
price_min = st.slider("Prezzo Minimo (€)", 0, 500, 0)
price_max = st.slider("Prezzo Massimo (€)", 0, 500, 200)

# Recupero dati
target_domain = country_domain_map[target_country]
compare_domains = [country_domain_map[c] for c in compare_countries]
filters = {
    'min_rank': min_rank,
    'price_range': [price_min * 100, price_max * 100]
}

df = fetch_data(target_domain, compare_domains, filters)

# Visualizzazione risultati
if not df.empty:
    st.header("📊 Risultati")
    df = df.sort_values('SalesRank')
    st.dataframe(df.style.highlight_max(axis=0, color='lightgreen'))
    
    # Preparazione dati per grafico
    plot_data = df.melt(id_vars=['ASIN', 'Titolo'], 
                        value_vars=[f'Prezzo_{d}' for d in [target_domain] + compare_domains],
                        var_name='Paese', value_name='Prezzo')
    
    # Mappatura domini a paesi
    domain_to_country = {v: k for k, v in country_domain_map.items()}
    plot_data['Paese'] = plot_data['Paese'].str.split('_').str[1].map(domain_to_country)
    
    # Creazione grafico
    fig = px.bar(plot_data, x='ASIN', y='Prezzo', color='Paese', barmode='group')
    st.plotly_chart(fig)
else:
    st.warning("Nessun risultato trovato con i filtri attuali")

# Aggiornamento contatore richieste
try:
    with open('request_count.txt', 'r') as f:
        count, date = f.read().split(',')
        count = int(count) + 1
except:
    count = 1

with open('request_count.txt', 'w') as f:
    f.write(f"{count},{datetime.now().strftime('%Y-%m-%d')}")