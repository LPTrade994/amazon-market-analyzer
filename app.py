import os
import re
import streamlit as st
import pandas as pd
import plotly.express as px
from keepa import Keepa
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env se presente
load_dotenv()

st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

# Limite giornaliero delle API (esempio)
API_LIMIT_DAILY = 250
api_requests_count = 0  # (Per semplicità, questo contatore non viene persistito)

#############################
# Funzioni per gestione API Key (cifratura con Fernet)
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

# Carica la API Key da st.secrets, .env o dal file cifrato
api_key = st.secrets.get("KEEPA_API_KEY") or os.getenv("KEEPA_API_KEY") or load_encrypted_api_key()

#############################
# Sidebar: Configurazione e filtri
#############################
with st.sidebar:
    st.header("⚙️ Configurazione")
    # Campo per inserire la API Key (in modalità password)
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
    # Filtri di ricerca
    st.markdown("### Filtri di Ricerca")
    # Filtro per vendite minime (input numerico), che può essere impostato a 0 (disattivato)
    min_sales = st.number_input("Vendite minime ultimi 30gg [Paese di Confronto]", min_value=0, max_value=10000, value=0, step=1)
    # Input manuale per intervallo di prezzo
    price_min = st.number_input("Prezzo minimo (€)", min_value=1, max_value=10000, value=10)
    price_max = st.number_input("Prezzo massimo (€)", min_value=1, max_value=10000, value=100)
    category = st.text_input("Categoria (ID o nome)")
    st.markdown("---")
    # Pulsante per avviare la ricerca
    search_trigger = st.button("Cerca")

#############################
# Funzione per testare la connessione con Keepa API (di base)
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

if api_key:
    if st.button("Test Connection"):
        if test_connection(api_key):
            st.success("Connessione con Keepa API riuscita!")
        else:
            st.error("Connessione con Keepa API fallita!")

#############################
# Funzione per recuperare dati (modalità demo o reale)
#############################
@st.cache_data(ttl=3600)
def fetch_data(key, purchase_country, comparison_country, min_sales, price_range, category):
    global api_requests_count
    if api_requests_count >= API_LIMIT_DAILY:
        st.error("Limite giornaliero API raggiunto!")
        return pd.DataFrame()
    api_requests_count += 1

    if key and test_connection(key):
        try:
            api = Keepa(key)
            # Qui dovresti passare i parametri reali per la chiamata all'API,
            # inclusi eventuali parametri specifici per il paese di acquisto e di confronto.
            # Per questo esempio, simuliamo i dati reali:
            data = {
                "ASIN": ["B0001", "B0002", "B0003"],
                "title": ["Prodotto 1", "Prodotto 2", "Prodotto 3"],
                # Vendite del mese scorso riferite al paese di confronto
                "salesLastMonth": [100, 200, 150],
                # Prezzo nel paese di acquisto (ad esempio, se purchase_country == "ES")
                "amazonCurrent": [19.99, 29.99, 9.99],
                # Prezzo nel paese di confronto (ad esempio, se comparison_country == "IT")
                "buyBoxCurrent": [21.99, 27.99, 10.99]
            }
            df = pd.DataFrame(data)
            # Applica il filtro delle vendite se il valore è maggiore di 0
            if min_sales > 0 and "salesLastMonth" in df.columns:
                df = df[df["salesLastMonth"] >= min_sales]
            return df
        except Exception as e:
            st.error(f"Errore durante il fetch dei dati: {e}")
            return pd.DataFrame()
    else:
        # Modalità demo: dati di esempio
        data = {
            "ASIN": ["B0001", "B0002", "B0003"],
            "title": ["Prodotto 1", "Prodotto 2", "Prodotto 3"],
            "salesLastMonth": [100, 200, 150],
            "amazonCurrent": [19.99, 29.99, 9.99],
            "buyBoxCurrent": [21.99, 27.99, 10.99]
        }
        df = pd.DataFrame(data)
        if min_sales > 0:
            df = df[df["salesLastMonth"] >= min_sales]
        return df

# Esegui la ricerca solo se viene premuto il pulsante "Cerca"
if search_trigger:
    df = fetch_data(api_key, purchase_country, comparison_country, min_sales, (price_min, price_max), category)
    if not df.empty and "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        df["priceDiff"] = df["buyBoxCurrent"] - df["amazonCurrent"]
        df["priceDiffPct"] = df.apply(lambda row: (row["priceDiff"] / row["amazonCurrent"]) * 100 if row["amazonCurrent"] != 0 else None, axis=1)
else:
    df = pd.DataFrame()

#############################
# Sezione Risultati
#############################
st.header("Risultati")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    if "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        fig = px.bar(df, x="ASIN", y=["amazonCurrent", "buyBoxCurrent"], 
                     title="Prezzi nei due paesi", barmode="group",
                     labels={"value": "Prezzo (€)", "variable": "Tipo"})
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Token residui:** {API_LIMIT_DAILY - api_requests_count} / {API_LIMIT_DAILY}")
else:
    st.info("Premi il pulsante 'Cerca' per visualizzare i risultati.")

# Messaggio per il testing:
st.info("Nota: Attualmente i dati sono in modalità demo. Per ottenere dati reali, assicurati di utilizzare una API Key valida e implementa la logica di fetch dalla API di Keepa.")
