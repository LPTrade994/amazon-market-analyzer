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
api_requests_count = 0  # Questo contatore non è persistito tra sessioni

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
# FUNZIONE DI PARSING DEL CSV DI KEEPA (VERSIONE SEMPLIFICATA)
#############################
def parse_keepa_csv(csv_data):
    """
    Estrae il prezzo corrente dal CSV.
    - csv_data[0]: timestamp
    - csv_data[1]: prezzo corrente (in centesimi)
    Ritorna un dizionario con 'currentPrice' e 'buyBoxPrice' (uguali in questo esempio).
    """
    current_price = None
    try:
        if isinstance(csv_data, list) and len(csv_data) > 1:
            for val in csv_data[1:]:
                if isinstance(val, (int, float)) and val != -1:
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
        params = {"domain": "US"}
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
    # Ora l'app effettuerà la ricerca in base ai filtri e all'elenco di prodotti ottenuto
    st.markdown("### Ricerca prodotti")
    # Se non viene specificato un elenco di ASIN, l'app utilizzerà product_finder per ottenere l'elenco
    use_manual_asin = st.checkbox("Inserisci manualmente ASIN?", value=False)
    asin_input = ""
    if use_manual_asin:
        asin_input = st.text_input("ASIN (separati da virgola)", value="", placeholder="Es: B0088PUEPK, B01N5IB20Q")
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
# FUNZIONE PER RECUPERARE DATI LIVE DA KEEPA
#############################
@st.cache_data(ttl=3600)
def fetch_data(key, purchase_country, comparison_country, min_sales, price_range, category, asin_input, use_manual_asin):
    global api_requests_count
    if api_requests_count >= API_LIMIT_DAILY:
        st.error("Limite giornaliero API raggiunto!")
        return pd.DataFrame()
    
    api = Keepa(key)
    domain_map = {"IT": "IT", "DE": "DE", "ES": "ES"}
    domain_purchase = domain_map.get(purchase_country, "IT")
    domain_comparison = domain_map.get(comparison_country, "IT")
    
    # Se l'utente inserisce manualmente gli ASIN, usali; altrimenti, usa product_finder per ottenere prodotti
    if use_manual_asin and asin_input.strip() != "":
        asin_list = [a.strip() for a in asin_input.split(",") if a.strip() != ""]
    else:
        # Costruisci parametri per product_finder nel paese di acquisto
        params = {
            "domain": domain_purchase,
            "category": category,
            "minPrice": price_range[0] * 100,
            "maxPrice": price_range[1] * 100
        }
        products_data = api.product_finder(params)
        if isinstance(products_data, dict) and "products" in products_data:
            products_list = products_data["products"]
        else:
            products_list = products_data
        asin_list = []
        for prod in products_list:
            a = prod.get("asin") or prod.get("ASIN")
            if a:
                asin_list.append(a)
    
    if not asin_list:
        st.error("Nessun ASIN trovato con i filtri specificati.")
        return pd.DataFrame()
    
    # Prepara la stringa degli ASIN separati da virgola
    asin_str = ",".join(asin_list)
    
    # Usa query per ottenere dati completi per entrambi i domini
    purchase_data = api.query(asin_str, domain=domain_purchase)
    comparison_data = api.query(asin_str, domain=domain_comparison)
    
    if purchase_data and isinstance(purchase_data, list):
        df_purchase = pd.DataFrame(purchase_data)
    else:
        st.error("Nessun dato ottenuto per il paese di acquisto.")
        return pd.DataFrame()
    
    if comparison_data and isinstance(comparison_data, list):
        df_comparison = pd.DataFrame(comparison_data)
    else:
        st.error("Nessun dato ottenuto per il paese di confronto.")
        return pd.DataFrame()
    
    # Parsing del CSV per estrarre i prezzi
    if "csv" in df_purchase.columns:
        df_purchase["amazonCurrent"] = df_purchase["csv"].apply(lambda x: parse_keepa_csv(x)["currentPrice"] if isinstance(x, list) else None)
    if "csv" in df_comparison.columns:
        df_comparison["buyBoxCurrent"] = df_comparison["csv"].apply(lambda x: parse_keepa_csv(x)["buyBoxPrice"] if isinstance(x, list) else None)
    
    # Individua il campo identificativo; in questo esempio, usiamo "asin" (di solito restituito in minuscolo)
    key_field = "asin"
    if key_field not in df_purchase.columns or key_field not in df_comparison.columns:
        st.write("df_purchase columns:", df_purchase.columns)
        st.write("df_comparison columns:", df_comparison.columns)
        raise KeyError("Nessun campo identificativo comune trovato (cercato: asin).")
    
    df = pd.merge(df_purchase, df_comparison, on=key_field, suffixes=("_purchase", "_comparison"))
    
    # Filtra per vendite minime se il campo è disponibile
    if min_sales > 0 and "salesLastMonth" in df.columns:
        df = df[df["salesLastMonth"] >= min_sales]
    
    # Seleziona solo le colonne rilevanti
    desired_columns = [key_field]
    title_col = "title_purchase" if "title_purchase" in df.columns else ("title" if "title" in df_purchase.columns else None)
    if title_col:
        desired_columns.append(title_col)
    if "amazonCurrent" in df.columns:
        desired_columns.append("amazonCurrent")
    if "buyBoxCurrent" in df.columns:
        desired_columns.append("buyBoxCurrent")
    
    df = df[desired_columns]
    
    return df

# Esegui la ricerca solo se viene premuto "Cerca"
if search_trigger:
    df = fetch_data(api_key, purchase_country, comparison_country, min_sales, (price_min, price_max), category, asin_input, use_manual_asin)
    if not df.empty and "amazonCurrent" in df.columns and "buyBoxCurrent" in df.columns:
        df["priceDiff"] = df["buyBoxCurrent"] - df["amazonCurrent"]
        df["priceDiffPct"] = df.apply(lambda row: (row["priceDiff"] / row["amazonCurrent"]) * 100 
                                      if row["amazonCurrent"] and isinstance(row["amazonCurrent"], (int, float)) else None, axis=1)
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

st.info("Nota: Adatta il parser CSV e il mapping dei campi in base alla documentazione ufficiale di Keepa se necessario.")
