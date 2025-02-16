import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)",
    page_icon="🔎",
    layout="wide"
)

st.title("Amazon Market Analyzer - Multi-Mercato + Vendite (Bought in past month)")

#################################
# Sidebar: Caricamento file e impostazioni di confronto
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
    # Opzione per mostrare la tabella aggregata
    show_aggregated = st.checkbox("Mostra tabella aggregata (prodotti convenienti su più mercati)")
    # Filtro: minimo numero di mercati in cui il prodotto deve risultare conveniente
    min_markets_convenient = st.number_input(
        "Mostra solo prodotti convenienti in almeno n mercati:",
        min_value=1,
        value=1
    )
    
    st.markdown("---")
    # Nuove impostazioni per il Composite Score
    st.subheader("Impostazioni Composite Score")
    peso_margine = st.slider("Peso Margine (mercato di riferimento)", 0.0, 10.0, 1.0, step=0.1)
    peso_volume = st.slider("Peso Volume (mercato di riferimento)", 0.0, 10.0, 1.0, step=0.1)
    peso_markets = st.slider("Peso Numero Mercati Convenienti", 0.0, 10.0, 1.0, step=0.1)
    
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
# 2) Confronto individuale per ciascun file di confronto
#################################
agg_list = []  # Per raccogliere dati per l'aggregazione multi-mercato

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
        
        # Calcola la differenza percentuale
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
        
        # Seleziona le colonne finali per questo confronto
        df_finale = df_merged[[
            "Locale", "ASIN", "Title", "Bought in past month",
            f"Prezzo base ({base_price_option})", f"Prezzo confronto ({comparison_price_option})", "Risparmio_%"
        ]]
        
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
        
        # Prepara i dati per l'aggregazione multi-mercato:
        # Per ciascun file, manteniamo ASIN, Prezzo_comp, Bought in past month e Locale.
        market = df_comp["Locale"].dropna().unique()[0]  # si assume che in ciascun file sia unico
        df_temp = df_comp.drop_duplicates(subset="ASIN")
        df_temp = df_temp[["ASIN", "Prezzo_comp", "Bought in past month"]]
        df_temp = df_temp.rename(columns={
            "Prezzo_comp": f"Prezzo_{market}",
            "Bought in past month": f"Bought_{market}"
        })
        df_temp["Market"] = market  # utile per identificare il mercato
        agg_list.append(df_temp)
    
    #################################
    # 3) Tabella Aggregata (prodotti convenienti su più mercati)
    #################################
    if show_aggregated:
        st.markdown("## Risultati Aggregati (prodotti convenienti su più mercati)")
        if df_base is None or df_base.empty:
            st.error("La lista di partenza non è disponibile per l'aggregazione.")
        else:
            df_agg = df_base.copy()  # partiamo dalla lista di partenza
            
            # Uniamo (merge left) per ogni mercato elaborato
            for df_temp in agg_list:
                market = df_temp["Market"].iloc[0]
                df_agg = pd.merge(df_agg, df_temp.drop(columns="Market"), on="ASIN", how="left")
            
            # Convertiamo le colonne Bought_{market} in numerico
            for col in df_agg.columns:
                if col.startswith("Bought_"):
                    df_agg[col] = pd.to_numeric(df_agg[col], errors='coerce').fillna(0)
            
            # Per ogni mercato (colonne che iniziano per "Prezzo_"), calcoliamo il risparmio percentuale se conveniente
            market_columns = [col for col in df_agg.columns if col.startswith("Prezzo_") and col != "Prezzo_base"]
            for col in market_columns:
                market = col.split("_", 1)[1]  # estrae il nome del mercato
                df_agg[f"Risparmio_{market}"] = df_agg.apply(
                    lambda row: ((row[col] - row["Prezzo_base"]) / row["Prezzo_base"] * 100)
                    if pd.notnull(row[col]) and row["Prezzo_base"] < row[col] else np.nan, axis=1
                )
            
            # Calcola il numero di mercati in cui il prodotto è conveniente e la lista dei mercati
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
                df_agg_filtered = df_agg_filtered.sort_values("Num_mercati_convenienti", ascending=False)
                st.dataframe(df_agg_filtered, height=600)
                
                csv_data_agg = df_agg_filtered.to_csv(index=False, sep=";").encode("utf-8")
                st.download_button(
                    label="Scarica CSV Risultati Aggregati",
                    data=csv_data_agg,
                    file_name="risultato_aggregato.csv",
                    mime="text/csv"
                )
            
            #################################
            # 4) Composite Score & Dashboard Convenienza
            #################################
            # Se sono stati aggregati dei mercati, chiediamo all'utente di scegliere il mercato di riferimento per il Composite Score.
            if agg_list:
                markets_available = list(set([df_temp["Market"].iloc[0] for df_temp in agg_list]))
                market_ref = st.sidebar.selectbox("Mercato di riferimento per Composite Score", options=markets_available, index=0)
                
                # Verifica che per il mercato scelto esistano le colonne Risparmio e Bought
                risparmio_col = f"Risparmio_{market_ref}"
                bought_col = f"Bought_{market_ref}"
                if risparmio_col in df_agg.columns and bought_col in df_agg.columns:
                    # Calcolo del Composite Score:
                    # Composite_Score = (Risparmio_{market_ref} * peso_margine) + (log(1 + Bought_{market_ref}) * peso_volume) + (Num_mercati_convenienti * peso_markets)
                    df_agg["Composite_Score"] = df_agg.apply(
                        lambda row: (row[risparmio_col] if pd.notnull(row[risparmio_col]) else 0) * peso_margine \
                                    + np.log1p(row[bought_col]) * peso_volume \
                                    + row["Num_mercati_convenienti"] * peso_markets,
                        axis=1
                    )
                    # Ordina per Composite Score decrescente
                    df_composite = df_agg.sort_values("Composite_Score", ascending=False)
                    
                    st.markdown("## Dashboard Convenienza (Composite Score)")
                    
                    # Mostriamo alcune metriche chiave
                    col1, col2, col3 = st.columns(3)
                    top_score = df_composite["Composite_Score"].max() if not df_composite.empty else 0
                    media_score = df_composite["Composite_Score"].mean() if not df_composite.empty else 0
                    num_prodotti = df_composite.shape[0]
                    col1.metric("Miglior Composite Score", f"{top_score:.2f}")
                    col2.metric("Composite Score Medio", f"{media_score:.2f}")
                    col3.metric("Numero Prodotti", f"{num_prodotti}")
                    
                    st.dataframe(df_composite, height=600)
                    
                    csv_data_composite = df_composite.to_csv(index=False, sep=";").encode("utf-8")
                    st.download_button(
                        label="Scarica CSV Dashboard Composite Score",
                        data=csv_data_composite,
                        file_name="dashboard_composite_score.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(f"Per il mercato di riferimento '{market_ref}' non sono disponibili i dati necessari per il Composite Score.")
