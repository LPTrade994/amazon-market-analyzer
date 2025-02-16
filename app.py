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
    
    # Lista di partenza (dove vuoi comprare)
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
    
    # Liste di confronto (es. Italia, Francia, etc.)
    comparison_files = st.file_uploader(
        "Liste di confronto - multipli (CSV/XLSX)",
        type=["csv", "xlsx"],
        accept_multiple_files=True
    )
    comparison_price_option = st.selectbox(
        "Scegli il prezzo di riferimento per le liste di confronto",
        options=["Buy Box: Current", "Amazon: Current"]
    )
    
    st.markdown("---")
    # Filtro per "Bought in past month" (applicato sui confronti individuali)
    threshold_bought = st.number_input(
        "Filtra i risultati (per ogni mercato) con 'Bought in past month' >= ",
        min_value=0,
        value=0
    )
    
    st.markdown("---")
    # Opzione per visualizzare anche la tabella aggregata
    show_aggregated = st.checkbox("Mostra tabella aggregata (prodotti convenienti su più mercati)")
    # Filtro: minimo numero di mercati in cui il prodotto deve risultare conveniente
    min_markets_convenient = st.number_input(
        "Mostra solo prodotti convenienti in almeno n mercati:",
        min_value=1,
        value=1
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
        try:
            df = pd.read_csv(uploaded_file, sep=";", dtype=str)
            return df
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=",", dtype=str)
            return df

def pulisci_prezzo(prezzo_raw):
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
# 2) Confronto individuale per ciascun file di confronto
#################################
if avvia_confronto:
    if not files_base:
        st.warning("Devi prima caricare la lista di partenza.")
        st.stop()
    if not comparison_files:
        st.warning("Devi caricare almeno un file di confronto.")
        st.stop()
    if df_base is None or df_base.empty:
        st.error("La lista di partenza sembra vuota o non caricata correttamente.")
        st.stop()
        
    # Verifica colonne necessarie nella lista di partenza
    base_required_cols = ["ASIN", "Title", base_price_option]
    missing_base = [col for col in base_required_cols if col not in df_base.columns]
    if missing_base:
        st.error(f"Nella lista di partenza mancano le colonne: {', '.join(missing_base)}.")
        st.stop()
    
    # Calcola il prezzo di riferimento per la lista di partenza
    df_base["Prezzo_base"] = df_base[base_price_option].apply(pulisci_prezzo)
    df_base = df_base[["ASIN", "Title", "Prezzo_base"]]
    
    # Lista per raccogliere i dati elaborati per l'aggregazione
    agg_list = []
    
    st.markdown("## Risultati per singolo mercato di confronto")
    for comp_file in comparison_files:
        df_comp = load_data(comp_file)
        if df_comp is None or df_comp.empty:
            st.error(f"Il file di confronto {comp_file.name} è vuoto o non caricato correttamente.")
            continue
        
        # Verifica colonne necessarie nel file di confronto
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
        
        # Filtra: mostra solo i prodotti in cui il prezzo base è minore di quello di confronto
        df_merged = df_merged[df_merged["Prezzo_base"] < df_merged["Prezzo_comp"]]
        
        # Calcolo della differenza percentuale
        df_merged["Risparmio_%"] = ((df_merged["Prezzo_comp"] - df_merged["Prezzo_base"]) / df_merged["Prezzo_base"]) * 100
        
        # Filtro sul "Bought in past month"
        df_merged["Bought_in_past_month_num"] = pd.to_numeric(df_merged["Bought in past month"], errors='coerce').fillna(0)
        df_merged = df_merged[df_merged["Bought_in_past_month_num"] >= threshold_bought]
        
        if df_merged.empty:
            st.info(f"Nessun prodotto soddisfa il filtro 'Bought in past month' >= {threshold_bought} per {comp_file.name}.")
            continue
        
        # Ordina per risparmio decrescente
        df_merged = df_merged.sort_values("Risparmio_%", ascending=False)
        
        # Rinomina le colonne di prezzo per chiarezza
        df_merged = df_merged.rename(columns={
            "Prezzo_base": f"Prezzo base ({base_price_option})",
            "Prezzo_comp": f"Prezzo confronto ({comparison_price_option})"
        })
        
        # Seleziona le colonne finali
        df_finale = df_merged[[
            "Locale", "ASIN", "Title", "Bought in past month",
            f"Prezzo base ({base_price_option})", f"Prezzo confronto ({comparison_price_option})", "Risparmio_%"
        ]]
        
        # Ottieni il valore di Locale (si assume che sia unico nel file)
        locale_val = df_finale["Locale"].iloc[0] if not df_finale.empty else "N/D"
        
        st.subheader(f"Risultati di confronto per {comp_file.name} - Paese di confronto: {locale_val}")
        st.dataframe(df_finale, height=600)
        
        csv_data = df_finale.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label=f"Scarica CSV per {comp_file.name}",
            data=csv_data,
            file_name=f"risultato_convenienza_{comp_file.name}",
            mime="text/csv"
        )
        
        # Prepara i dati per l'aggregazione:
        # Prendiamo per ogni file: ASIN, Prezzo_comp, Bought in past month e Locale.
        # Useremo il valore unico di Locale come identificatore del mercato.
        market = df_comp["Locale"].dropna().unique()[0]  # si assume che in ciascun file sia unico
        df_temp = df_comp.copy()
        # Manteniamo solo una riga per ASIN (in caso di duplicati, prendiamo la prima)
        df_temp = df_temp.drop_duplicates(subset="ASIN")
        df_temp = df_temp[["ASIN", "Prezzo_comp", "Bought in past month"]]
        # Rinominiamo le colonne per questo mercato
        df_temp = df_temp.rename(columns={
            "Prezzo_comp": f"Prezzo_{market}",
            "Bought in past month": f"Bought_{market}"
        })
        # Aggiungiamo una colonna per il mercato (utile in aggregazione)
        df_temp["Market"] = market
        
        # Salviamo il dataframe per la fase aggregata
        agg_list.append(df_temp)
    
    #################################
    # 3) Tabella aggregata (prodotti convenienti su più mercati)
    #################################
    if show_aggregated:
        st.markdown("## Risultati Aggregati (prodotti convenienti su più mercati)")
        if df_base is None or df_base.empty:
            st.error("La lista di partenza non è disponibile per l'aggregazione.")
        else:
            # Partiamo dalla lista di partenza con ASIN, Title e Prezzo_base
            df_agg = df_base.copy()
            # Per ogni mercato elaborato, facciamo un merge left su ASIN
            for df_temp in agg_list:
                market = df_temp["Market"].iloc[0]
                df_agg = pd.merge(df_agg, df_temp.drop(columns="Market"), on="ASIN", how="left")
            
            # Calcoliamo, per ciascun mercato, la differenza percentuale se il prezzo base è inferiore
            market_columns = [col for col in df_agg.columns if col.startswith("Prezzo_") and col != "Prezzo_base"]
            for col in market_columns:
                market = col.split("_", 1)[1]  # estrae il nome del mercato
                # Creiamo la colonna di risparmio per quel mercato
                df_agg[f"Risparmio_{market}"] = df_agg.apply(
                    lambda row: ((row[col] - row["Prezzo_base"]) / row["Prezzo_base"] * 100)
                    if pd.notnull(row[col]) and row["Prezzo_base"] < row[col] else None, axis=1
                )
            
            # Calcoliamo il numero di mercati in cui il prodotto è conveniente
            def count_convenient(row):
                count = 0
                markets_list = []
                for col in df_agg.columns:
                    if col.startswith("Risparmio_"):
                        if pd.notnull(row[col]):
                            count += 1
                            market_name = col.split("_", 1)[1]
                            markets_list.append(market_name)
                return pd.Series({"Num_mercati_convenienti": count, "Mercati_convenienti": ", ".join(markets_list)})
            
            convenienza = df_agg.apply(count_convenient, axis=1)
            df_agg = pd.concat([df_agg, convenienza], axis=1)
            
            # Filtro: mostra solo i prodotti convenienti in almeno 'min_markets_convenient' mercati
            df_agg_filtered = df_agg[df_agg["Num_mercati_convenienti"] >= min_markets_convenient]
            
            if df_agg_filtered.empty:
                st.info(f"Nessun prodotto risulta conveniente in almeno {min_markets_convenient} mercato/i.")
            else:
                # Ordiniamo in base al numero di mercati convenienti e poi per uno dei risparmi medi (opzionale)
                df_agg_filtered = df_agg_filtered.sort_values("Num_mercati_convenienti", ascending=False)
                st.dataframe(df_agg_filtered, height=600)
                
                csv_data_agg = df_agg_filtered.to_csv(index=False, sep=";").encode("utf-8")
                st.download_button(
                    label="Scarica CSV Risultati Aggregati",
                    data=csv_data_agg,
                    file_name="risultato_aggregato.csv",
                    mime="text/csv"
                )
