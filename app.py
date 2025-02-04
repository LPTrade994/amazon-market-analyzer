import os
import re
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from keepa import Keepa
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env, se presente
load_dotenv()

st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

# Limite giornaliero delle API (esempio)
API_LIMIT_DAILY = 250
api_requests_count = 0  # Non persistito tra sessioni

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
# FUNZIONE DI PARSING DEL CSV DI KEEPA (VERSIONE SEMPLIFICATA)
#############################
def parse_keepa_csv(csv_data):
    """
    Estrae il prezzo corrente dal CSV.
    Si assume che csv_data[0] sia il timestamp e csv_data[1] il prezzo corrente (in centesimi).
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
    input_api = st.text_input("Inserisci API Key", value=api_key, type="password")
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
    st.markdown("### Inserisci ASIN (separati da virgola)")
    asin_input = st.text_input("ASIN", value="", placeholder="Es: B0088PUEPK, B01N5IB20Q")
    st.markdown("---")
    st.markdown("### Inserisci ID Categoria (facoltativo)")
    category = st.text_input("Categoria (ID)", value="", placeholder="Inserisci l'ID della categoria, o lascia vuoto")
    st.markdown("---")
    search_trigger = st.button("Cerca")

if api_key:
    if st.button("Test Connection"):
        if test_connection(api_key):
            st.success("Connessione con Keepa API riuscita!")
        else:
            st.error("Connessione con Keepa API fallita!")

#############################
# FUNZIONE PER RECUPERARE DATI LIVE PER OGNI ASIN
#############################
@st.cache_data(ttl=3600)
def fetch_data(key, purchase_country, comparison_country, min_sales, price_range, category, asin_input):
    global api_requests_count
    if api_requests_count >= API_LIMIT_DAILY:
        st.error("Limite giornaliero API raggiunto!")
        return pd.DataFrame()
    api = Keepa(key)
    asin_list = [a.strip() for a in asin_input.split(",") if a.strip() != ""]
    data_purchase = []
    data_comparison = []
    
    # Codice di dominio: utilizza la mappatura per ciascun paese
    domain_map = {"IT": 1, "DE": 4, "ES": 3}
    domain_purchase = domain_map.get(purchase_country, 1)
    domain_comparison = domain_map.get(comparison_country, 1)
    
    for asin in asin_list:
        try:
            # Per ciascun ASIN, effettua due query: una per il paese di acquisto e una per il paese di confronto.
            prod_purchase = api.query(asin, domain=domain_purchase)
            prod_comparison = api.query(asin, domain=domain_comparison)
            # Se la risposta è valida e contiene almeno un prodotto, aggiungila
            if prod_purchase and isinstance(prod_purchase, list):
                data_purchase.append(prod_purchase[0])
            if prod_comparison and isinstance(prod_comparison, list):
                data_comparison.append(prod_comparison[0])
        except Exception as e:
            st.error(f"Errore per ASIN {asin}: {e}")
    
    if not data_purchase or not data_comparison:
        st.error("Nessun dato recuperato per uno o più ASIN.")
        return pd.DataFrame()
    
    df_purchase = pd.DataFrame(data_purchase)
    df_comparison = pd.DataFrame(data_comparison)
    
    # Parsing del CSV per estrarre il prezzo corrente (paese di acquisto)
    if "csv" in df_purchase.columns:
        df_purchase["amazonCurrent"] = df_purchase["csv"].apply(lambda x: parse_keepa_csv(x)["currentPrice"] if isinstance(x, list) else None)
    # Parsing del CSV per estrarre il prezzo buy box (paese di confronto)
    if "csv" in df_comparison.columns:
        df_comparison["buyBoxCurrent"] = df_comparison["csv"].apply(lambda x: parse_keepa_csv(x)["buyBoxPrice"] if isinstance(x, list) else None)
    
    # Verifica il campo identificativo: si assume che la query restituisca "asin" in minuscolo
    key_field = "asin"
    if key_field not in df_purchase.columns or key_field not in df_comparison.columns:
        st.write("df_purchase columns:", df_purchase.columns)
        st.write("df_comparison columns:", df_comparison.columns)
        raise KeyError("Nessun campo identificativo comune trovato per ASIN.")
    
    df = pd.merge(df_purchase, df_comparison, on=key_field, suffixes=("_purchase", "_comparison"))
    
    # Applica filtri opzionali: ad esempio, filtrare per vendite minime (se presente)
    if min_sales > 0 and "salesLastMonth" in df.columns:
        df = df[df["salesLastMonth"] >= min_sales]
    
    return df

if search_trigger:
    df = fetch_data(api_key, purchase_country, comparison_country, min_sales, (price_min, price_max), category, asin_input)
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
    key_col = "ASIN" if "ASIN" in df.columns else "asin"
    if "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        fig = px.bar(df, x=key_col, y=["amazonCurrent", "buyBoxCurrent"],
                     title="Prezzi nei due paesi", barmode="group",
                     labels={"value": "Prezzo (€)", "variable": "Tipo"})
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Token residui:** {API_LIMIT_DAILY - api_requests_count} / {API_LIMIT_DAILY}")
else:
    st.info("Premi il pulsante 'Cerca' per visualizzare i risultati.")

st.info("Nota: Se la struttura dei dati reali differisce, adatta il parsing in base alla documentazione ufficiale di Keepa.")
