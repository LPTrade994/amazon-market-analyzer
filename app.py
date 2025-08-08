import streamlit as st

# QUESTO DEVE ESSERE IL PRIMO COMANDO STREAMLIT
# Prima di qualsiasi altra importazione che potrebbe contenere comandi Streamlit
st.set_page_config(
    page_title="Amazon Market Analyzer - Arbitraggio Multi-Mercato",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ora possiamo importare altri moduli
import pandas as pd
import numpy as np
import re
import altair as alt
import io
import json
import math, statistics
from typing import Optional, Dict, Any
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_extras.colored_header import colored_header
from loaders import (
    load_data,
    parse_float,
    parse_int,
    parse_weight,
)
from score import (
    SHIPPING_COSTS,
    VAT_RATES,
    normalize_locale,
    calculate_shipping_cost,
    calc_final_purchase_price,
    format_trend,
    classify_opportunity,
    compute_scores,
    aggregate_opportunities,
)
from utils import load_preset, save_preset
from ui import apply_dark_theme

apply_dark_theme()

# Result grid column order
# Only the following columns are displayed in this exact sequence.
DISPLAY_COLS_ORDER = [
    "Locale (base)",
    "Locale (comp)",
    "Title (base)",
    "ASIN",
    "Margine_Stimato",
    "Margine_Netto_%",
    "Margine_Netto",
    "Price_Base",
    "Acquisto_Netto",
    "Shipping_Cost",
    "Price_Comp",
    "Vendita_Netto",
    "Bought_Comp",
    "SalesRank_Comp",
    "Trend",
    "NewOffer_Comp",
    "Opportunity_Score",
    "Opportunity_Class",
    "Volume_Score",
    "Weight_kg",
    "Package: Dimension (cm³) (base)",
    "IVA_Origine",
    "IVA_Confronto",
]


# Helper functions
def float_or_nan(x) -> float:
    try:
        if x is None:
            return float("nan")
        if isinstance(x, (int, float)):
            return float(x)
        s = (
            str(x)
            .strip()
            .replace("%", "")
            .replace("\u202f", "")
            .replace(" ", "")
        )
        s = s.replace(".", "").replace(",", ".") if s.count(",") and s.count(".") <= 1 else s
        return float(s)
    except Exception:
        return float("nan")


def euro_to_float(x: Any) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    s = str(x).replace("€", "").strip()
    return float_or_nan(s)


def apply_discounts(price_gross: float, coupon_abs, coupon_pct, business_pct) -> float:
    p = float(price_gross) if math.isfinite(price_gross) else float("nan")
    if not math.isfinite(p):
        return p
    ca = euro_to_float(coupon_abs)
    cp = float_or_nan(coupon_pct)
    bp = float_or_nan(business_pct)
    if math.isfinite(ca) and ca > 0:
        p = max(0.0, p - ca)
    if math.isfinite(cp) and cp > 0:
        p = p * (1.0 - cp / 100.0)
    if math.isfinite(bp) and bp > 0:
        p = p * (1.0 - bp / 100.0)
    return max(0.0, p)


def pick_current_price(row: pd.Series) -> float:
    # priorità: BB -> Amazon -> New -> New FBM current (se disponibile)
    for col in [
        "Buy Box 🚚: Current",
        "Amazon: Current",
        "New: Current",
        "New, 3rd Party FBM 🚚: Current",
    ]:
        if (
            col in row
            and math.isfinite(euro_to_float(row[col]))
            and euro_to_float(row[col]) > 0
        ):
            return euro_to_float(row[col])
    return float("nan")


def fair_price_row(row: pd.Series) -> float:
    # mediana robusta delle medie storiche (BB/Amazon/New su 90/180/365)
    cols = [
        "Buy Box 🚚: 90 days avg.",
        "Buy Box 🚚: 180 days avg.",
        "Buy Box 🚚: 365 days avg.",
        "Amazon: 90 days avg.",
        "Amazon: 180 days avg.",
        "Amazon: 365 days avg.",
        "New: 90 days avg.",
        "New: 180 days avg.",
        "New: 365 days avg.",
    ]
    vals = [euro_to_float(row.get(c)) for c in cols if c in row]
    vals = [v for v in vals if math.isfinite(v) and v > 0]
    if not vals:
        return float("nan")
    fair = statistics.median(sorted(vals))
    # clamp entro min/max storico BB se disponibili
    low = euro_to_float(row.get("Buy Box 🚚: Lowest"))
    high = euro_to_float(row.get("Buy Box 🚚: Highest"))
    if math.isfinite(low) and fair < low:
        fair = low
    if math.isfinite(high) and fair > high:
        fair = high
    return fair


def get_vat_for_locale(locale_raw: str) -> float:
    # RIUSA la tua mappa IVA se esiste (VAT_RATES + normalize_locale).
    try:
        loc = normalize_locale(locale_raw)
        return VAT_RATES.get(loc, 0.22)
    except Exception:
        return 0.22


def estimate_fulfillment_fee(row: pd.Series) -> float:
    # Se c'è FBA Pick&Pack Fee usalo, altrimenti stima FBM via peso e tua funzione di spedizione
    fba = float_or_nan(row.get("FBA Pick&Pack Fee"))
    if math.isfinite(fba) and fba > 0:
        return fba
    # FBM: calcola costo spedizione dalla tua funzione principale, usando peso pacco/item
    grams = float_or_nan(row.get("Package: Weight (g)"))
    if not math.isfinite(grams) or grams <= 0:
        grams = float_or_nan(row.get("Item: Weight (g)"))
    if not math.isfinite(grams) or grams <= 0:
        grams = 1000.0  # fallback = 1 kg
    kg = grams / 1000.0
    try:
        return calculate_shipping_cost(kg)
    except Exception:
        if kg <= 1:
            return 5.0
        elif kg <= 2:
            return 7.0
        elif kg <= 5:
            return 10.0
        else:
            return 15.0


def demand_score(row: pd.Series) -> float:
    rank_c = float_or_nan(row.get("Sales Rank: Current"))
    rank_90 = float_or_nan(row.get("Sales Rank: 90 days avg."))
    bought = float_or_nan(row.get("Bought in past month"))
    rev_now = float_or_nan(row.get("Reviews: Rating Count"))
    rev_90 = float_or_nan(row.get("Reviews: Rating Count - 90 days avg."))

    def vol(r):
        if not math.isfinite(r) or r <= 0:
            return 0.0
        return max(0.0, min(100.0, 1000.0 / math.log(r + 10.0)))

    base = vol(rank_c)
    if math.isfinite(rank_c) and math.isfinite(rank_90) and rank_c < rank_90:
        base *= 1.10
    if math.isfinite(bought) and bought > 0:
        base += min(30.0, 10.0 * math.log(1.0 + bought))
    if math.isfinite(rev_now) and math.isfinite(rev_90) and rev_now > rev_90:
        base += min(10.0, (rev_now - rev_90) * 0.02)
    return float(max(0.0, min(100.0, base)))


def competition_score(row: pd.Series) -> float:
    offers = float_or_nan(row.get("New Offer Count: Current"))
    amz90 = float_or_nan(row.get("Buy Box: % Amazon 90 days"))
    amz180 = float_or_nan(row.get("Buy Box: % Amazon 180 days"))
    amz = max(
        amz90 if math.isfinite(amz90) else 0.0,
        amz180 if math.isfinite(amz180) else 0.0,
    )
    unq = 100.0 if str(row.get("Buy Box: Unqualified")).strip().lower() == "yes" else 0.0
    off_pen = min(100.0, (offers / 50.0) * 50.0) if math.isfinite(offers) else 0.0
    amz_pen = min(100.0, amz) if math.isfinite(amz) else 0.0
    return float(max(0.0, min(100.0, 0.6 * off_pen + 0.4 * amz_pen + 0.5 * unq)))


def scale_0_100(series: pd.Series) -> pd.Series:
    s = series.astype(float).replace([np.inf, -np.inf], np.nan)
    mn, mx = s.min(skipna=True), s.max(skipna=True)
    if not math.isfinite(mn) or not math.isfinite(mx) or mx == mn:
        return pd.Series([50.0] * len(s), index=s.index)
    return (s - mn) * 100.0 / (mx - mn)


@st.cache_data(show_spinner=False)
def compute_historic_deals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    work["PriceNowGross"] = work.apply(pick_current_price, axis=1)
    work["PriceNowGrossAfterDisc"] = work.apply(
        lambda r: apply_discounts(
            r["PriceNowGross"],
            r.get("One Time Coupon: Absolute"),
            r.get("One Time Coupon: Percentage"),
            r.get("Business Discount: Percentage"),
        ),
        axis=1,
    )
    if "Locale" not in work.columns:
        work["Locale"] = (
            work.get("Locale (comp)", pd.Series("", index=work.index)).fillna("").astype(str)
            + work.get("Locale (base)", pd.Series("", index=work.index)).fillna("").astype(str)
        )
    work["VAT"] = work["Locale"].apply(get_vat_for_locale)
    work["NetSale"] = work["PriceNowGrossAfterDisc"] / (1.0 + work["VAT"])

    work["FairPrice"] = work.apply(fair_price_row, axis=1)
    work["UnderPct"] = (
        work["FairPrice"] - work["PriceNowGrossAfterDisc"]
    ) / work["FairPrice"]
    work.loc[~np.isfinite(work["UnderPct"]), "UnderPct"] = np.nan

    work["ReferralFeePct"] = work.get(
        "Referral Fee %", pd.Series(np.nan, index=work.index)
    ).apply(float_or_nan).fillna(0.0)
    work["ReferralFee€"] = work["NetSale"] * (work["ReferralFeePct"] / 100.0)
    work["Fulfillment€"] = work.apply(estimate_fulfillment_fee, axis=1)
    work["NetProceed€"] = (
        work["NetSale"] - work["ReferralFee€"] - work["Fulfillment€"]
    )

    if "Acquisto_Netto" not in work.columns:
        work["Acquisto_Netto"] = np.nan

    work["Marg€"] = work["NetProceed€"] - work["Acquisto_Netto"]
    work["Marg%"] = np.where(
        work["Acquisto_Netto"] > 0,
        work["Marg€"] / work["Acquisto_Netto"],
        np.nan,
    )

    work["Demand"] = work.apply(demand_score, axis=1)
    vol_candidates = []
    for c in [
        "Buy Box: Standard Deviation 90 days",
        "Buy Box: Standard Deviation 30 days",
        "Buy Box: Standard Deviation 365 days",
    ]:
        if c in work.columns:
            vol_candidates.append(work[c].apply(euro_to_float))
    work["Volatility"] = (
        pd.concat(vol_candidates, axis=1).bfill(axis=1).iloc[:, 0]
        if vol_candidates
        else np.nan
    )
    work["Competition"] = work.apply(competition_score, axis=1)

    work["Badge_AMZ_OOS"] = (
        work.get("Amazon: 90 days OOS", pd.Series(0, index=work.index)).fillna(0) > 0
    )
    amzbb90 = work.get("Buy Box: % Amazon 90 days", pd.Series(0, index=work.index))
    amzbb90 = amzbb90.apply(float_or_nan)
    work["Badge_BB_Amazon"] = amzbb90.fillna(0) > 50
    work["Badge_Coupon"] = (
        work.get("One Time Coupon: Absolute", pd.Series(0, index=work.index))
        .apply(euro_to_float)
        .fillna(0)
        > 0
    ) | (
        work.get("One Time Coupon: Percentage", pd.Series(0, index=work.index))
        .apply(float_or_nan)
        .fillna(0)
        > 0
    )
    work["Badge_Prime"] = (
        work.get("Prime Eligible (Buy Box)", pd.Series(False, index=work.index))
        .astype(str)
        .str.lower()
        .eq("yes")
    )
    work["Badge_VolHigh"] = False
    work["Badge_MAP"] = (
        work.get("MAP restriction", pd.Series("", index=work.index))
        .astype(str)
        .str.lower()
        .eq("yes")
    )

    return work

def render_results(df_finale: pd.DataFrame, df_ranked: pd.DataFrame, include_shipping: bool) -> None:
    """Render the dashboard and detailed results grids."""
    #################################
    # Dashboard Interattiva
    #################################
    with tab_main2:
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        st.subheader("📊 Dashboard delle Opportunità")

        # Metriche principali
        if not df_finale.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Prodotti Trovati", len(df_finale))
            with col2:
                st.metric(
                    "Margine Netto Medio (%)",
                    f"{df_finale['Margine_Netto_%'].mean():.2f}%",
                )
            with col3:
                st.metric(
                    "Margine Netto Medio (€)",
                    f"{df_finale['Margine_Netto'].mean():.2f}€",
                )
            with col4:
                st.metric(
                    "Opportunity Score Massimo",
                    f"{df_finale['Opportunity_Score'].max():.2f}",
                )

            st.info(
                "Aliquote IVA determinate automaticamente per ogni riga | "
                + ("✅ Spedizione Inclusa" if include_shipping else "❌ Spedizione Esclusa")
            )

            dark_colors = {
                "Eccellente": "#2ecc71",
                "Buona": "#27ae60",
                "Discreta": "#f39c12",
                "Bassa": "#e74c3c",
            }

            st.subheader("Distribuzione Opportunity Score")
            hist = (
                alt.Chart(df_finale.reset_index())
                .mark_bar()
                .encode(
                    alt.X(
                        "Opportunity_Score:Q",
                        bin=alt.Bin(maxbins=20),
                        title="Opportunity Score",
                    ),
                    alt.Y("count()", title="Numero di Prodotti"),
                    color=alt.Color(
                        "Opportunity_Class:N",
                        scale=alt.Scale(domain=list(dark_colors.keys()), range=list(dark_colors.values())),
                    ),
                )
                .properties(height=250)
            )
            st.altair_chart(hist, use_container_width=True)

            st.subheader("Analisi Multifattoriale")
            chart = (
                alt.Chart(df_finale.reset_index())
                .mark_circle()
                .encode(
                    x=alt.X("Margine_Netto_%:Q", title="Margine Netto (%)"),
                    y=alt.Y("Opportunity_Score:Q", title="Opportunity Score"),
                    size=alt.Size("Volume_Score:Q", title="Volume Stimato", scale=alt.Scale(range=[20, 200])),
                    color=alt.Color("Locale (comp):N", title="Mercato Confronto", scale=alt.Scale(scheme="category10")),
                    tooltip=[
                        "Title (base)",
                        "ASIN",
                        "Margine_Netto_%",
                        "Margine_Netto",
                        "Shipping_Cost",
                        "SalesRank_Comp",
                        "Opportunity_Score",
                        "Trend",
                    ],
                )
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)

            st.subheader("Analisi per Mercato")
            if "Locale (comp)" in df_finale.columns:
                market_analysis = (
                    df_finale.groupby("Locale (comp)")
                    .agg({
                        "ASIN": "count",
                        "Margine_Netto_%": "mean",
                        "Margine_Netto": "mean",
                        "Shipping_Cost": "mean",
                        "Opportunity_Score": "mean",
                    })
                    .reset_index()
                )
                market_analysis.columns = [
                    "Mercato",
                    "Prodotti",
                    "Margine Netto Medio (%)",
                    "Margine Netto Medio (€)",
                    "Costo Spedizione Medio (€)",
                    "Opportunity Score Medio",
                ]
                market_analysis = market_analysis.round(2)
                st.dataframe(market_analysis, use_container_width=True)

                market_chart = (
                    alt.Chart(market_analysis)
                    .mark_bar()
                    .encode(
                        x="Mercato:N",
                        y="Opportunity Score Medio:Q",
                        color=alt.Color("Mercato:N", scale=alt.Scale(scheme="category10")),
                        tooltip=[
                            "Mercato",
                            "Prodotti",
                            "Margine Netto Medio (%)",
                            "Margine Netto Medio (€)",
                            "Costo Spedizione Medio (€)",
                            "Opportunity Score Medio",
                        ],
                    )
                    .properties(height=300)
                )
                st.altair_chart(market_chart, use_container_width=True)
        else:
            st.info("Nessun prodotto trovato con i filtri applicati.")

        st.markdown("</div>", unsafe_allow_html=True)

    # Risultati dettagliati e filtri interattivi
    with tab_main3:
        if df_finale is not None and not df_finale.empty:
            st.markdown('<div class="result-container">', unsafe_allow_html=True)
            st.subheader("🔍 Esplora i Risultati")

            st.markdown('<div class="filter-group">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)

            filtered_df = df_finale.copy()

            with col1:
                if "Locale (comp)" in filtered_df.columns:
                    markets = ["Tutti"] + sorted(filtered_df["Locale (comp)"].unique().tolist())
                    selected_market = st.selectbox("Filtra per Mercato", markets)
                    if selected_market != "Tutti":
                        filtered_df = filtered_df[filtered_df["Locale (comp)"] == selected_market]

            with col2:
                if "Brand (base)" in filtered_df.columns:
                    brands = ["Tutti"] + sorted(filtered_df["Brand (base)"].unique().tolist())
                    selected_brand = st.selectbox("Filtra per Brand", brands)
                    if selected_brand != "Tutti":
                        filtered_df = filtered_df[filtered_df["Brand (base)"] == selected_brand]

            with col3:
                if "Opportunity_Class" in filtered_df.columns:
                    classes = ["Tutti"] + sorted(filtered_df["Opportunity_Class"].unique().tolist())
                    selected_class = st.selectbox("Filtra per Qualità Opportunità", classes)
                    if selected_class != "Tutti":
                        filtered_df = filtered_df[filtered_df["Opportunity_Class"] == selected_class]

            col1, col2 = st.columns(2)
            with col1:
                min_op_score = st.slider(
                    "Opportunity Score Minimo",
                    min_value=float(filtered_df["Opportunity_Score"].min()),
                    max_value=float(filtered_df["Opportunity_Score"].max()),
                    value=float(filtered_df["Opportunity_Score"].min()),
                )
                filtered_df = filtered_df[filtered_df["Opportunity_Score"] >= min_op_score]

            with col2:
                min_margin = st.slider(
                    "Margine Netto Minimo (€)",
                    min_value=float(filtered_df["Margine_Netto"].min()),
                    max_value=float(filtered_df["Margine_Netto"].max()),
                    value=float(filtered_df["Margine_Netto"].min()),
                )
                filtered_df = filtered_df[filtered_df["Margine_Netto"] >= min_margin]

            search_term = st.text_input("Cerca per ASIN o Titolo")
            if search_term:
                mask = filtered_df["ASIN"].str.contains(search_term, case=False, na=False) | filtered_df[
                    "Title (base)"
                ].str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]

            st.markdown("</div>", unsafe_allow_html=True)

            if not filtered_df.empty:
                def highlight_opportunity(val):
                    if val == "Eccellente":
                        return "background-color: #153d2e; color: #2ecc71; font-weight: bold"
                    elif val == "Buona":
                        return "background-color: #14432d; color: #27ae60; font-weight: bold"
                    elif val == "Discreta":
                        return "background-color: #402d10; color: #f39c12; font-weight: bold"
                    else:
                        return "background-color: #3d1a15; color: #e74c3c; font-weight: bold"

                def format_with_html(df):
                    styled = df.style.map(
                        lambda x: highlight_opportunity(x)
                        if x in ["Eccellente", "Buona", "Discreta", "Bassa"]
                        else "",
                        subset=["Opportunity_Class"],
                    )
                    return styled.format(
                        {
                            "Price_Base": "€{:.2f}",
                            "Acquisto_Netto": "€{:.2f}",
                            "Price_Comp": "€{:.2f}",
                            "Vendita_Netto": "€{:.2f}",
                            "Margine_Stimato": "€{:.2f}",
                            "Shipping_Cost": "€{:.2f}",
                            "Margine_Netto": "€{:.2f}",
                            "Margine_Netto_%": "{:.2f}%",
                            "Opportunity_Score": "{:.2f}",
                            "Volume_Score": "{:.2f}",
                            "Weight_kg": "{:.2f} kg",
                        }
                    )

                st.markdown(f"**{len(filtered_df)} prodotti trovati**")

                display_cols = [c for c in DISPLAY_COLS_ORDER if c in filtered_df.columns]
                filtered_df = filtered_df[display_cols]

                go = GridOptionsBuilder.from_dataframe(filtered_df)
                go.configure_default_column(sortable=True, filter=True)
                go.configure_grid_options(enableRangeSelection=True)
                go.configure_grid_options(autoSizeStrategy={"type": "fitGridWidth"})
                go = go.build()

                container_cls = "fullscreen" if st.session_state.get("grid_fullscreen") else ""
                st.markdown(f'<div id="results_grid_container" class="{container_cls}">', unsafe_allow_html=True)

                if st.session_state.get("grid_fullscreen"):
                    if st.button("Chiudi", key="close_grid_fullscreen"):
                        st.session_state["grid_fullscreen"] = False
                else:
                    if st.button("Schermo intero", key="open_grid_fullscreen"):
                        st.session_state["grid_fullscreen"] = True

                AgGrid(
                    filtered_df,
                    gridOptions=go,
                    update_mode=GridUpdateMode.NO_UPDATE,
                    theme="streamlit",
                    key="results_grid",
                    enable_enterprise_modules=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                csv_data = filtered_df.to_csv(index=False, sep=";").encode("utf-8")
                excel_data = io.BytesIO()
                filtered_df.to_excel(excel_data, index=False)
                excel_data.seek(0)

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Scarica CSV",
                        data=csv_data,
                        file_name="risultato_opportunity_arbitrage.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with col2:
                    st.download_button(
                        label="📥 Scarica Excel",
                        data=excel_data,
                        file_name="risultato_opportunity_arbitrage.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            else:
                st.warning("Nessun prodotto corrisponde ai filtri selezionati.")

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(
                "👈 Clicca su 'Calcola Opportunity Score' nella barra laterale per visualizzare i risultati."
            )

    with tab_rank:
        if df_ranked is not None and not df_ranked.empty:
            st.markdown('<div class="result-container">', unsafe_allow_html=True)
            st.subheader("🏆 Classifica prodotti")
            st.dataframe(df_ranked, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("👈 Calcola le opportunità per vedere la classifica.")


# Inizializzazione delle "ricette" in session_state
if "recipes" not in st.session_state:
    st.session_state["recipes"] = {}

# Inizializzazione dei dati filtrati per la sessione
if "filtered_data" not in st.session_state:
    st.session_state["filtered_data"] = None
if "ranked_data" not in st.session_state:
    st.session_state["ranked_data"] = None

# Flag to indicate if a previous analysis is available
analysis_available = (
    st.session_state["filtered_data"] is not None
    and not st.session_state["filtered_data"].empty
)

# State for fullscreen grid view
if "grid_fullscreen" not in st.session_state:
    st.session_state["grid_fullscreen"] = False

st.markdown(
    '<h1 class="main-header">📊 Amazon Market Analyzer - Arbitraggio Multi-Mercato</h1>',
    unsafe_allow_html=True,
)

tab_main1, tab_main2, tab_main3, tab_rank, tab_deals = st.tabs(
    [
        "📋 ASIN Caricati",
        "📊 Analisi Opportunità",
        "📎 Risultati Dettagliati",
        "🏆 Classifica prodotti",
        "📉 Affari Storici",
    ]
)

#################################
# Sidebar: Caricamento file, Prezzo di riferimento, Sconto, Impostazioni e Ricette
#################################
with st.sidebar:
    colored_header(
        label="🔄 Caricamento Dati",
        description="Carica i file dei mercati",
        color_name="blue-70",
    )

    files_base = st.file_uploader(
        "Lista di Origine (Mercato Base)",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
    )
    comparison_files = st.file_uploader(
        "Liste di Confronto (Mercati di Confronto)",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
    )

    # Precarica i dati base per mostrare gli ASIN disponibili
    df_base = None
    asin_list = []
    if files_base:
        base_list = []
        for f in files_base:
            df_temp = load_data(f)
            if df_temp is not None and not df_temp.empty:
                base_list.append(df_temp)
        if base_list:
            df_base = pd.concat(base_list, ignore_index=True)
            if "ASIN" in df_base.columns:
                asin_list = (
                    df_base["ASIN"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .dropna()
                    .unique()
                    .tolist()
                )

    colored_header(
        label="💰 Impostazioni Prezzi",
        description="Configurazione prezzi",
        color_name="blue-70",
    )
    price_options = ["Buy Box 🚚: Current", "Amazon: Current", "New: Current"]
    ref_price_base = st.selectbox("Per la Lista di Origine", price_options)
    ref_price_comp = st.selectbox("Per la Lista di Confronto", price_options)

    colored_header(
        label="🏷️ Sconto", description="Parametri finanziari", color_name="blue-70"
    )
    discount_percent = st.number_input(
        "Sconto sugli acquisti (%)",
        min_value=0.0,
        value=st.session_state.get("discount_percent", 20.0),
        step=0.1,
        key="discount_percent",
    )
    discount = discount_percent / 100.0  # convertiamo in frazione

    # Sezione per i costi di spedizione
    colored_header(
        label="🚚 Spedizione",
        description="Calcolo costi di spedizione",
        color_name="blue-70",
    )

    # Visualizzazione dei costi di spedizione
    st.markdown('<div class="shipping-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="shipping-title">📦 Listino Costi di Spedizione (Italia)</div>',
        unsafe_allow_html=True,
    )

    # Creare una tabella per il listino
    shipping_table = pd.DataFrame(
        {
            "Peso (kg)": [
                "Fino a 3",
                "Fino a 4",
                "Fino a 5",
                "Fino a 10",
                "Fino a 25",
                "Fino a 50",
                "Fino a 100",
            ],
            "Costo (€)": [
                SHIPPING_COSTS[3],
                SHIPPING_COSTS[4],
                SHIPPING_COSTS[5],
                SHIPPING_COSTS[10],
                SHIPPING_COSTS[25],
                SHIPPING_COSTS[50],
                SHIPPING_COSTS[100],
            ],
        }
    )
    st.dataframe(shipping_table, hide_index=True, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Includi costi di spedizione nel calcolo
    include_shipping = st.checkbox("Calcola margine netto con spedizione", value=True)

    colored_header(
        label="📈 Opportunity Score",
        description="Pesi e parametri",
        color_name="blue-70",
    )

    tab1, tab2 = st.tabs(["Parametri Base", "Parametri Avanzati"])

    with tab1:
        alpha = st.slider(
            "Peso per Sales Rank (penalità)",
            0.0,
            5.0,
            st.session_state.get("alpha", 1.0),
            step=0.1,
            key="alpha",
        )
        beta = st.slider(
            "Peso per 'Bought in past month'",
            0.0,
            5.0,
            st.session_state.get("beta", 1.0),
            step=0.1,
            key="beta",
        )
        delta = st.slider(
            "Peso penalizzante per Offer Count",
            0.0,
            5.0,
            st.session_state.get("delta", 1.0),
            step=0.1,
            key="delta",
        )
        epsilon = st.slider(
            "Peso per il Margine (%)",
            0.0,
            10.0,
            st.session_state.get("epsilon", 3.0),
            step=0.1,
            key="epsilon",
        )  # Valore predefinito aumentato
        zeta = st.slider(
            "Peso per Trend Sales Rank",
            0.0,
            5.0,
            st.session_state.get("zeta", 1.0),
            step=0.1,
            key="zeta",
        )

    with tab2:
        gamma = st.slider(
            "Peso per volume di vendita",
            0.0,
            5.0,
            st.session_state.get("gamma", 2.0),
            step=0.1,
            key="gamma",
        )
        theta = st.slider(
            "Peso per margine assoluto (€)",
            0.0,
            5.0,
            st.session_state.get("theta", 1.5),
            step=0.1,
            key="theta",
        )
        min_margin_multiplier = st.slider(
            "Moltiplicatore margine minimo",
            1.0,
            3.0,
            st.session_state.get("min_margin_multiplier", 1.2),
            step=0.1,
            key="min_margin_multiplier",
        )

    colored_header(
        label="🔍 Filtri Avanzati",
        description="Limita i risultati",
        color_name="blue-70",
    )
    with st.expander("Filtri avanzati"):
        max_sales_rank = st.number_input(
            "Sales Rank massimo", min_value=1, value=999999
        )
        max_offer_count = st.number_input("Offer Count massimo", min_value=1, value=30)
        min_buybox_price = st.number_input(
            "Prezzo minimo (€)", min_value=0.0, value=15.0
        )
        max_buybox_price = st.number_input(
            "Prezzo massimo (€)", min_value=0.0, value=200.0
        )
        min_margin_pct = st.number_input(
            "Margine minimo (%)", min_value=0.0, value=15.0
        )
        min_margin_abs = st.number_input("Margine minimo (€)", min_value=0.0, value=5.0)

    colored_header(
        label="📋 Ricette",
        description="Salva e carica configurazioni",
        color_name="blue-70",
    )
    selected_recipe = st.selectbox(
        "Carica Ricetta",
        options=["-- Nessuna --"] + list(st.session_state["recipes"].keys()),
    )
    if selected_recipe != "-- Nessuna --":
        recipe = st.session_state["recipes"][selected_recipe]
        st.session_state["alpha"] = recipe.get("alpha", 1.0)
        st.session_state["beta"] = recipe.get("beta", 1.0)
        st.session_state["delta"] = recipe.get("delta", 1.0)
        st.session_state["epsilon"] = recipe.get("epsilon", 3.0)
        st.session_state["zeta"] = recipe.get("zeta", 1.0)
        st.session_state["gamma"] = recipe.get("gamma", 2.0)
        st.session_state["theta"] = recipe.get("theta", 1.5)
        st.session_state["min_margin_multiplier"] = recipe.get(
            "min_margin_multiplier", 1.2
        )
        st.session_state["discount_percent"] = recipe.get("discount_percent", 20.0)

    new_recipe_name = st.text_input("Nome Nuova Ricetta")
    if st.button("💾 Salva Ricetta"):
        if new_recipe_name:
            st.session_state["recipes"][new_recipe_name] = {
                "alpha": st.session_state.get("alpha", 1.0),
                "beta": st.session_state.get("beta", 1.0),
                "delta": st.session_state.get("delta", 1.0),
                "epsilon": st.session_state.get("epsilon", 3.0),
                "zeta": st.session_state.get("zeta", 1.0),
                "gamma": st.session_state.get("gamma", 2.0),
                "theta": st.session_state.get("theta", 1.5),
                "min_margin_multiplier": st.session_state.get(
                    "min_margin_multiplier", 1.2
                ),
                "discount_percent": st.session_state.get("discount_percent", 20.0),
            }
            st.success(f"Ricetta '{new_recipe_name}' salvata!")
        else:
            st.error("Inserisci un nome valido per la ricetta.")

    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("💾 Salva preset", use_container_width=True):
            if new_recipe_name:
                save_preset(
                    new_recipe_name, st.session_state["recipes"][new_recipe_name]
                )
    with col_load:
        if st.button("📂 Carica preset", use_container_width=True):
            if selected_recipe != "-- Nessuna --":
                loaded = load_preset(selected_recipe)
                if loaded:
                    st.session_state.update(loaded)

    st.markdown("---")
    avvia = st.button("🚀 Calcola Opportunity Score", use_container_width=True)

with tab_main1:
    if asin_list:
        asin_text = "\n".join(asin_list)
        st.text_area("ASIN caricati", value=asin_text, height=200, key="asin_display")
        st.markdown(
            f"""
            <button class="copy-button" id="copy-asins">📋 Copia ASIN</button>
            <div id="copy-notification">Copiato!</div>
            <script>
            const asinText = {json.dumps(asin_text)};
            const btn = document.getElementById('copy-asins');
            btn.addEventListener('click', function() {{
                navigator.clipboard.writeText(asinText);
                const note = document.getElementById('copy-notification');
                note.classList.add('show-notification');
                setTimeout(() => note.classList.remove('show-notification'), 2000);
            }});
            </script>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Carica una Lista di Origine per visualizzare gli ASIN.")

#################################
# Funzioni di Caricamento e Parsing
#################################

#################################
# Elaborazione Completa e Calcolo Opportunity Score
#################################
if avvia:
    if not files_base:
        with tab_main1:
            st.error("Carica almeno un file di Lista di Origine.")
        st.stop()

    base_list = []
    for f in files_base:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            base_list.append(df_temp)
        else:
            with tab_main1:
                st.warning(f"Il file base {f.name} è vuoto o non valido.")
    if not base_list:
        with tab_main1:
            st.error("Nessun file di origine valido caricato.")
        st.stop()

    df_base = pd.concat(base_list, ignore_index=True)

    # Controllo file di confronto
    if not comparison_files:
        with tab_main1:
            st.error("Carica almeno un file di Liste di Confronto.")
        st.stop()

    # Elaborazione Liste di Confronto
    comp_list = []
    for f in comparison_files:
        df_temp = load_data(f)
        if df_temp is not None and not df_temp.empty:
            comp_list.append(df_temp)
        else:
            with tab_main1:
                st.warning(f"Il file di confronto {f.name} è vuoto o non valido.")
    if not comp_list:
        with tab_main1:
            st.error("Nessun file di confronto valido caricato.")
        st.stop()
    df_comp = pd.concat(comp_list, ignore_index=True)

    # Verifica della presenza della colonna ASIN in entrambi i dataset
    if "ASIN" not in df_base.columns or "ASIN" not in df_comp.columns:
        with tab_main1:
            st.error(
                "Assicurati che entrambi i file (origine e confronto) contengano la colonna ASIN."
            )
        st.stop()

    # Normalizza gli ASIN rimuovendo spazi e usando il maiuscolo
    df_base["ASIN"] = df_base["ASIN"].str.strip().str.upper()
    df_comp["ASIN"] = df_comp["ASIN"].str.strip().str.upper()

    # Merge tra base e confronto sulla colonna ASIN
    df_merged = pd.merge(
        df_base, df_comp, on="ASIN", how="inner", suffixes=(" (base)", " (comp)")
    )
    if df_merged.empty:
        with tab_main1:
            st.error(
                "Nessuna corrispondenza trovata tra la Lista di Origine e le Liste di Confronto."
            )
        st.stop()

    # Utilizza le colonne di prezzo selezionate dalla sidebar
    price_col_base = f"{ref_price_base} (base)"
    price_col_comp = f"{ref_price_comp} (comp)"
    df_merged["Price_Base"] = df_merged.get(price_col_base, pd.Series(np.nan)).apply(
        parse_float
    )
    df_merged["Price_Comp"] = df_merged.get(price_col_comp, pd.Series(np.nan)).apply(
        parse_float
    )

    # Conversione dei dati dal mercato di confronto per le altre metriche
    df_merged["SalesRank_Comp"] = df_merged.get(
        "Sales Rank: Current (comp)", pd.Series(np.nan)
    ).apply(parse_int)
    df_merged["Bought_Comp"] = df_merged.get(
        "Bought in past month (comp)", pd.Series(np.nan)
    ).apply(parse_int)
    df_merged["NewOffer_Comp"] = df_merged.get(
        "New Offer Count: Current (comp)", pd.Series(np.nan)
    ).apply(parse_int)
    # Leggi anche il Sales Rank a 30 giorni, se presente
    df_merged["SalesRank_30d"] = df_merged.get(
        "Sales Rank: 30 days avg. (comp)", pd.Series(np.nan)
    ).apply(parse_int)

    # Estrai informazioni sul peso
    # Cerca in varie colonne che potrebbero contenere informazioni sul peso
    possible_weight_cols = [
        "Weight (base)",
        "Item Weight (base)",
        "Package: Weight (kg) (base)",
        "Package: Weight (g) (base)",
        "Product details (base)",
        "Features (base)",
    ]

    # Inizializza colonna peso
    df_merged["Weight_kg"] = np.nan

    # Cerca nelle possibili colonne di peso
    for col in possible_weight_cols:
        if col in df_merged.columns:
            if "(g)" in col:
                # Valori espressi in grammi
                def to_kg(val):
                    if pd.isna(val):
                        return np.nan
                    try:
                        num = re.search(r"(\d+\.?\d*)", str(val))
                        return float(num.group(1)) / 1000 if num else np.nan
                    except Exception:
                        return np.nan

                weight_data = df_merged[col].apply(to_kg)
            else:
                weight_data = df_merged[col].apply(parse_weight)
            # Aggiorna solo i valori mancanti
            df_merged.loc[df_merged["Weight_kg"].isna(), "Weight_kg"] = weight_data.loc[
                df_merged["Weight_kg"].isna()
            ]

    # Se non ci sono informazioni sul peso, imposta un valore predefinito
    df_merged["Weight_kg"] = df_merged["Weight_kg"].fillna(
        1.0
    )  # Assume 1kg come predefinito

    # Calcola il costo di spedizione per ogni prodotto
    df_merged["Shipping_Cost"] = df_merged["Weight_kg"].apply(calculate_shipping_cost)

    # Calcolo del prezzo d'acquisto netto per ogni prodotto dalla lista di origine
    # Utilizzo della funzione aggiornata con IVA variabile
    df_merged["Acquisto_Netto"] = df_merged.apply(
        lambda row: calc_final_purchase_price(row, discount), axis=1
    )

    # NUOVA LOGICA: Calcolo del margine stimato considerando IVA correttamente
    # 1. Prezzo nel mercato di confronto (lordo IVA)
    # 2. Prezzo di acquisto netto (già senza IVA)
    # 3. Margine = Prezzo confronto / (1 + IVA) - Prezzo acquisto netto

    df_merged["Price_Comp"] = df_merged["Price_Comp"].fillna(0)

    # Prezzo netto di vendita nel mercato di confronto (senza IVA)
    df_merged["Vendita_Netto"] = df_merged.apply(
        lambda row: row["Price_Comp"]
        / (
            1 + VAT_RATES.get(normalize_locale(row.get("Locale (comp)", "")), 0) / 100.0
        ),
        axis=1,
    )

    # Margine stimato e percentuale rispetto al prezzo d'acquisto
    df_merged["Margine_Stimato"] = (
        df_merged["Vendita_Netto"] - df_merged["Acquisto_Netto"]
    )
    df_merged["Margine_%"] = (
        df_merged["Margine_Stimato"] / df_merged["Acquisto_Netto"]
    ) * 100

    # Calcolo del margine netto con o senza costi di spedizione
    if include_shipping:
        df_merged["Margine_Netto"] = (
            df_merged["Margine_Stimato"] - df_merged["Shipping_Cost"]
        )
        df_merged["Margine_Netto_%"] = (
            df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]
        ) * 100
    else:
        df_merged["Margine_Netto"] = df_merged["Margine_Stimato"]
        df_merged["Margine_Netto_%"] = df_merged["Margine_%"]

    # Margine percentuale lordo per riferimento
    df_merged["Margin_Pct_Lordo"] = (
        (df_merged["Price_Comp"] - df_merged["Price_Base"]) / df_merged["Price_Base"]
    ) * 100

    df_merged["SalesRank_Comp"] = df_merged["SalesRank_Comp"].fillna(999999)
    df_merged["NewOffer_Comp"] = df_merged["NewOffer_Comp"].fillna(0)
    mask = (
        (df_merged["Margine_Netto_%"] > min_margin_pct)
        & (df_merged["Margine_Netto"] > min_margin_abs)
        & (df_merged["SalesRank_Comp"] <= max_sales_rank)
        & (df_merged["NewOffer_Comp"] <= max_offer_count)
        & (df_merged["Price_Comp"].between(min_buybox_price, max_buybox_price))
    )
    df_merged = df_merged[mask]

    # Calcolo del bonus/penalità per il Trend del Sales Rank
    df_merged["Trend_Bonus"] = np.log(
        (df_merged["SalesRank_30d"].fillna(df_merged["SalesRank_Comp"]) + 1)
        / (df_merged["SalesRank_Comp"] + 1)
    )
    # Formattiamo il trend in una stringa con icona
    df_merged["Trend"] = df_merged["Trend_Bonus"].apply(format_trend)

    df_merged["Norm_Rank"] = np.log(df_merged["SalesRank_Comp"].fillna(999999) + 10)
    df_merged["Volume_Score"] = 1000 / df_merged["Norm_Rank"]
    df_merged["ROI_Factor"] = df_merged["Margine_Netto"] / df_merged["Acquisto_Netto"]

    weights = {
        "margin": epsilon + theta,
        "demand": beta + gamma,
        "competition": delta,
        "volatility": zeta,
        "risk": alpha,
    }
    df_scores = compute_scores(df_merged, weights)
    df_merged["Opportunity_Score"] = df_scores["final_score"]

    min_margin_threshold = min_margin_abs * min_margin_multiplier
    df_merged.loc[
        df_merged["Margine_Netto"] < min_margin_threshold, "Opportunity_Score"
    ] *= (df_merged["Margine_Netto"] / min_margin_threshold)

    # Classificazione dell'opportunità - Correzione dell'errore
    # Invece di assegnare una Series a due colonne, creiamo le colonne separatamente
    df_merged["Opportunity_Class"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[
            0
        ]  # Solo il primo elemento della tupla
    )
    df_merged["Opportunity_Tag"] = df_merged["Opportunity_Score"].apply(
        lambda score: classify_opportunity(score)[
            1
        ]  # Solo il secondo elemento della tupla
    )

    # Aggiunta dell'informazione sulle aliquote IVA utilizzate
    df_merged["IVA_Origine"] = df_merged["Locale (base)"].map(
        lambda x: f"{VAT_RATES.get(normalize_locale(x), 0)}%"
    )
    df_merged["IVA_Confronto"] = df_merged["Locale (comp)"].map(
        lambda x: f"{VAT_RATES.get(normalize_locale(x), 0)}%"
    )

    # Ordiniamo i risultati per Opportunity Score decrescente
    df_merged = df_merged.sort_values("Opportunity_Score", ascending=False)

    # Selezione delle colonne finali da visualizzare
    cols_final = [c for c in DISPLAY_COLS_ORDER if c in df_merged.columns]
    df_finale = df_merged[cols_final].copy()

    # Arrotonda i valori numerici principali a 2 decimali
    cols_to_round = [
        "Price_Base",
        "Acquisto_Netto",
        "Price_Comp",
        "Vendita_Netto",
        "Margine_Stimato",
        "Shipping_Cost",
        "Margine_Netto",
        "Margine_Netto_%",
        "Margine_%",
        "Opportunity_Score",
        "Volume_Score",
        "Weight_kg",
    ]
    for col in cols_to_round:
        if col in df_finale.columns:
            df_finale[col] = df_finale[col].round(2)

    # Classifica cross-country per ASIN
    df_ranked = aggregate_opportunities(df_finale)

    # Salviamo i dati nella sessione per i filtri interattivi
    st.session_state["filtered_data"] = df_finale
    st.session_state["ranked_data"] = df_ranked
    analysis_available = True

    render_results(df_finale, df_ranked, include_shipping)
elif analysis_available:
    render_results(
        st.session_state["filtered_data"],
        st.session_state["ranked_data"],
        include_shipping,
    )

# Aggiunta dell'help
with st.expander("ℹ️ Come funziona l'Opportunity Score"):
    st.markdown(
        """
    ### Calcolo dell'Opportunity Score
    
    L'Opportunity Score è un punteggio che combina diversi fattori per identificare le migliori opportunità di arbitraggio. 
    La formula considera:
    
    - **Margine netto percentuale**: Quanto margine percentuale ottieni dopo aver sottratto i costi di spedizione
    - **Margine netto assoluto**: Quanto guadagno in euro ottieni per ogni vendita dopo i costi di spedizione
    - **Volume di vendita**: Stimato tramite il Sales Rank (più basso = più vendite)
    - **Trend**: Se il prodotto sta migliorando o peggiorando nel ranking
    - **Competizione**: Quante altre offerte ci sono per lo stesso prodotto
    - **Acquisti recenti**: Quanti acquisti sono stati fatti nell'ultimo mese
    
    ### Calcolo del Margine
    
    Il margine viene calcolato considerando:
    1. **Prezzo di acquisto netto**: Prezzo base scontato e senza IVA (usando l'aliquota IVA del mercato di origine)
    2. **Prezzo di vendita netto**: Prezzo di confronto senza IVA (usando l'aliquota IVA del mercato di confronto)
    3. **Margine stimato**: Differenza tra prezzo di vendita netto e prezzo di acquisto netto
    4. **Costi di spedizione**: Calcolati in base al peso del prodotto secondo il listino
    5. **Margine netto**: Margine stimato meno i costi di spedizione
    
    ### Calcolo dei Costi di Spedizione
    
    I costi di spedizione vengono calcolati in base al peso del prodotto secondo questo listino:
    - Fino a 3 kg: €5.14
    - Fino a 4 kg: €6.41
    - Fino a 5 kg: €6.95
    - Fino a 10 kg: €8.54
    - Fino a 25 kg: €12.51
    - Fino a 50 kg: €21.66
    - Fino a 100 kg: €34.16
    
    ### Note sull'IVA
    
    L'applicazione gestisce correttamente l'IVA dei diversi paesi, sia per il mercato di origine che per quello di confronto:
    - Italia: 22%
    - Germania: 19%
    - Francia: 20%
    - Spagna: 21%
    - Regno Unito: 20%
    
    Il margine stimato tiene conto di queste differenze, permettendoti di calcolare correttamente il potenziale guadagno anche quando il mercato di origine è diverso da quello italiano.
    """
    )

# Tab Affari Storici
df_final = st.session_state.get("filtered_data")

with tab_deals:
    st.subheader("Affari Storici")

    colw1, colw2, colw3, colw4, colw5 = st.columns(5)
    with colw1:
        w1 = st.slider("Peso Sottoprezzo", 0.0, 1.0, 0.30, 0.05)
    with colw2:
        w2 = st.slider("Peso Margine %", 0.0, 1.0, 0.25, 0.05)
    with colw3:
        w3 = st.slider("Peso Domanda", 0.0, 1.0, 0.25, 0.05)
    with colw4:
        w4 = st.slider("Penalità Concorrenza", 0.0, 1.0, 0.10, 0.05)
    with colw5:
        w5 = st.slider("Penalità Volatilità", 0.0, 1.0, 0.10, 0.05)

    c1, c2, c3 = st.columns(3)
    with c1:
        min_marg_eur = st.number_input("Margine minimo €", 0.0, 10000.0, 10.0)
        min_under = st.number_input(
            "Sottoprezzo minimo %", 0.0, 1.0, 0.10, format="%.2f"
        )
    with c2:
        min_marg_pct = st.number_input(
            "Margine minimo %", 0.0, 1.0, 0.10, format="%.2f"
        )
        max_rank = st.number_input("Rank massimo", 0.0, 1e7, 200000.0)
    with c3:
        max_offers = st.number_input("Max offerte nuove", 0, 1000, 50)
        max_vol = st.number_input("Max volatilità (std 90d)", 0.0, 10000.0, 50.0)

    excl_amz_bb = st.checkbox(
        "Escludi se %Amazon in Buy Box > 50%", value=True
    )
    only_amz_oos = st.checkbox(
        "Solo prodotti con Amazon OOS negli ultimi 90 giorni", value=False
    )

    deals_df = compute_historic_deals(df_final)

    if deals_df.empty:
        st.info("Nessun dato disponibile per Affari Storici.")
    else:
        vol_series = deals_df["Volatility"].replace([np.inf, -np.inf], np.nan)
        vol_thr = (
            np.nanpercentile(vol_series.dropna(), 75)
            if vol_series.notna().any()
            else np.nan
        )
        if math.isfinite(vol_thr):
            deals_df["Badge_VolHigh"] = deals_df["Volatility"] > vol_thr

        def pct_amz_bb(row):
            s = [
                float_or_nan(row.get("Buy Box: % Amazon 90 days")),
                float_or_nan(row.get("Buy Box: % Amazon 180 days")),
            ]
            return max([x for x in s if math.isfinite(x)] + [0.0])

        mask = pd.Series(True, index=deals_df.index)
        if math.isfinite(min_marg_eur):
            mask &= deals_df["Marg€"].fillna(-1e9) >= min_marg_eur
        if math.isfinite(min_marg_pct):
            mask &= deals_df["Marg%"].fillna(-1e9) >= min_marg_pct
        if math.isfinite(min_under):
            mask &= deals_df["UnderPct"].fillna(-1e9) >= min_under
        mask &= (
            deals_df.get("Sales Rank: Current", np.nan)
            .apply(float_or_nan)
            .fillna(1e12)
            <= max_rank
        )
        mask &= (
            deals_df.get("New Offer Count: Current", np.nan)
            .apply(float_or_nan)
            .fillna(1e9)
            <= max_offers
        )
        mask &= deals_df["Volatility"].fillna(0) <= max_vol
        if excl_amz_bb:
            mask &= deals_df.apply(lambda r: pct_amz_bb(r) <= 50.0, axis=1)
        if only_amz_oos:
            mask &= deals_df.get("Amazon: 90 days OOS", 0).fillna(0) > 0

        deals_f = deals_df[mask].copy()

        S_under = scale_0_100(deals_f["UnderPct"])
        S_marg = scale_0_100(deals_f["Marg%"])
        S_dem = scale_0_100(deals_f["Demand"])
        S_comp = scale_0_100(deals_f["Competition"])
        S_vol = scale_0_100(deals_f["Volatility"])

        deals_f["DealScore"] = (
            w1 * S_under
            + w2 * S_marg
            + w3 * S_dem
            - w4 * S_comp
            - w5 * S_vol
        )
        deals_f["DealScore"] = scale_0_100(deals_f["DealScore"])

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Prodotti (filtrati)", len(deals_f))
        with k2:
            st.metric(
                "Margine medio %",
                f"{np.nanmean(deals_f['Marg%']) * 100:0.1f}%",
            )
        with k3:
            st.metric(
                "Sottoprezzo medio %",
                f"{np.nanmean(deals_f['UnderPct']) * 100:0.1f}%",
            )
        with k4:
            st.metric(
                "DealScore medio",
                f"{np.nanmean(deals_f['DealScore']):0.1f}",
            )

        try:
            scatter = (
                alt.Chart(deals_f.reset_index())
                .mark_circle()
                .encode(
                    x=alt.X("UnderPct:Q", title="Sottoprezzo %"),
                    y=alt.Y("Marg%:Q", title="Margine %"),
                    color=alt.Color("DealScore:Q"),
                    size=alt.Size("Demand:Q"),
                    tooltip=[
                        "ASIN:N",
                        "Title:N",
                        "UnderPct:Q",
                        "Marg%:Q",
                        "DealScore:Q",
                    ],
                )
                .interactive()
            )
            st.altair_chart(scatter, use_container_width=True)

            hist = (
                alt.Chart(deals_f)
                .mark_bar()
                .encode(
                    x=alt.X("DealScore:Q", bin=alt.Bin(maxbins=30), title="DealScore"),
                    y="count()",
                )
            )
            st.altair_chart(hist, use_container_width=True)
        except Exception:
            pass

        show_cols = [
            c
            for c in [
                "Locale",
                "ASIN",
                "Title",
                "PriceNowGrossAfterDisc",
                "FairPrice",
                "UnderPct",
                "NetSale",
                "ReferralFee€",
                "Fulfillment€",
                "NetProceed€",
                "Acquisto_Netto",
                "Marg€",
                "Marg%",
                "Demand",
                "Competition",
                "Volatility",
                "DealScore",
                "URL: Amazon",
                "Brand",
            ]
            if c in deals_f.columns
        ]

        disp = deals_f.copy()
        for c in [
            "PriceNowGrossAfterDisc",
            "FairPrice",
            "NetSale",
            "ReferralFee€",
            "Fulfillment€",
            "NetProceed€",
            "Acquisto_Netto",
            "Marg€",
        ]:
            if c in disp.columns:
                disp[c] = disp[c].map(
                    lambda v: f"€ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    if pd.notna(v)
                    else v
                )
        disp = disp.sort_values("DealScore", ascending=False)
        st.dataframe(disp[show_cols], use_container_width=True)

        cexp1, cexp2 = st.columns(2)
        with cexp1:
            csv = deals_f.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Scarica CSV (Affari Storici)",
                csv,
                file_name="affari_storici.csv",
                mime="text/csv",
            )
        with cexp2:
            try:
                import io
                from pandas import ExcelWriter

                bio = io.BytesIO()
                with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
                    deals_f.to_excel(writer, index=False, sheet_name="AffariStorici")
                st.download_button(
                    "Scarica XLSX (Affari Storici)",
                    bio.getvalue(),
                    file_name="affari_storici.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception:
                pass

# Footer
st.markdown(
    """
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #333; color: #aaa;">
    Amazon Market Analyzer - Arbitraggio Multi-Mercato © 2025<br>
    Versione 2.0
</div>
""",
    unsafe_allow_html=True,
)
