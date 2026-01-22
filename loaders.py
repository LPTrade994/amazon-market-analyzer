import pandas as pd
import numpy as np
import re
import streamlit as st
import openpyxl  # Per supporto XLSX Keepa
from typing import List, Any
from io import BytesIO  # NUOVO import per XLSX handling
import traceback        # Per debug errors
import config

@st.cache_data(ttl=3600)  # Cache per 1 ora
def load_keepa_excel_cached(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Cached loading of Keepa XLSX files
    
    Args:
        file_bytes: Raw bytes of the Excel file
        filename: Name of the file for debugging
        
    Returns:
        pd.DataFrame: Loaded DataFrame
    """
    excel_file = BytesIO(file_bytes)
    return pd.read_excel(excel_file, engine='openpyxl', header=0)

@st.cache_data(ttl=3600)  # Cache per 1 ora  
def load_keepa_csv_cached(file_bytes: bytes, encoding: str) -> pd.DataFrame:
    """
    Cached loading of Keepa CSV files
    
    Args:
        file_bytes: Raw bytes of the CSV file
        encoding: File encoding to use
        
    Returns:
        pd.DataFrame: Loaded DataFrame
    """
    csv_file = BytesIO(file_bytes)
    
    # Rileva automaticamente il formato CSV
    csv_file.seek(0)
    sample = csv_file.read(2048).decode(encoding, errors='ignore')
    csv_file.seek(0)
    
    # Rileva il separatore più probabile
    separators = ['\t', ';', ',', '|']
    separator_counts = {sep: sample.count(sep) for sep in separators}
    best_separator = max(separator_counts, key=separator_counts.get)
    
    # Se il miglior separatore ha almeno 3 occorrenze, usalo
    if separator_counts[best_separator] >= 3:
        if best_separator in ['\t', ';']:
            # Tab o semicolon: probabilmente formato europeo con virgola decimale
            return pd.read_csv(csv_file, encoding=encoding, decimal=',', sep=best_separator)
        else:
            # Virgola o pipe: formato standard
            return pd.read_csv(csv_file, encoding=encoding, sep=best_separator)
    else:
        # Fallback: formato standard
        return pd.read_csv(csv_file, encoding=encoding)

# Try to import chardet for encoding detection
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False


def detect_file_encoding(uploaded_file):
    """
    Detect file encoding using chardet if available
    """
    if not HAS_CHARDET:
        return None
    
    try:
        # Read first 10KB for encoding detection
        uploaded_file.seek(0)
        sample = uploaded_file.read(10240)
        uploaded_file.seek(0)
        
        result = chardet.detect(sample)
        if result and result.get('confidence', 0) > 0.7:
            return result['encoding']
    except:
        pass
    
    return None


def force_numeric_conversion(series):
    """
    Conversione forzata a numeric SENZA ECCEZIONI
    
    Args:
        series: Pandas Series da convertire
        
    Returns:
        pd.Series: Serie numerica garantita come float
    """
    try:
        # Step 1: Converti tutto a string
        series_str = series.astype(str)
        
        # Step 2: Sostituisci valori problematici
        series_clean = (series_str
                       .str.replace('None', '0', regex=False)
                       .str.replace('null', '0', regex=False) 
                       .str.replace('NaN', '0', regex=False)
                       .str.replace('nan', '0', regex=False)
                       .str.replace('€', '', regex=False)
                       .str.replace('EUR', '', regex=False)
                       .str.replace(',', '.', regex=False)
                       .str.replace(' ', '', regex=False)
                       .str.strip())
        
        # Step 3: Sostituisci stringhe vuote
        series_clean = series_clean.replace('', '0')
        
        # Step 4: Conversione finale a numeric
        result = pd.to_numeric(series_clean, errors='coerce')
        
        # Step 5: Riempi eventuali NaN rimasti
        result = result.fillna(0.0)
        
        # Step 6: GARANZIA che sia float
        return result.astype(float)
        
    except Exception as e:
        st.warning(f"Force conversion fallback activated: {e}")
        # FALLBACK ASSOLUTO: serie di zeri
        return pd.Series([0.0] * len(series), index=series.index, dtype=float)


def convert_to_numeric(series, default=0.0):
    """
    Converte serie a numeric gestendo tutti i casi edge
    
    Args:
        series: Pandas Series da convertire
        default: Valore di default per valori non convertibili
        
    Returns:
        pd.Series: Serie numerica pulita
    """
    try:
        # Se già numeric, ritorna così
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(default)
        
        # Converti a string prima
        series_str = series.astype(str)
        
        # Rimuovi simboli comuni
        series_clean = (series_str
                       .str.replace('€', '', regex=False)
                       .str.replace('EUR', '', regex=False)
                       .str.replace(',', '.', regex=False)
                       .str.replace(' ', '', regex=False)
                       .str.replace('nan', str(default), regex=False)
                       .str.replace('None', str(default), regex=False)
                       .str.replace('null', str(default), regex=False))
        
        # Gestisci stringhe vuote
        series_clean = series_clean.replace('', str(default))
        
        # Converti a numeric
        series_numeric = pd.to_numeric(series_clean, errors='coerce')
        
        # Riempi NaN con default
        return series_numeric.fillna(default)
        
    except Exception as e:
        st.warning(f"Conversion warning: {e}")
        # Fallback: crea serie di default
        return pd.Series([default] * len(series), index=series.index)


def detect_locale(row) -> str:
    """
    Detect market locale from row data.
    CRITICAL RULE: Market MUST be detected from 'Locale' column, NEVER from filename.
    
    Args:
        row: DataFrame row containing product data
        
    Returns:
        str: Locale code ('it', 'de', 'fr', 'es')
    """
    # Primary: Use 'Locale' column if present
    if 'Locale' in row.index and pd.notna(row['Locale']):
        locale = str(row['Locale']).lower().strip()
        # Normalize to supported locales
        if locale in ['it', 'de', 'fr', 'es']:
            return locale
        # Handle variations
        locale_mapping = {
            'italy': 'it',
            'deutschland': 'de', 
            'germany': 'de',
            'france': 'fr',
            'spain': 'es',
            'españa': 'es'
        }
        if locale in locale_mapping:
            return locale_mapping[locale]
    
    # Fallback: Extract from 'URL: Amazon' domain
    if 'URL: Amazon' in row.index and pd.notna(row['URL: Amazon']):
        url = str(row['URL: Amazon'])
        domain_match = re.search(r'amazon\.([a-z]{2})', url)
        if domain_match:
            domain = domain_match.group(1)
            if domain in ['it', 'de', 'fr', 'es']:
                return domain
    
    # Default fallback
    return 'it'


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizza colonne per formato Keepa XLSX con conversioni robuste
    
    Args:
        df: Input DataFrame
        
    Returns:
        pd.DataFrame: Normalized DataFrame con type safety
    """
    df = df.copy()
    
    # Rimuovi spazi dai nomi colonne
    df.columns = df.columns.str.strip()
    
    # Convert numeric columns silently
    conversions = 0
    
    # CONVERTI PREZZI
    price_keywords = ['price', 'current', 'fee', 'avg', 'lowest', 'highest', '€', 'cost']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in price_keywords):
            df[col] = convert_to_numeric(df[col], default=0.0)
            conversions += 1
    
    # CONVERTI PERCENTUALI
    pct_keywords = ['%', 'drop', 'change']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in pct_keywords):
            df[col] = convert_to_numeric(df[col], default=0.0)
            conversions += 1
    
    # CONVERTI RANKS
    rank_keywords = ['rank', 'count', 'rating count']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in rank_keywords):
            df[col] = convert_to_numeric(df[col], default=999999)
            conversions += 1
    
    # CONVERTI RATINGS specificamente
    if 'Reviews: Rating' in df.columns:
        df['Reviews: Rating'] = convert_to_numeric(df['Reviews: Rating'], default=0.0)
    
    # CONVERTI BOUGHT IN PAST MONTH
    if 'Bought in past month' in df.columns:
        df['Bought in past month'] = convert_to_numeric(df['Bought in past month'], default=0)
    
    # CONVERTI CONTATORI/OFFERTE
    count_keywords = ['offers', 'winner']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in count_keywords):
            df[col] = convert_to_numeric(df[col], default=0)
    
    # Trim whitespace da colonne stringa rimanenti
    string_columns = df.select_dtypes(include=['object']).columns
    for col in string_columns:
        if col in df.columns and col not in ['ASIN', 'Title', 'Brand']:
            df[col] = df[col].astype(str).str.strip()
    
    if conversions > 0:
        st.info(f"Colonne numeriche normalizzate: {conversions}")
    
    return df


def validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida schema con FORCE CONVERSION di tutte le colonne numeriche
    
    Args:
        df: Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame con schema validato e conversioni forzate
    """
    st.write("🔧 Validating schema and forcing numeric conversions...")
    
    df = df.copy()
    
    # CRITICAL: Lista completa colonne che DEVONO essere numeriche
    NUMERIC_COLUMNS = [
        'Sales Rank: Current', 'Sales Rank: 30 days avg.', 'Sales Rank: 90 days avg.',
        'Buy Box 🚚: Current', 'Buy Box 🚚: 30 days avg.', 'Buy Box 🚚: 90 days avg.',
        'Amazon: Current', 'Reviews: Rating', 'Reviews: Rating Count',
        'Total Offer Count', 'New Offer Count: Current', 'Used Offer Count: Current',
        'Buy Box: Winner Count 30 days', 'Buy Box: Winner Count 90 days',
        'Buy Box: % Amazon 30 days', 'Buy Box: % Amazon 90 days', 'Buy Box: % Amazon 180 days',
        'Referral Fee %', 'FBA Pick&Pack Fee', 'Referral Fee based on current Buy Box price',
        'Return Rate', 'Bought in past month', 'Sales Rank: Drops last 30 days',
        'Buy Box 🚚: 90 days OOS', 'Amazon: 90 days OOS'
    ]
    
    # FORCE CONVERT ogni colonna numerica
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            if config.DEBUG_MODE:
                st.write(f"  Converting {col}...")
            
            # DEBUG SPECIALE per Buy Box
            if col == 'Buy Box 🚚: Current':
                if config.DEBUG_MODE:
                    sample_values = df[col].head(3).tolist()
                    st.write(f"    Buy Box sample values BEFORE conversion: {sample_values}")
                
            df[col] = force_numeric_conversion(df[col])
            
            if col == 'Buy Box 🚚: Current':
                if config.DEBUG_MODE:
                    sample_values = df[col].head(3).tolist()
                    st.write(f"    Buy Box sample values AFTER conversion: {sample_values}")
                    st.write(f"    Buy Box data type: {df[col].dtype}")
        else:
            # CREA colonna mancante con default
            if config.DEBUG_MODE:
                st.write(f"  Creating missing column {col} with default 0.0")
            df[col] = 0.0
    
    # SPECIAL CASES per colonne critiche
    if 'Amazon: Current' not in df.columns or df['Amazon: Current'].isna().all():
        df['Amazon: Current'] = 0.0
        if config.DEBUG_MODE:
            st.write("  Amazon: Current set to 0.0 (no Amazon offers)")
    
    if 'Return Rate' not in df.columns or df['Return Rate'].isna().all():
        df['Return Rate'] = 0.0
        if config.DEBUG_MODE:
            st.write("  Return Rate set to 0.0 (no data)")
    
    # Legacy column mappings
    legacy_mappings = {
        'SalesRank_Comp': 'Sales Rank: Current',
        'BuyBox_Current': 'Buy Box 🚚: Current'
    }
    
    # Apply legacy mappings
    for old_col, new_col in legacy_mappings.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = force_numeric_conversion(df[old_col])
    
    # Required columns with defaults (garantite come float)
    required_columns = {
        'Buy Box 🚚: Current': 0.0,
        'Referral Fee %': 0.15,  # 15% default
        'FBA Pick&Pack Fee': 2.0
    }
    
    # Add missing required columns (garantite come float)
    for col, default_value in required_columns.items():
        if col not in df.columns:
            df[col] = float(default_value)
        else:
            # Force conversion anche per quelle esistenti
            df[col] = force_numeric_conversion(df[col])
    
    st.write("Schema validation completed - all numeric columns guaranteed as float")
    return df


def load_data(uploaded_files: List[Any]) -> pd.DataFrame:
    """
    Carica dataset Keepa da file CSV o XLSX con gestione errori avanzata.
    
    Args:
        uploaded_files: Lista di file caricati da Streamlit
        
    Returns:
        pd.DataFrame: DataFrame combinato e processato
    """
    all_data = []
    
    for uploaded_file in uploaded_files:
        try:
            if config.DEBUG_MODE:
                st.write(f"Processing file: {uploaded_file.name}, type: {type(uploaded_file)}")
            
            # RESET file pointer to beginning
            uploaded_file.seek(0)
            
            # Determina tipo file
            if uploaded_file.name.endswith('.xlsx'):
                # PER XLSX: Usa cached loading
                st.info(f"Caricamento XLSX: {uploaded_file.name}")
                
                # Leggi bytes per cached function
                bytes_data = uploaded_file.read()
                
                # Usa cached loading
                df = load_keepa_excel_cached(bytes_data, uploaded_file.name)
                st.success(f"XLSX loaded: {len(df)} rows, {len(df.columns)} columns")
                
            elif uploaded_file.name.endswith('.csv'):
                # PER CSV: Usa cached loading con encoding detection
                st.info(f"Caricamento CSV: {uploaded_file.name}")
                uploaded_file.seek(0)
                
                df = None
                encoding_used = None
                
                # Read bytes for caching
                bytes_data = uploaded_file.read()
                
                # Prova prima rilevazione automatica
                uploaded_file.seek(0)
                detected_encoding = detect_file_encoding(uploaded_file)
                
                # Lista di encoding da provare
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']
                if detected_encoding:
                    encodings_to_try.insert(0, detected_encoding)
                
                for encoding in encodings_to_try:
                    try:
                        df = load_keepa_csv_cached(bytes_data, encoding)
                        encoding_used = encoding
                        break
                    except (UnicodeDecodeError, UnicodeError, LookupError):
                        continue
                
                if df is None:
                    st.error(f"Impossibile decodificare il file CSV: {uploaded_file.name}")
                    st.error("Prova a salvare il file in formato UTF-8 o XLSX")
                    continue
                    
                st.success(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns, encoding: {encoding_used}")
                
            else:
                st.error(f"Formato file non supportato: {uploaded_file.name}")
                st.error("📋 Formati supportati: .xlsx (Keepa), .csv")
                continue
            
            # Verifica che il file non sia vuoto
            if df.empty:
                st.warning(f"⚠️ File vuoto saltato: {uploaded_file.name}")
                continue
            
            # Debug: mostra sample colonne
            if config.DEBUG_MODE:
                st.write(f"Sample columns: {list(df.columns[:10])}")
            
            # Log informazioni dataset per debug
            st.info(f"📊 {uploaded_file.name}: {len(df)} righe, {len(df.columns)} colonne")
            
            # Applica normalizzazione per formato Keepa
            df = normalize_columns(df)
            df = validate_schema(df)
            
            # Rileva mercato dai dati (CRITICO: non dal filename!)
            df['source_market'] = df.apply(detect_locale, axis=1)
            
            # Debug mercato rilevato
            # Aggiungi metadati source
            df['source_file'] = uploaded_file.name
            
            all_data.append(df)
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"Errore caricamento {uploaded_file.name}: {error_msg}")
            
            # Diagnosi specifica del tipo di errore
            if 'utf-8' in error_msg and 'decode' in error_msg:
                st.error("🔤 Problema di codifica caratteri. Prova:")
                st.error("   • Salvare il file come CSV UTF-8")
                st.error("   • Oppure usare formato XLSX")
            elif 'excel' in error_msg.lower() or 'openpyxl' in error_msg.lower():
                st.error("📊 Problema file Excel. Verifica:")
                st.error("   • File non corrotto")
                st.error("   • Formato XLSX standard")
            else:
                st.error(f"💡 Dettaglio errore: {error_msg}")
                st.error("💡 Suggerimento: Verifica che il file sia un export Keepa valido")
            continue
    
    # Combina tutti i DataFrame
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Statistiche finali
        total_rows = len(combined_df)
        unique_asins = combined_df['ASIN'].nunique() if 'ASIN' in combined_df.columns else 0
        markets = combined_df['source_market'].value_counts()
        
        st.success(f"Dataset combinato: {total_rows} righe totali")
        st.success(f"ASIN unici: {unique_asins}")
        st.success(f"Mercati: {dict(markets)}")
        
        return combined_df
    
    else:
        st.warning("⚠️ Nessun file caricato con successo")
        # Return empty DataFrame con struttura base
        return pd.DataFrame(columns=[
            'ASIN', 'Title', 'Locale', 'Buy Box 🚚: Current', 'Amazon: Current',
            'New FBA: Current', 'New FBM: Current', 'Sales Rank: Current',
            'Reviews Rating', 'Buy Box: % Amazon 90 days', 'Offers: Count',
            'Prime Eligible', 'Referral Fee %', 'FBA Pick&Pack Fee',
            'source_market', 'source_file'
        ])