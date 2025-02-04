import os
import re
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from keepa import Keepa
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env (se presente)
load_dotenv()

st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

# Limite giornaliero delle API (esempio)
API_LIMIT_DAILY = 250
api_requests_count = 0  # Nota: questo contatore non viene persistito tra sessioni

#############################
# FUNZIONI PER LA GESTIONE DELL'API KEY (CIFRATURA CON FERNET)
#############################
def get_fernet():
    key_file = "key.key"
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    else:
        with open(key_file, "rb") as f:
            key = f.read()
    return Fernet(key)

def save_encrypted_api_key(api_key):
    if not re.match(r"^[A-Za-z0-9_-]+$", api_key):
        st.error("Formato API Key non valido!")
        return
    fernet = get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    with open("api_key.enc", "wb") as f:
        f.write(encrypted)
    st.success("API Key salvata in modo sicuro!")

def load_encrypted_api_key():
    if os.path.exists("api_key.enc"):
        fernet = get_fernet()
        with open("api_key.enc", "rb") as f:
            encrypted = f.read()
        try:
            return fernet.decrypt(encrypted).decode()
        except Exception as e:
            st.error("Errore nella decrittazione della API Key!")
            return None
    return None

#############################
# (Opzionale) Funzione per caricare le categorie da file JSON
#############################
@st.cache_data(ttl=86400)
def load_categories_from_file():
    try:
        with open("categories.json", "r", encoding="utf-8") as f:
            categories = json.load(f)
        return categories
    except Exception as e:
        st.error(f"Errore nel caricamento del file categorie: {e}")
        return {}

#############################
# FUNZIONE DI PARSING DEL CSV DI KEEPA (semplice esempio)
#############################
def parse_keepa_csv(csv_data):
    """
    Funzione semplificata per estrarre il prezzo corrente dal CSV.
    Si assume che:
      - csv_data[0] sia il timestamp
      - csv_data[1] sia il prezzo corrente (in centesimi)
    Ritorna un dizionario con 'currentPrice' e 'buyBoxPrice' (uguali in questo esempio).
    """
    current_price = None
    try:
        if isinstance(csv_data, list) and len(csv_data) > 1:
            for val in csv_data[1:]:
                if val != -1:
                    current_price = val / 100.0  # Converti centesimi in euro
                    break
    except Exception as e:
        st.error(f"Errore nel parsing del CSV: {e}")
    return {"currentPrice": current_price, "buyBoxPrice": current_price}

#############################
# FUNZIONE PER TESTARE LA CONNESSIONE CON KEEPA API
#############################
def test_connection(key):
    try:
        api = Keepa(key)
        params = {"domain": 1}
        _ = api.product_finder(params)
        return True
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return False

#############################
# CARICA LA API KEY
#############################
api_key = st.secrets.get("KEEPA_API_KEY") or os.getenv("KEEPA_API_KEY") or load_encrypted_api_key() or "1nf5mcc4mb9li5hc2l9bnuo2oscq0io4f7h26vfeekb9fccr6e9q6hve5aqcbca4"

#############################
# SIDEBAR: CONFIGURAZIONE E FILTRI
#############################
with st.sidebar:
    st.header("⚙️ Configurazione")
    input_api = st.text_input("Inserisci API Key", value="" if api_key is None else api_key, type="password")
    if st.button("Salva API Key"):
        if input_api:
            save_encrypted_api_key(input_api)
            api_key = input_api
        else:
            st.error("Inserisci una API Key valida!")
    st.markdown("---")
    purchase_country = st.selectbox("Paese di Acquisto", ["IT", "DE", "ES"], key="purchase")
    comparison_country = st.selectbox("Paese di Confronto", ["IT", "DE", "ES"], index=0, key="compare")
    st.markdown("---")
    st.markdown("### Filtri di Ricerca")
    min_sales = st.number_input("Vendite minime ultimi 30gg [Paese di Confronto]", min_value=0, max_value=10000, value=0, step=1)
    price_min = st.number_input("Prezzo minimo (€)", min_value=1, max_value=10000, value=10)
    price_max = st.number_input("Prezzo massimo (€)", min_value=1, max_value=10000, value=100)
    st.markdown("---")
    st.markdown("### Inserisci ID Categoria")
    category = st.text_input("Categoria (ID)", value="", placeholder="Inserisci l'ID della categoria")
    st.markdown("---")
    search_trigger = st.button("Cerca")

if api_key:
    if st.button("Test Connection"):
        if test_connection(api_key):
            st.success("Connessione con Keepa API riuscita!")
        else:
            st.error("Connessione con Keepa API fallita!")

#############################
# FUNZIONE PER RECUPERARE DATI LIVE DA KEEPA E UNIRE I RISULTATI PER ASIN
#############################
@st.cache_data(ttl=3600)
def fetch_data(key, purchase_country, comparison_country, min_sales, price_range, category):
    global api_requests_count
    if api_requests_count >= API_LIMIT_DAILY:
        st.error("Limite giornaliero API raggiunto!")
        return pd.DataFrame()
    api_requests_count += 1

    try:
        api = Keepa(key)
        # Parametri per il paese di acquisto:
        params_purchase = {
            "domain": {"IT": 1, "DE": 4, "ES": 3}.get(purchase_country, 1),
            "category": category,
            "minPrice": price_range[0] * 100,
            "maxPrice": price_range[1] * 100
        }
        products_purchase = api.product_finder(params_purchase)
        
        # Parametri per il paese di confronto:
        params_comparison = {
            "domain": {"IT": 1, "DE": 4, "ES": 3}.get(comparison_country, 1),
            "minSalesRank": min_sales
        }
        products_comparison = api.product_finder(params_comparison)
        
        df_purchase = pd.DataFrame(products_purchase)
        df_comparison = pd.DataFrame(products_comparison)
        
        # Parsing del CSV per estrarre il prezzo corrente dal paese di acquisto
        if "csv" in df_purchase.columns:
            df_purchase["amazonCurrent"] = df_purchase["csv"].apply(lambda x: parse_keepa_csv(x)["currentPrice"] if isinstance(x, list) else None)
        # Parsing del CSV per estrarre il prezzo buy box dal paese di confronto
        if "csv" in df_comparison.columns:
            df_comparison["buyBoxCurrent"] = df_comparison["csv"].apply(lambda x: parse_keepa_csv(x)["buyBoxPrice"] if isinstance(x, list) else None)
        
        # Determina il campo chiave per il merge: controlla l'intersezione tra le colonne di df_purchase e df_comparison
        common_keys = set(df_purchase.columns).intersection(set(df_comparison.columns))
        if "ASIN" in common_keys:
            key_field = "ASIN"
        elif "asin" in common_keys:
            key_field = "asin"
        else:
            raise KeyError("Nessun campo ASIN/asin comune trovato nei dati.")
        
        df = pd.merge(df_purchase, df_comparison, on=key_field, suffixes=("_purchase", "_comparison"))
        
        if min_sales > 0 and "salesLastMonth_comparison" in df.columns:
            df = df[df["salesLastMonth_comparison"] >= min_sales]
        
        return df
    except Exception as e:
        st.error(f"Errore durante il fetch dei dati: {e}")
        return pd.DataFrame()

if search_trigger:
    df = fetch_data(api_key, purchase_country, comparison_country, min_sales, (price_min, price_max), category)
    if not df.empty and "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        df["priceDiff"] = df["buyBoxCurrent"] - df["amazonCurrent"]
        df["priceDiffPct"] = df.apply(lambda row: (row["priceDiff"] / row["amazonCurrent"]) * 100 
                                      if row["amazonCurrent"] != 0 else None, axis=1)
else:
    df = pd.DataFrame()

#############################
# SEZIONE RISULTATI
#############################
st.header("Risultati")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    if "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        fig = px.bar(df, x="ASIN" if "ASIN" in df.columns else "asin", y=["amazonCurrent", "buyBoxCurrent"], 
                     title="Prezzi nei due paesi", barmode="group",
                     labels={"value": "Prezzo (€)", "variable": "Tipo"})
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Token residui:** {API_LIMIT_DAILY - api_requests_count} / {API_LIMIT_DAILY}")
else:
    st.info("Premi il pulsante 'Cerca' per visualizzare i risultati.")

st.info("Nota: Se la struttura dei dati reali differisce, adatta il parsing e il merge in base alla documentazione ufficiale di Keepa.")
