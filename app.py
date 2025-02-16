import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)")

#################################
# Sidebar: Caricamento file e impostazioni
#################################
with st.sidebar:
    st.subheader("Caricamento file")
    
    # File di partenza (dove vuoi comprare)
    files_base = st.file_uploader(
        "Lista di partenza (es. Germania) - multipli (CSV/XLSX)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    base_price_option = st.selectbox(
        "Scegli il prezzo di riferimento per la lista di partenza",
        options=["Buy Box: Current", "Amazon: Current"]
    )
    
    st.markdown("---")
    
    # File di confronto
    comparison_files = st.file_uploader(
        "Liste di confronto (es. Italia) - multipli (CSV/XLSX)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    comparison_price_option = st.selectbox(
        "Scegli il prezzo di riferimento per le liste di confronto",
        options=["Buy Box: Current", "Amazon: Current"]
    )
    
    st.markdown("---")
    # Filtro per "Bought in past month"
    threshold = st.number_input(
        "Filtra i risultati con 'Bought in past month' >= ",
        min_value=0,  # imposta un minimo di 0
        value=0       # valore di default (nessun filtro effettivo)
    )
    
    st.markdown("---")
    avvia_confronto = st.button("Confronta Prezzi")

#################################
# Funzioni di caricamento e pulizia
#################################
def load_data(uploaded_file):
    if not uploaded_file:
        return None
    fname = uploaded_file.name.lower()
    if fname.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, dtype=str)
        return df
    else:
        # Proviamo prima con il separatore ';', altrimenti con ','
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def pulisci_prezzo(prezzo_raw):
    """Rimuove simboli e converte la stringa in float."""
    if not isinstance(prezzo_raw, str):
        return None
    prezzo = prezzo_raw.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(prezzo)
    except:
        return None

#################################
# 1) Caricamento e unificazione della lista di partenza
#################################
df_base = None
if files_base:
    df_base_list = []
    for f in files_base:
        dftemp = load_data(f)
        if dftemp is not None:
            df_base_list.append(dftemp)
    
    if df_base_list:
        df_base = pd.concat(df_base_list, ignore_index=True)
        
        # Mostra la lista unificata degli ASIN se presente
        if "ASIN" in df_base.columns:
            asins = df_base["ASIN"].dropna().unique()
            asins_text = "\n".join(asins)
            st.info("**Lista unificata di ASIN dalla lista di partenza:**")
            st.text_area("Copia qui:", asins_text, height=200)
        else:
            st.warning("Nei file di partenza non è presente la colonna 'ASIN'. Impossibile mostrare la lista.")

#################################
# 2) Confronto prezzi per ciascun file di confronto
#################################
if avvia_confronto:
    # Controlli preliminari
    if not files_base:
        st.warning("Devi prima caricare la lista di partenza.")
        st.stop()
    if not comparison_files:
        st.warning("Devi caricare almeno un file di confronto.")
        st.stop()
    if df_base is None or df_base.empty:
        st.error("La lista di partenza sembra vuota o non caricata correttamente.")
        st.stop()
        
    # Verifica che la lista di partenza contenga le colonne necessarie
    base_required_cols = ["ASIN", "Title", base_price_option]
    missing_base = [col for col in base_required_cols if col not in df_base.columns]
    if missing_base:
        st.error(f"Nella lista di partenza mancano le colonne: {', '.join(missing_base)}.")
        st.stop()
    
    # Calcola il prezzo di riferimento per la lista di partenza
    df_base["Prezzo_base"] = df_base[base_price_option].apply(pulisci_prezzo)
    df_base = df_base[["ASIN", "Title", "Prezzo_base"]]
    
    #################################
    # Elaborazione per ogni file di confronto
    #################################
    for comp_file in comparison_files:
        df_comp = load_data(comp_file)
        if df_comp is None or df_comp.empty:
            st.error(f"Il file di confronto {comp_file.name} è vuoto o non caricato correttamente.")
            continue
        
        # Verifica che il file di confronto contenga le colonne necessarie
        comp_required_cols = ["ASIN", "Bought in past month", "Locale", comparison_price_option]
        missing_comp = [col for col in comp_required_cols if col not in df_comp.columns]
        if missing_comp:
            st.error(f"Nel file di confronto {comp_file.name} mancano le colonne: {', '.join(missing_comp)}.")
            continue
        
        # Calcola il prezzo di riferimento per il file di confronto
        df_comp["Prezzo_comp"] = df_comp[comparison_price_option].apply(pulisci_prezzo)
        df_comp = df_comp[["ASIN", "Locale", "Bought in past month", "Prezzo_comp"]]
        
        # Merge tra la lista di partenza e il file di confronto
        df_merged = pd.merge(df_base, df_comp, on="ASIN", how="inner")
        if df_merged.empty:
            st.warning(f"Nessuna corrispondenza trovata tra la lista di partenza e il file {comp_file.name}.")
            continue
        
        # Filtra i prodotti in cui il prezzo base è minore del prezzo di confronto
        # (significa che conviene comprare nella lista di partenza)
        df_merged = df_merged[df_merged["Prezzo_base"] < df_merged["Prezzo_comp"]]
        
        # Calcolo della differenza percentuale
        # (Prezzo_comp - Prezzo_base) / Prezzo_base * 100
        df_merged["Risparmio_%"] = (
            (df_merged["Prezzo_comp"] - df_merged["Prezzo_base"]) / df_merged["Prezzo_base"]
        ) * 100
        
        # ---- Nuovo filtro su "Bought in past month" ----
        # Convertiamo "Bought in past month" in numero (se non lo è, diventa NaN)
        df_merged["Bought_in_past_month_num"] = pd.to_numeric(df_merged["Bought in past month"], errors='coerce')
        # Sostituiamo gli eventuali NaN con 0 (per evitare errori nel confronto)
        df_merged["Bought_in_past_month_num"] = df_merged["Bought_in_past_month_num"].fillna(0)
        
        # Applichiamo il filtro solo dopo aver fatto il confronto prezzi
        df_merged = df_merged[df_merged["Bought_in_past_month_num"] >= threshold]
        # ---- Fine nuovo filtro ----
        
        # Se dopo il filtro non c'è nulla, avvisiamo
        if df_merged.empty:
            st.info(f"Nessun prodotto soddisfa il filtro 'Bought in past month' >= {threshold} per {comp_file.name}.")
            continue
        
        # Ordina i risultati in ordine decrescente di risparmio
        df_merged = df_merged.sort_values("Risparmio_%", ascending=False)
        
        # Rinomina le colonne di prezzo per chiarezza
        df_merged = df_merged.rename(columns={
            "Prezzo_base": f"Prezzo base ({base_price_option})",
            "Prezzo_comp": f"Prezzo confronto ({comparison_price_option})"
        })
        
        # Seleziona le colonne finali (manteniamo la colonna originale "Bought in past month")
        df_finale = df_merged[[
            "Locale", "ASIN", "Title", "Bought in past month",
            f"Prezzo base ({base_price_option})", f"Prezzo confronto ({comparison_price_option})", "Risparmio_%"
        ]]
        
        # Ricava il "Locale" di confronto (si assume che sia unico per file)
        locale_val = df_finale["Locale"].iloc[0] if not df_finale.empty else "N/D"
        
        st.subheader(f"Risultati di confronto per {comp_file.name} - Paese di confronto: {locale_val}")
        
        st.dataframe(df_finale, height=600)
            
        # Pulsante per il download dei risultati in CSV
        csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label=f"Scarica CSV per {comp_file.name}",
            data=csv_data,
            file_name=f"risultato_convenienza_{comp_file.name}",
            mime="text/csv"
        )
