"""
Export Module - Comprehensive Export and Watchlist Functionality

Modulo per esportazione dati consolidati, watchlist e report di analisi.
"""

import pandas as pd
import numpy as np
import json
import io
import csv
import re
from datetime import datetime
from typing import List, Dict, Any, Optional


def export_consolidated_csv(df: pd.DataFrame, filename: str = "analyzer_export.csv", action_ready: bool = True) -> bytes:
    """
    Esporta tabella consolidata in CSV compatibile con Excel EU
    
    Args:
        df: DataFrame consolidato con risultati analisi
        filename: Nome file di default (non utilizzato, ma mantenuto per compatibilità)
        
    Returns:
        bytes: Dati CSV codificati in UTF-8 con BOM per Excel
    """
    if df.empty:
        # Return empty CSV if no data
        return "ASIN;Title;Message\n;No data available;".encode('utf-8-sig')
    
    # Definisci colonne per export in ordine preferito
    export_columns = [
        'ASIN', 'Title', 'Best Route', 
        'Purchase Price €', 'Net Cost €', 'Target Price €', 
        'Target Price (Gross)', 'Target Price (Net)', 'VAT Amount', 'Fees €',
        'Gross Margin €', 'Real Profit', 'Gross Margin %', 'ROI %', 'Opportunity Score',
        'Velocity Score', 'Competition Score', 'Risk Score', 'Momentum Score',
        'is_historic_deal', 'amazon_share', 'sales_rank'
    ]
    
    # Aggiungi colonne dinamiche che potrebbero esistere
    additional_columns = [
        'source_market', 'target_market', 'velocity_score', 'competition_score', 
        'risk_score', 'momentum_score', 'amazon_dominance', 'rating', 'return_rate',
        'asin', 'title', 'route'  # Colonne cross-market
    ]
    
    # Filtra colonne esistenti nel DataFrame
    available_cols = []
    for col in export_columns + additional_columns:
        if col in df.columns:
            available_cols.append(col)
    
    # Se nessuna colonna standard trovata, usa tutte le colonne disponibili
    if not available_cols:
        available_cols = df.columns.tolist()
    
    # Crea DataFrame per export e ordina per ROI descending
    export_df = df[available_cols].copy()
    
    # Crea colonne VAT se non esistono già
    if 'Target Price (Gross)' not in export_df.columns and 'target_price_gross' in df.columns:
        export_df['Target Price (Gross)'] = df['target_price_gross']
    
    if 'Target Price (Net)' not in export_df.columns and 'target_price_net' in df.columns:
        export_df['Target Price (Net)'] = df['target_price_net']
    
    if 'VAT Amount' not in export_df.columns and 'target_vat_amount' in df.columns:
        export_df['VAT Amount'] = df['target_vat_amount']
    
    if 'Real Profit' not in export_df.columns and 'gross_margin_eur' in df.columns:
        export_df['Real Profit'] = df['gross_margin_eur']
    
    # ORDINA per ROI descending di default
    roi_col = 'ROI %' if 'ROI %' in export_df.columns else 'roi'
    if roi_col in export_df.columns:
        export_df = export_df.sort_values(roi_col, ascending=False)
    
    # 1. RIMUOVI HTML dal campo Opportunity Score
    if 'Opportunity Score' in export_df.columns:
        export_df['Opportunity Score'] = export_df['Opportunity Score'].astype(str)
        # Rimuovi tutti i tag HTML
        export_df['Opportunity Score'] = export_df['Opportunity Score'].str.replace(r'<[^>]+>', '', regex=True)
        # Estrai solo i numeri (inclusi decimali)
        export_df['Opportunity Score'] = export_df['Opportunity Score'].str.extract(r'(\d+\.?\d*)', expand=False)
        # Converti a numerico
        export_df['Opportunity Score'] = pd.to_numeric(export_df['Opportunity Score'], errors='coerce').fillna(0)
    
    # 2. VALIDA che Best Route sia nel formato corretto
    route_col = 'Best Route' if 'Best Route' in export_df.columns else 'route'
    if route_col in export_df.columns:
        valid_markets = ['IT', 'DE', 'FR', 'ES']
        
        def validate_route(route_str):
            if pd.isna(route_str):
                return "INVALID_ROUTE"
            route_str = str(route_str).strip()
            if '->' in route_str:
                parts = route_str.split('->')
                if len(parts) == 2:
                    source = parts[0].strip().upper()
                    target = parts[1].strip().upper()
                    if source in valid_markets and target in valid_markets:
                        return f"{source}->{target}"
            return "INVALID_ROUTE"
        
        export_df[route_col] = export_df[route_col].apply(validate_route)
    
    # 3. ESCAPE caratteri problematici per CSV
    text_cols = ['Title', 'ASIN', 'title', 'asin']
    for col in text_cols:
        if col in export_df.columns:
            export_df[col] = export_df[col].astype(str)
            # Sostituisci le virgolette doppie con virgolette doppie escaped
            export_df[col] = export_df[col].str.replace('"', '""', regex=False)
            # Rimuovi caratteri di controllo che possono rompere il CSV
            export_df[col] = export_df[col].str.replace(r'[\r\n\t]', ' ', regex=True)
    
    # 4. FORMATTING NUMERICO per Excel EU
    # Assicurati che i valori numerici siano formattati correttamente
    numeric_cols = [
        'Purchase Price €', 'Net Cost €', 'Target Price €', 'Fees €', 'Gross Margin €',
        'purchase_price', 'net_cost', 'target_price', 'gross_margin_eur'
    ]
    for col in numeric_cols:
        if col in export_df.columns:
            export_df[col] = pd.to_numeric(export_df[col], errors='coerce').fillna(0).round(2)
    
    # Formatta percentuali e score
    percentage_cols = [
        'Gross Margin %', 'ROI %', 'Opportunity Score', 'Velocity Score', 
        'Competition Score', 'Risk Score', 'Momentum Score',
        'gross_margin_pct', 'roi', 'opportunity_score'
    ]
    for col in percentage_cols:
        if col in export_df.columns:
            export_df[col] = pd.to_numeric(export_df[col], errors='coerce').fillna(0).round(1)
    
    # 5. Pulisci altri campi HTML se presenti
    html_columns = ['Gross Margin %', 'ROI %', 'Links']
    for col in html_columns:
        if col in export_df.columns:
            export_df[col] = export_df[col].astype(str)
            # Rimuovi HTML tags
            export_df[col] = export_df[col].str.replace(r'<[^>]+>', '', regex=True)
            # Rimuovi entità HTML comuni
            export_df[col] = export_df[col].str.replace('&nbsp;', ' ', regex=False)
            export_df[col] = export_df[col].str.replace('&amp;', '&', regex=False)
            export_df[col] = export_df[col].str.replace('&lt;', '<', regex=False)
            export_df[col] = export_df[col].str.replace('&gt;', '>', regex=False)
    
    # AGGIUNGI colonne action-ready se richiesto
    if action_ready:
        # 1. Action Required column
        def determine_action(row):
            try:
                roi = pd.to_numeric(row.get('ROI %', 0) if 'ROI %' in row else row.get('roi', 0), errors='coerce')
                score = pd.to_numeric(row.get('Opportunity Score', 0), errors='coerce')
                risk_score = pd.to_numeric(row.get('Risk Score', 50) if 'Risk Score' in row else row.get('risk_score', 50), errors='coerce')
                
                roi = roi if pd.notna(roi) else 0
                score = score if pd.notna(score) else 0
                risk_score = risk_score if pd.notna(risk_score) else 50
                
                if roi > 30 and score > 70 and risk_score < 40:
                    return "BUY NOW"
                elif roi > 15 and score > 50:
                    return "MONITOR"
                else:
                    return "SKIP"
            except:
                return "SKIP"
        
        export_df['Action Required'] = export_df.apply(determine_action, axis=1)
        
        # 2. Budget Needed (net_cost * suggested_quantity)
        def calculate_budget_needed(row):
            try:
                net_cost = pd.to_numeric(row.get('Net Cost €', 0) if 'Net Cost €' in row else row.get('net_cost', 0), errors='coerce')
                roi = pd.to_numeric(row.get('ROI %', 0) if 'ROI %' in row else row.get('roi', 0), errors='coerce')
                
                net_cost = net_cost if pd.notna(net_cost) else 0
                roi = roi if pd.notna(roi) else 0
                
                # Suggested quantity based on ROI and risk
                if roi > 30:
                    suggested_qty = 10  # High ROI = higher quantity
                elif roi > 15:
                    suggested_qty = 5   # Medium ROI = medium quantity
                else:
                    suggested_qty = 2   # Low ROI = test quantity
                    
                return round(net_cost * suggested_qty, 2)
            except:
                return 0.0
        
        export_df['Budget Needed'] = export_df.apply(calculate_budget_needed, axis=1)
        
        # 3. Expected Profit 30d (profit * estimated_sales_30d)
        def calculate_expected_profit_30d(row):
            gross_margin = float(row.get('Gross Margin €', 0)) if 'Gross Margin €' in row else 0
            velocity_score = float(row.get('Velocity Score', 50)) if 'Velocity Score' in row else float(row.get('velocity_score', 50))
            
            # Estimate monthly sales based on velocity score
            # Velocity 70+ = ~20 units/month, 50-70 = ~10 units, <50 = ~5 units
            if velocity_score >= 70:
                estimated_monthly_sales = 20
            elif velocity_score >= 50:
                estimated_monthly_sales = 10
            else:
                estimated_monthly_sales = 5
                
            return round(gross_margin * estimated_monthly_sales, 2)
        
        export_df['Expected Profit 30d'] = export_df.apply(calculate_expected_profit_30d, axis=1)
        
        # 4. Break Even Units (fixed_costs / profit_per_unit)
        def calculate_break_even_units(row):
            gross_margin = float(row.get('Gross Margin €', 0)) if 'Gross Margin €' in row else 0
            
            if gross_margin <= 0:
                return "NEVER"  # Can't break even with negative margins
            
            # Assume fixed costs of €50 (advertising, time, misc)
            fixed_costs = 50
            break_even = fixed_costs / gross_margin
            
            return max(1, round(break_even))  # At least 1 unit
        
        export_df['Break Even Units'] = export_df.apply(calculate_break_even_units, axis=1)
    
    # AGGIUNGI summary row se action_ready
    if action_ready and len(export_df) > 0:
        # Calculate summary statistics (exclude action-ready rows from calculation)
        summary_df = export_df[~export_df['ASIN'].isin(['SUMMARY', 'TOTALS/AVG'])].copy() if 'ASIN' in export_df.columns else export_df.copy()
        
        total_budget = pd.to_numeric(summary_df['Budget Needed'], errors='coerce').fillna(0).sum() if 'Budget Needed' in summary_df.columns else 0
        total_expected_profit = pd.to_numeric(summary_df['Expected Profit 30d'], errors='coerce').fillna(0).sum() if 'Expected Profit 30d' in summary_df.columns else 0
        avg_roi = pd.to_numeric(summary_df[roi_col], errors='coerce').fillna(0).mean() if roi_col in summary_df.columns else 0
        
        # Risk distribution
        buy_now_count = len(export_df[export_df.get('Action Required', '') == 'BUY NOW'])
        monitor_count = len(export_df[export_df.get('Action Required', '') == 'MONITOR'])
        skip_count = len(export_df[export_df.get('Action Required', '') == 'SKIP'])
        
        # Create summary row
        summary_row = {
            'ASIN': 'TOTALS/AVG',
            'Title': f'Total Opportunities: {len(export_df)}',
            'Best Route': f'BUY: {buy_now_count} | MONITOR: {monitor_count} | SKIP: {skip_count}',
            'Budget Needed': total_budget,
            'Expected Profit 30d': total_expected_profit,
            roi_col: avg_roi,
            'Action Required': f'Total ROI: {(total_expected_profit/total_budget*100) if total_budget > 0 else 0:.1f}%'
        }
        
        # Fill other columns with appropriate values
        for col in export_df.columns:
            if col not in summary_row:
                if col in ['Purchase Price €', 'Net Cost €', 'Target Price €', 'Gross Margin €']:
                    try:
                        # Safely convert to numeric and calculate mean
                        numeric_values = pd.to_numeric(export_df[col], errors='coerce').fillna(0)
                        summary_row[col] = numeric_values.mean()
                    except:
                        summary_row[col] = 0.0
                else:
                    summary_row[col] = ''
        
        # Add separator row
        separator_row = {col: '---' for col in export_df.columns}
        separator_row['ASIN'] = 'SUMMARY'
        separator_row['Title'] = '--- SUMMARY STATISTICS ---'
        
        # Append rows to DataFrame
        export_df = pd.concat([export_df, pd.DataFrame([separator_row, summary_row])], ignore_index=True)
    
    # 6. Aggiungi metadati di export
    export_df['exported_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    export_df['export_version'] = '2.0' if action_ready else '1.0'
    
    # 7. Export con formato EU per Excel (separatore ; e decimale ,)
    csv_buffer = io.StringIO()
    export_df.to_csv(
        csv_buffer, 
        index=False, 
        encoding='utf-8',
        sep=';',           # Usa ; invece di , per Excel EU
        decimal=',',       # Usa , per decimali EU
        quoting=csv.QUOTE_MINIMAL,  # Quote solo quando necessario
        lineterminator='\n'
    )
    return csv_buffer.getvalue().encode('utf-8-sig')  # BOM per Excel


def export_watchlist_json(selected_asins: List[str], df: pd.DataFrame, params: Dict[str, Any]) -> str:
    """
    Esporta watchlist selezionata in JSON
    
    Args:
        selected_asins: Lista degli ASIN selezionati
        df: DataFrame con i dati dei prodotti
        params: Parametri di analisi utilizzati
        
    Returns:
        str: Stringa JSON formattata della watchlist
    """
    if not selected_asins:
        return json.dumps({
            "watchlist": [],
            "message": "No ASINs selected",
            "exported_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
    
    watchlist = []
    
    for asin in selected_asins:
        # Trova il prodotto nel DataFrame
        asin_rows = df[df['ASIN'] == asin]
        
        if asin_rows.empty:
            # Se ASIN non trovato, crea entry minima
            item = {
                'asin': asin,
                'title': 'Product not found',
                'status': 'error',
                'message': 'ASIN not found in current analysis'
            }
        else:
            asin_data = asin_rows.iloc[0].to_dict()
            
            # Determina target market per links
            target_market = 'it'  # Default
            if 'Best Route' in asin_data and asin_data['Best Route']:
                route_parts = str(asin_data['Best Route']).split('->')
                if len(route_parts) > 1:
                    target_market = route_parts[1].lower().strip()
            
            # Struttura watchlist item
            item = {
                'asin': asin,
                'title': asin_data.get('Title', 'Unknown Title'),
                'best_route': asin_data.get('Best Route', 'Unknown Route'),
                'metrics': {
                    'opportunity_score': float(asin_data.get('Opportunity Score', 0)) if pd.notna(asin_data.get('Opportunity Score', 0)) else 0,
                    'roi_pct': float(asin_data.get('ROI %', 0)) if pd.notna(asin_data.get('ROI %', 0)) else 0,
                    'gross_margin_eur': float(asin_data.get('Gross Margin €', 0)) if pd.notna(asin_data.get('Gross Margin €', 0)) else 0,
                    'gross_margin_pct': float(asin_data.get('Gross Margin %', 0)) if pd.notna(asin_data.get('Gross Margin %', 0)) else 0,
                    'velocity_score': float(asin_data.get('velocity_score', 0)) if pd.notna(asin_data.get('velocity_score', 0)) else 0,
                    'risk_score': float(asin_data.get('risk_score', 0)) if pd.notna(asin_data.get('risk_score', 0)) else 0
                },
                'financial': {
                    'purchase_price': float(asin_data.get('Purchase Price €', 0)) if pd.notna(asin_data.get('Purchase Price €', 0)) else 0,
                    'net_cost': float(asin_data.get('Net Cost €', 0)) if pd.notna(asin_data.get('Net Cost €', 0)) else 0,
                    'target_price': float(asin_data.get('Target Price €', 0)) if pd.notna(asin_data.get('Target Price €', 0)) else 0,
                    'fees': asin_data.get('Fees €', '€0.00')
                },
                'flags': {
                    'is_historic_deal': bool(asin_data.get('is_historic_deal', False)),
                    'prime_eligible': bool(asin_data.get('prime_eligible', False))
                },
                'analysis_params': {
                    'discount_pct': params.get('discount', 0) * 100,
                    'purchase_strategy': params.get('purchase_strategy', 'Unknown'),
                    'sale_scenario': params.get('scenario', 'Unknown'),
                    'mode': params.get('mode', 'FBA')
                },
                'links': {
                    'amazon': f"https://amazon.{target_market}/dp/{asin}",
                    'keepa': f"https://keepa.com/#!product/8-{asin}"  # 8 = Amazon IT
                },
                'exported_at': datetime.now().isoformat()
            }
        
        watchlist.append(item)
    
    # Struttura finale JSON
    export_data = {
        'watchlist': watchlist,
        'summary': {
            'total_items': len(watchlist),
            'valid_items': len([item for item in watchlist if 'status' not in item or item['status'] != 'error']),
            'avg_opportunity_score': np.mean([item['metrics']['opportunity_score'] for item in watchlist if 'metrics' in item]),
            'historic_deals_count': len([item for item in watchlist if item.get('flags', {}).get('is_historic_deal', False)])
        },
        'analysis_metadata': {
            'export_version': '1.0',
            'parameters_used': params,
            'exported_at': datetime.now().isoformat(),
            'exported_from': 'Amazon Analyzer Pro'
        }
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def create_summary_report(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    """
    Genera report summary in markdown
    
    Args:
        df: DataFrame consolidato con risultati
        params: Parametri di analisi utilizzati
        
    Returns:
        str: Report in formato markdown
    """
    if df.empty:
        return """# Amazon Analyzer Pro - Report Summary

**Nessun dato disponibile per il report.**

Generato il: {}
""".format(datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Calcola statistiche principali
    total_asins = len(df)
    avg_score = df['Opportunity Score'].mean() if 'Opportunity Score' in df.columns else 0
    
    # Gestisci colonna historic deals
    historic_deals = 0
    if 'is_historic_deal' in df.columns:
        historic_deals = len(df[df['is_historic_deal'] == True])
    
    # Calcola ROI
    best_roi = 0
    if 'ROI %' in df.columns:
        roi_values = pd.to_numeric(df['ROI %'], errors='coerce').fillna(0)
        best_roi = roi_values.max()
    
    # Generazione report
    report = f"""# Amazon Analyzer Pro - Report Summary

**Data Analisi:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

## Parametri Analisi
- **Sconto applicato:** {params.get('discount', 0)*100:.1f}%
- **Strategia acquisto:** {params.get('purchase_strategy', 'N/A')}
- **Scenario vendita:** {params.get('scenario', 'N/A')}
- **Modalità:** {params.get('mode', 'N/A')}

## Risultati Chiave
- **ASIN analizzati:** {total_asins:,}
- **Opportunity Score medio:** {avg_score:.1f}/100
- **Affari storici identificati:** {historic_deals} ({historic_deals/total_asins*100:.1f}% del totale)
- **Miglior ROI:** {best_roi:.1f}%

## Distribuzione Opportunity Score
"""
    
    # Distribuzione score
    if 'Opportunity Score' in df.columns:
        scores = pd.to_numeric(df['Opportunity Score'], errors='coerce').fillna(0)
        high_score = len(scores[scores >= 70])
        medium_score = len(scores[(scores >= 50) & (scores < 70)])
        low_score = len(scores[scores < 50])
        
        report += f"""- **Score Alto (≥70):** {high_score} prodotti ({high_score/total_asins*100:.1f}%)
- **Score Medio (50-69):** {medium_score} prodotti ({medium_score/total_asins*100:.1f}%)
- **Score Basso (<50):** {low_score} prodotti ({low_score/total_asins*100:.1f}%)

"""
    
    # Top 10 opportunità
    report += "## Top 10 Opportunità\n\n"
    
    # Seleziona colonne per top 10
    top_columns = []
    for col in ['ASIN', 'Title', 'Best Route', 'Opportunity Score', 'ROI %']:
        if col in df.columns:
            top_columns.append(col)
    
    if top_columns and 'Opportunity Score' in df.columns:
        # Ordina per Opportunity Score e prendi top 10
        top_df = df.sort_values('Opportunity Score', ascending=False).head(10)
        
        for idx, (_, row) in enumerate(top_df.iterrows(), 1):
            asin = row.get('ASIN', 'N/A')
            title = str(row.get('Title', 'N/A'))[:40]
            if len(str(row.get('Title', ''))) > 40:
                title += "..."
            route = row.get('Best Route', 'N/A')
            score = row.get('Opportunity Score', 0)
            roi = row.get('ROI %', 0)
            
            report += f"{idx}. **{asin}** | {title} | {route} | Score: {score:.0f} | ROI: {roi:.1f}%\n"
    else:
        report += "*Nessun dato disponibile per la classifica delle opportunità*\n"
    
    # Affari storici section
    if historic_deals > 0:
        report += f"\n## Affari Storici Identificati ({historic_deals})\n\n"
        
        historic_df = df[df['is_historic_deal'] == True] if 'is_historic_deal' in df.columns else pd.DataFrame()
        
        if not historic_df.empty:
            historic_top = historic_df.sort_values('Opportunity Score', ascending=False).head(5)
            
            for idx, (_, row) in enumerate(historic_top.iterrows(), 1):
                asin = row.get('ASIN', 'N/A')
                title = str(row.get('Title', 'N/A'))[:35]
                if len(str(row.get('Title', ''))) > 35:
                    title += "..."
                score = row.get('Opportunity Score', 0)
                
                report += f"{idx}. **{asin}** | {title} | Score: {score:.0f} 🔥\n"
    
    # Footer
    report += f"""
---
*Report generato da Amazon Analyzer Pro v1.0*  
*{datetime.now().strftime('%d/%m/%Y alle %H:%M')}*
"""
    
    return report


def validate_export_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Valida i dati prima dell'export
    
    Args:
        df: DataFrame da validare
        
    Returns:
        Dict con risultati della validazione
    """
    validation = {
        'is_valid': True,
        'warnings': [],
        'errors': [],
        'stats': {}
    }
    
    if df.empty:
        validation['is_valid'] = False
        validation['errors'].append("DataFrame is empty")
        return validation
    
    # Statistiche base
    validation['stats']['total_rows'] = len(df)
    validation['stats']['total_columns'] = len(df.columns)
    
    # Controlla colonne essenziali
    essential_columns = ['ASIN', 'Title']
    missing_essential = [col for col in essential_columns if col not in df.columns]
    
    if missing_essential:
        validation['errors'].extend([f"Missing essential column: {col}" for col in missing_essential])
        validation['is_valid'] = False
    
    # Controlla valori nulli in colonne importanti
    important_columns = ['ASIN', 'Opportunity Score', 'ROI %']
    for col in important_columns:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                validation['warnings'].append(f"Column '{col}' has {null_count} null values")
    
    # Controlla range valori
    if 'Opportunity Score' in df.columns:
        score_values = pd.to_numeric(df['Opportunity Score'], errors='coerce')
        out_of_range = len(score_values[(score_values < 0) | (score_values > 100)])
        if out_of_range > 0:
            validation['warnings'].append(f"{out_of_range} Opportunity Scores are out of range (0-100)")
    
    validation['stats']['validation_warnings'] = len(validation['warnings'])
    validation['stats']['validation_errors'] = len(validation['errors'])
    
    return validation


def export_executive_summary(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    """
    Genera Executive Summary (1-page) con top opportunities e business metrics
    
    Args:
        df: DataFrame consolidato con risultati 
        params: Parametri di analisi utilizzati
        
    Returns:
        str: Executive Summary in formato markdown action-ready
    """
    if df.empty:
        return """# 📊 Executive Summary - Amazon Arbitrage Analysis

**⚠️ No opportunities found with current parameters**

Generated: {}
""".format(datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Sort by ROI descending for top opportunities
    roi_col = 'ROI %' if 'ROI %' in df.columns else 'roi'
    if roi_col in df.columns:
        df_sorted = df.sort_values(roi_col, ascending=False)
    else:
        df_sorted = df.copy()
    
    # Calculate key metrics
    total_opportunities = len(df_sorted)
    avg_roi = df_sorted[roi_col].mean() if roi_col in df_sorted.columns else 0
    
    # Top 10 opportunities
    top_10 = df_sorted.head(10)
    
    # Calculate investment and returns
    total_investment_needed = 0
    expected_profit_30d = 0
    expected_profit_60d = 0
    expected_profit_90d = 0
    
    buy_now_count = 0
    monitor_count = 0
    high_risk_count = 0
    
    for _, row in top_10.iterrows():
        net_cost = row.get('Net Cost €', 0) if 'Net Cost €' in row else row.get('net_cost', 0)
        gross_margin = row.get('Gross Margin €', 0) if 'Gross Margin €' in row else 0
        roi = row.get(roi_col, 0)
        velocity = row.get('Velocity Score', 50) if 'Velocity Score' in row else row.get('velocity_score', 50)
        risk_score = row.get('Risk Score', 50) if 'Risk Score' in row else row.get('risk_score', 50)
        
        # Investment calculation (suggested quantity based on ROI)
        if roi > 30:
            suggested_qty = 10
        elif roi > 15:
            suggested_qty = 5
        else:
            suggested_qty = 2
            
        investment = net_cost * suggested_qty
        total_investment_needed += investment
        
        # Sales estimation based on velocity
        if velocity >= 70:
            monthly_sales = 20
        elif velocity >= 50:
            monthly_sales = 10
        else:
            monthly_sales = 5
            
        monthly_profit = gross_margin * monthly_sales
        expected_profit_30d += monthly_profit
        expected_profit_60d += monthly_profit * 2
        expected_profit_90d += monthly_profit * 3
        
        # Risk categorization
        if roi > 30 and velocity > 70 and risk_score < 40:
            buy_now_count += 1
        elif roi > 15 and velocity > 50:
            monitor_count += 1
            
        if risk_score > 60:
            high_risk_count += 1
    
    # ROI calculations
    portfolio_roi_30d = (expected_profit_30d / total_investment_needed * 100) if total_investment_needed > 0 else 0
    portfolio_roi_60d = (expected_profit_60d / total_investment_needed * 100) if total_investment_needed > 0 else 0
    portfolio_roi_90d = (expected_profit_90d / total_investment_needed * 100) if total_investment_needed > 0 else 0
    
    # Generate executive summary
    summary = f"""# 📊 Executive Summary - Amazon Arbitrage Analysis

**Generated:** {datetime.now().strftime('%d/%m/%Y %H:%M')} | **Analysis Parameters:** {params.get('purchase_strategy', 'N/A')} | {params.get('discount', 0)*100:.0f}% discount

---

## 🎯 KEY BUSINESS METRICS

### Investment Overview
- **Total Opportunities Analyzed:** {total_opportunities:,}
- **Top 10 Investment Required:** €{total_investment_needed:,.2f}
- **Average ROI (Individual):** {avg_roi:.1f}%
- **Portfolio ROI (30d):** {portfolio_roi_30d:.1f}%

### Expected Returns
| Period | Expected Profit | Portfolio ROI |
|--------|----------------|---------------|
| 30 days | €{expected_profit_30d:,.2f} | {portfolio_roi_30d:.1f}% |
| 60 days | €{expected_profit_60d:,.2f} | {portfolio_roi_60d:.1f}% |
| 90 days | €{expected_profit_90d:,.2f} | {portfolio_roi_90d:.1f}% |

---

## 🏆 TOP 10 OPPORTUNITIES (Action Ready)

| # | ASIN | Product | Route | ROI | Action | Investment | 30d Profit |
|---|------|---------|--------|-----|--------|------------|------------|"""

    # Add top 10 opportunities table
    for i, (_, row) in enumerate(top_10.iterrows(), 1):
        asin = row.get('ASIN', 'N/A')
        title = str(row.get('Title', 'N/A'))[:25] + "..." if len(str(row.get('Title', ''))) > 25 else str(row.get('Title', 'N/A'))
        route = row.get('Best Route', 'N/A') if 'Best Route' in row else row.get('route', 'N/A')
        roi = row.get(roi_col, 0)
        net_cost = row.get('Net Cost €', 0) if 'Net Cost €' in row else row.get('net_cost', 0)
        gross_margin = row.get('Gross Margin €', 0) if 'Gross Margin €' in row else 0
        velocity = row.get('Velocity Score', 50) if 'Velocity Score' in row else row.get('velocity_score', 50)
        risk_score = row.get('Risk Score', 50) if 'Risk Score' in row else row.get('risk_score', 50)
        
        # Determine action
        if roi > 30 and velocity > 70 and risk_score < 40:
            action = "🟢 BUY NOW"
        elif roi > 15 and velocity > 50:
            action = "🟡 MONITOR"
        else:
            action = "🔴 SKIP"
            
        # Calculate suggested investment and profit
        suggested_qty = 10 if roi > 30 else 5 if roi > 15 else 2
        investment = net_cost * suggested_qty
        monthly_sales = 20 if velocity >= 70 else 10 if velocity >= 50 else 5
        profit_30d = gross_margin * monthly_sales
        
        summary += f"\n| {i} | {asin} | {title} | {route} | {roi:.1f}% | {action} | €{investment:.0f} | €{profit_30d:.0f} |"
    
    # Risk analysis section
    summary += f"""

---

## ⚠️ RISK ANALYSIS

### Action Distribution (Top 10)
- **🟢 BUY NOW (High Confidence):** {buy_now_count} opportunities
- **🟡 MONITOR (Medium Risk):** {monitor_count} opportunities  
- **🔴 SKIP (High Risk/Low ROI):** {10 - buy_now_count - monitor_count} opportunities

### Risk Assessment
- **High Risk Products (>60 risk score):** {high_risk_count} out of 10
- **Risk-Adjusted ROI:** Consider starting with BUY NOW items only
- **Diversification:** Recommended across {len(set(top_10['Best Route'].dropna())) if 'Best Route' in top_10.columns else 1} different routes

---

## 💡 EXECUTIVE RECOMMENDATIONS

### Immediate Actions (Next 7 Days)
1. **Start with BUY NOW items** - Lowest risk, highest probability
2. **Allocate €{total_investment_needed * 0.3:.0f}** for initial test purchases (30% of total)
3. **Focus on top 3 opportunities** for maximum impact

### 30-Day Strategy
- **Expected breakeven:** 15-20 days based on velocity scores
- **Scale successful products** after initial test results
- **Monitor price changes** on MONITOR category items

### 90-Day Outlook
- **Portfolio target:** €{expected_profit_90d:,.0f} total profit
- **ROI target:** {portfolio_roi_90d:.1f}% portfolio return
- **Risk mitigation:** Diversify across multiple routes and price points

---

*Analysis powered by Amazon Analyzer Pro v2.0 | Action-Ready Business Intelligence*
"""

    return summary