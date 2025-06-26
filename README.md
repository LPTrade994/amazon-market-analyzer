# Amazon Market Analyzer

This project contains a Streamlit dashboard for analyzing product arbitrage opportunities across different Amazon marketplaces.

## Requirements

- **Python**: 3.10 or higher is recommended.
- Install dependencies either by running `./setup.sh` or manually with `pip install -r requirements.txt`.

## Launching the App

After installing dependencies, start the dashboard with:

```bash
streamlit run app.py
```

## Keepa Export Files

The application expects Keepa CSV/XLSX exports for both the origin marketplace and the comparison marketplaces. Essential headers include:

- `ASIN`
- `Title`
- `Locale`
- Price columns: `Buy Box 🚚: Current`, `Amazon: Current`, `New: Current`
- Metrics: `Sales Rank: Current`, `Sales Rank: 30 days avg.`, `Bought in past month`, `New Offer Count: Current`
- Optional data: `Brand`, `Package: Dimension (cm³)`, `Weight`, `Item Weight`, `Package: Weight (kg)` or `Package: Weight (g)`

These headers must be present (with `(base)` or `(comp)` suffixes after upload) for correct processing.

## Main Features

- **Opportunity Score** – weighted ranking combining margin, volume, sales rank, offers, trend and other factors.
- **Advanced Filters** – limit results by sales rank, offer count, price range and minimum margins.
- **Shipping & VAT Handling** – calculate net margins including shipping costs and market‑specific VAT rates.
- **Interactive Dashboard** – visualize scores, margins and volume with histograms and scatter plots; save/load parameter "recipes" for repeated analyses.

