import pandas as pd
from typing import Dict, Any


def compute_net_purchase(price_gross: float, source_locale: str, discount_pct: float, vat_rates: Dict[str, float]) -> float:
    """
    Apply fundamental VAT logic for Italy vs Foreign markets.
    
    MANDATORY RULES:
    
    ITALY (source_locale == 'it'):
    1. Calculate discount on gross price: discount_amount = price_gross * discount_pct
    2. Remove Italian VAT: price_no_vat = price_gross / 1.22
    3. Subtract discount from no-VAT price: net_cost = price_no_vat - discount_amount
    
    FOREIGN (source_locale in ['de', 'fr', 'es']):
    1. Remove local VAT: price_no_vat = price_gross / (1 + vat_rate_local)
    2. Apply discount on no-VAT price: net_cost = price_no_vat * (1 - discount_pct)
    
    Args:
        price_gross: Gross purchase price
        source_locale: Source market locale ('it', 'de', 'fr', 'es')
        discount_pct: Discount percentage (0.21 = 21%)
        vat_rates: Dictionary of VAT rates by locale
        
    Returns:
        float: Net purchase cost after VAT and discount logic
    """
    if price_gross <= 0:
        return 0.0
    
    if source_locale == 'it':
        # ITALY LOGIC
        # 1. Calculate discount on gross price
        discount_amount = price_gross * discount_pct
        
        # 2. Remove Italian VAT (22%)
        price_no_vat = price_gross / 1.22
        
        # 3. Subtract discount from no-VAT price
        net_cost = price_no_vat - discount_amount
        
        return max(net_cost, 0.0)
    
    else:
        # FOREIGN LOGIC (de, fr, es)
        # 1. Get local VAT rate
        vat_rate_local = vat_rates.get(source_locale.upper(), 0.19)  # Default to DE rate
        
        # 2. Remove local VAT
        price_no_vat = price_gross / (1 + vat_rate_local)
        
        # 3. Apply discount on no-VAT price
        net_cost = price_no_vat * (1 - discount_pct)
        
        return max(net_cost, 0.0)


def select_purchase_price(row: pd.Series, strategy: str) -> float:
    """
    Select purchase price from dataset columns based on strategy.
    
    Args:
        row: DataFrame row containing price data
        strategy: Purchase strategy name
        
    Returns:
        float: Selected purchase price, 0 if column missing
    """
    strategy_column_mapping = {
        "Buy Box Current": 'Buy Box 🚚: Current',
        "Amazon Current": 'Amazon: Current',
        "New FBA Current": 'New FBA: Current',
        "New FBM Current": 'New FBM: Current'
    }
    
    column_name = strategy_column_mapping.get(strategy)
    
    if column_name and column_name in row.index:
        price = row[column_name]
        if pd.notna(price) and price > 0:
            return float(price)
    
    return 0.0


def select_target_price(row: pd.Series, target_locale: str, scenario: str) -> float:
    """
    Select target selling price based on locale and scenario.
    ALWAYS uses Buy Box as the primary reference price to beat.
    
    Args:
        row: DataFrame row containing price data
        target_locale: Target market locale ('it', 'de', 'fr', 'es')
        scenario: Pricing scenario ('conservative', 'aggressive', 'current')
        
    Returns:
        float: Target selling price (always based on Buy Box)
    """
    # SEMPRE utilizza Buy Box come prezzo di riferimento primario
    # Questo è il prezzo da battere nel paese di riferimento
    buy_box_column = 'Buy Box 🚚: Current'
    
    # Controlla se il Buy Box è disponibile
    if buy_box_column in row.index and pd.notna(row[buy_box_column]) and row[buy_box_column] > 0:
        base_price = float(row[buy_box_column])
    else:
        # Solo se Buy Box non è disponibile, usa fallback in ordine di priorità
        fallback_columns = [
            'Amazon: Current', 
            'New FBA: Current',
            'New FBM: Current'
        ]
        
        base_price = 0.0
        for col in fallback_columns:
            if col in row.index and pd.notna(row[col]) and row[col] > 0:
                base_price = float(row[col])
                break
    
    if base_price <= 0:
        return 0.0
    
    # Apply scenario adjustment to the Buy Box reference price
    price = base_price
    if price > 0:
        if scenario.lower() == 'short':
            price = price * 0.95  # -5% for quick turnover
        elif scenario.lower() == 'long':
            price = price * 1.05  # +5% for patient approach
        # 'medium' or 'current' = no adjustment
        
        # Keep compatibility with old scenario names
        elif scenario.lower() == 'conservative':
            price = price * 0.95
        elif scenario.lower() == 'aggressive':
            price = price * 1.05
    
    return max(price, 0.0)


def calculate_profit_metrics(row: pd.Series, purchase_strategy: str, target_locale: str, 
                           scenario: str, discount_pct: float, vat_rates: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate comprehensive profit metrics for a product.
    
    Args:
        row: DataFrame row with product data
        purchase_strategy: Purchase strategy name
        target_locale: Target selling market
        scenario: Pricing scenario
        discount_pct: Purchase discount percentage
        vat_rates: VAT rates by locale
        
    Returns:
        Dict with profit metrics
    """
    # Get source locale
    source_locale = row.get('detected_locale', 'it')
    
    # Get purchase price
    purchase_price_gross = select_purchase_price(row, purchase_strategy)
    
    # Calculate net purchase cost
    net_purchase_cost = compute_net_purchase(purchase_price_gross, source_locale, discount_pct, vat_rates)
    
    # Get target selling price  
    target_selling_price = select_target_price(row, target_locale, scenario)
    
    # Calculate fees
    referral_fee_pct = row.get('Referral Fee %', 0.15)
    fba_fee = row.get('FBA Pick&Pack Fee', 2.0)
    
    referral_fee = target_selling_price * referral_fee_pct
    
    # RIMUOVI IVA dal prezzo di vendita per calcolo profitto corretto
    target_vat_rate = vat_rates.get(target_locale.upper(), 0.20)
    target_selling_price_net = target_selling_price / (1 + target_vat_rate)
    
    # Calculate profit (USA PREZZO NETTO)
    gross_profit = target_selling_price_net - net_purchase_cost - referral_fee - fba_fee
    
    # Calculate margins (usa prezzo netto per margine realistico)
    profit_margin = (gross_profit / target_selling_price_net * 100) if target_selling_price_net > 0 else 0
    roi = (gross_profit / net_purchase_cost * 100) if net_purchase_cost > 0 else 0
    
    return {
        'purchase_price_gross': purchase_price_gross,
        'net_purchase_cost': net_purchase_cost,
        'target_selling_price': target_selling_price,
        'referral_fee': referral_fee,
        'fba_fee': fba_fee,
        'gross_profit': gross_profit,
        'profit_margin': profit_margin,
        'roi': roi,
        'source_locale': source_locale,
        'target_locale': target_locale
    }


def calculate_price_volatility_index(row):
    """
    Indice 0-100 dove 0 = massima volatilità (rischio)
    """
    # Coefficiente di variazione su 3 timeframe
    
    # 30 days timeframe
    std_30 = row.get('Buy Box: Standard Deviation 30 days', 0)
    avg_30 = row.get('Buy Box 🚚: 30 days avg.', 1)
    cv_30 = std_30 / avg_30 if avg_30 > 0 else 0
    
    # 90 days timeframe
    std_90 = row.get('Buy Box: Standard Deviation 90 days', 0)
    avg_90 = row.get('Buy Box 🚚: 90 days avg.', 1)
    cv_90 = std_90 / avg_90 if avg_90 > 0 else 0
    
    # 365 days timeframe
    std_365 = row.get('Buy Box: Standard Deviation 365 days', 0)
    avg_365 = row.get('Buy Box 🚚: 365 days avg.', 1)
    cv_365 = std_365 / avg_365 if avg_365 > 0 else 0
    
    # Media ponderata (più peso al recente)
    weighted_cv = (cv_30 * 0.5) + (cv_90 * 0.3) + (cv_365 * 0.2)
    
    # Converti in score 0-100
    volatility_index = max(0, 100 - (weighted_cv * 200))
    
    return volatility_index