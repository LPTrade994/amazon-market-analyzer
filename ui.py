"""Streamlit UI helper functions."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode


def apply_dark_theme():
    """Inject the custom dark theme CSS used by the dashboard."""
    css = ""
    if st.runtime.exists():
        try:
            css = Path(__file__).with_name("style.css").read_text(encoding="utf-8")
        except FileNotFoundError:
            css = ""
    st.markdown("<style>\n" + css + "\n</style>", unsafe_allow_html=True)


def render_triaging_table(df: pd.DataFrame, min_pct: float) -> None:
    """Render a triaging dataframe with styling and tooltips."""
    if df is None or df.empty:
        st.info("Nessun dato disponibile per il triaging.")
        return

    go = GridOptionsBuilder.from_dataframe(df)
    go.configure_default_column(sortable=True, filter=True)

    net_pct_style = JsCode(
        f"""
        function(params) {{
            if (params.value < 0) {{
                return {{'color': 'white', 'backgroundColor': '#c0392b'}};
            }} else if (params.value >= {min_pct}) {{
                return {{'color': 'white', 'backgroundColor': '#27ae60'}};
            }}
            return null;
        }}
        """
    )

    score_renderer = JsCode(
        """
        function(params) {
            const cls = params.data.class;
            let color = '#7f8c8d';
            if (cls === 'A') color = '#27ae60';
            else if (cls === 'B') color = '#f39c12';
            else if (cls === 'C') color = '#c0392b';
            return `<span>${params.value.toFixed(2)}</span> ` +
                   `<span style="background-color:${color};color:white;padding:2px 4px;` +
                   `border-radius:4px;font-size:10px;">${cls}</span>`;
        }
        """
    )

    go.configure_column(
        "Netto %",
        type=["numericColumn"],
        valueFormatter=JsCode("function(p){return p.value.toFixed(2)+'%';}"),
        cellStyle=net_pct_style,
    )
    go.configure_column(
        "Netto €",
        type=["numericColumn"],
        valueFormatter=JsCode("function(p){return p.value.toFixed(2)+'€';}"),
    )
    go.configure_column("Score", cellRenderer=score_renderer)
    go.configure_column("class", hide=True)
    if "tooltip" in df.columns:
        go.configure_column("tooltip", hide=True)
        for c in df.columns:
            go.configure_column(c, tooltipField="tooltip")
        go.configure_grid_options(enableBrowserTooltips=True)

    AgGrid(
        df,
        gridOptions=go.build(),
        update_mode=GridUpdateMode.NO_UPDATE,
        theme="streamlit",
        height=400,
    )
