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
        api_key = decrypt_key(f.read())
elif 'KEEPA_API_KEY' in st.secrets:
    api_key = st.secrets.KEEPA_API_KEY

# Interfaccia utente
with st.sidebar:
    st.header("⚙️ Configurazione")
    
    # Input API Key
    if not api_key:
        api_input = st.text_input("Inserisci API Key Keepa", type="password")
        if api_input:
            # Regex corretta per validazione API Key
            if re.match(r'^[a-zA-Z0-9-]{36}$', api_input):
                with open('.encrypted_key', 'w') as f:
                    f.write(encrypt_key(api_input))
                st.rerun()
            else:
                st.error("Formato API Key non valido. Esempio: 1Ab2c3-D4e5... (36 caratteri)")
                st.error(f"Lunghezza inserita: {len(api_input)} caratteri")

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

# ... (il resto del codice rimane invariato come nell'ultima versione fornita)