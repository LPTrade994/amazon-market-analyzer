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
# Funzioni di cifratura e gestione API Key con Fernet
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
    # Controlla il formato (usa una regex semplice)
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
# Gestione della API Key: prova a caricarla da st.secrets, .env o dal file cifrato
#############################
api_key = st.secrets.get("KEEPA_API_KEY") or os.getenv("KEEPA_API_KEY") or load_encrypted_api_key()

#############################
# Sidebar: Configurazione e test della API Key
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
    # Selezione del Paese target
    country = st.selectbox("Paese Target", ["IT", "ES", "DE", "FR"])
    # Filtri di ricerca
    st.markdown("### Filtri Ricerca")
    min_sales = st.slider("Vendite minime ultimi 30gg", 50, 500, 100)
    price_min, price_max = st.slider("Intervallo Prezzo (€)", 1, 1000, (10, 100))
    category = st.text_input("Categoria (ID o nome)")

#############################
# Funzione per testare la connessione con Keepa API (demo)
#############################
def test_connection(key):
    try:
        api = Keepa(key)
        # Chiamiamo product_finder() solo con il parametro 'domain'
        _ = api.product_finder(domain=1)
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
# Funzione per recuperare dati (modalità demo se API Key non valida)
#############################
@st.cache_data(ttl=3600)
def fetch_data(key, country, min_sales, price_range, category):
    global api_requests_count
    if api_requests_count >= API_LIMIT_DAILY:
        st.error("Limite giornaliero API raggiunto!")
        return pd.DataFrame()
    api_requests_count += 1

    if key and test_connection(key):
        try:
            api = Keepa(key)
            query_params = {
                "domain": {"IT": 1, "ES": 3, "DE": 4, "FR": 5}.get(country, 1),
                "minSalesRank": min_sales,
                "minPrice": price_range[0] * 100,  # Keepa usa centesimi
                "maxPrice": price_range[1] * 100,
                "category": category if category else None,
            }
            # Chiamata a product_finder() senza parametro "query"
            products = api.product_finder(**{k: v for k, v in query_params.items() if v is not None})
            df = pd.DataFrame(products)
            if df.empty:
                st.warning("Nessun prodotto trovato con i filtri impostati.")
            return df
        except Exception as e:
            st.error(f"Errore durante il fetch dei dati: {e}")
            return pd.DataFrame()
    else:
        # Modalità demo: dati di esempio
        data = {
            "ASIN": ["B0001", "B0002", "B0003"],
            "SalesRank": [120, 250, 75],
            "Prezzo": [19.99, 29.99, 9.99]
        }
        return pd.DataFrame(data)

df = fetch_data(api_key, country, min_sales, (price_min, price_max), category)

#############################
# Sezione Risultati
#############################
st.header("Risultati")
if not df.empty:
    st.dataframe(df.sort_values("SalesRank"), use_container_width=True)
    if "Prezzo" in df.columns:
        fig = px.bar(df, x="ASIN", y="Prezzo", title="Differenze Prezzi per Prodotto")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Token residui:** {API_LIMIT_DAILY - api_requests_count} / {API_LIMIT_DAILY}")
else:
    st.info("Nessun dato disponibile da mostrare.")
