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
# Se preferisci inserire manualmente l'ID della categoria, questa parte non è utilizzata.
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
# Funzione per testare la connessione con Keepa API
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
# Carica la API Key da st.secrets, .env o dal file cifrato.
# Se non disponibile, usa la chiave fornita (non usarla in produzione).
#############################
api_key = st.secrets.get("KEEPA_API_KEY") or os.getenv("KEEPA_API_KEY") or load_encrypted_api_key() or "1nf5mcc4mb9li5hc2l9bnuo2oscq0io4f7h26vfeekb9fccr6e9q6hve5aqcbca4"

#############################
# Sidebar: Configurazione e filtri
#############################
with st.sidebar:
    st.header("⚙️ Configurazione")
    # Campo per inserire la API Key (password)
    input_api = st.text_input("Inserisci API Key", value="" if api_key is None else api_key, type="password")
    if st.button("Salva API Key"):
        if input_api:
            save_encrypted_api_key(input_api)
            api_key = input_api
        else:
            st.error("Inserisci una API Key valida!")
    st.markdown("---")
    # Selezione dei paesi: Amazon.it, Amazon.de, Amazon.es
    purchase_country = st.selectbox("Paese di Acquisto", ["IT", "DE", "ES"], key="purchase")
    comparison_country = st.selectbox("Paese di Confronto", ["IT", "DE", "ES"], index=0, key="compare")
    st.markdown("---")
    # Filtri di Ricerca
    st.markdown("### Filtri di Ricerca")
    # Input numerico per le vendite minime (per il paese di confronto)
    min_sales = st.number_input("Vendite minime ultimi 30gg [Paese di Confronto]", min_value=0, max_value=10000, value=0, step=1)
    # Input manuale per l'intervallo di prezzo
    price_min = st.number_input("Prezzo minimo (€)", min_value=1, max_value=10000, value=10)
    price_max = st.number_input("Prezzo massimo (€)", min_value=1, max_value=10000, value=100)
    st.markdown("---")
    # Campo per inserire manualmente l'ID della Categoria
    st.markdown("### Inserisci ID Categoria")
    category = st.text_input("Categoria (ID)", value="", placeholder="Inserisci l'ID della categoria")
    st.markdown("---")
    # Pulsante per avviare la ricerca (per ridurre chiamate automatiche e token consumati)
    search_trigger = st.button("Cerca")

#############################
# Test della connessione (opzionale)
#############################
if api_key:
    if st.button("Test Connection"):
        if test_connection(api_key):
            st.success("Connessione con Keepa API riuscita!")
        else:
            st.error("Connessione con Keepa API fallita!")

#############################
# Funzione per recuperare dati reali da Keepa e unirli per ASIN
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
            "category": category,  # l'ID inserito manualmente
            "minPrice": price_range[0] * 100,  # Convertito in centesimi
            "maxPrice": price_range[1] * 100
        }
        products_purchase = api.product_finder(params_purchase)
        
        # Parametri per il paese di confronto:
        params_comparison = {
            "domain": {"IT": 1, "DE": 4, "ES": 3}.get(comparison_country, 1),
            "minSalesRank": min_sales
        }
        products_comparison = api.product_finder(params_comparison)
        
        # Converti le risposte in DataFrame
        df_purchase = pd.DataFrame(products_purchase)
        df_comparison = pd.DataFrame(products_comparison)
        
        # Debug: visualizza i primi record (puoi rimuovere in produzione)
        st.write("Dati Paese di Acquisto:", df_purchase.head())
        st.write("Dati Paese di Confronto:", df_comparison.head())
        
        # Unisci i dati basandoti su ASIN (assicurati che il campo ASIN esista in entrambe le risposte)
        df = pd.merge(df_purchase, df_comparison, on="ASIN", suffixes=("_purchase", "_comparison"))
        
        # Applica il filtro delle vendite, se min_sales > 0, sul campo delle vendite del paese di confronto
        if min_sales > 0 and "salesLastMonth_comparison" in df.columns:
            df = df[df["salesLastMonth_comparison"] >= min_sales]
        
        return df
    except Exception as e:
        st.error(f"Errore durante il fetch dei dati: {e}")
        return pd.DataFrame()

if search_trigger:
    df = fetch_data(api_key, purchase_country, comparison_country, min_sales, (price_min, price_max), category)
    if not df.empty and "amazonCurrent_purchase" in df.columns and "buyBoxCurrent_comparison" in df.columns:
        df["priceDiff"] = df["buyBoxCurrent_comparison"] - df["amazonCurrent_purchase"]
        df["priceDiffPct"] = df.apply(lambda row: (row["priceDiff"] / row["amazonCurrent_purchase"]) * 100 
                                      if row["amazonCurrent_purchase"] != 0 else None, axis=1)
else:
    df = pd.DataFrame()

#############################
# Sezione Risultati
#############################
st.header("Risultati")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    if "amazonCurrent_purchase" in df.columns and "buyBoxCurrent_comparison" in df.columns:
        fig = px.bar(df, x="ASIN", y=["amazonCurrent_purchase", "buyBoxCurrent_comparison"], 
                     title="Prezzi nei due paesi", barmode="group",
                     labels={"value": "Prezzo (€)", "variable": "Tipo"})
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Token residui:** {API_LIMIT_DAILY - api_requests_count} / {API_LIMIT_DAILY}")
else:
    st.info("Premi il pulsante 'Cerca' per visualizzare i risultati.")

st.info("Nota: Se la struttura dei dati reali restituiti da Keepa differisce, adatta i nomi dei campi nel merge e nel calcolo delle differenze. Consulta la documentazione ufficiale di Keepa per i dettagli.")
