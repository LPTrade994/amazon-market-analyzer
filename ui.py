"""Streamlit UI helper functions."""

from __future__ import annotations

import streamlit as st


def apply_dark_theme():
    """Inject the custom dark theme CSS used by the dashboard."""
    st.markdown(
        "<style>\n" + (
            open("style.css", "r", encoding="utf-8").read() if st._is_running_with_streamlit else ""
        ) + "\n</style>",
        unsafe_allow_html=True,
    )
