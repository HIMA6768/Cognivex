"""Streamlit entrypoint for the biomedical research prototype."""

from __future__ import annotations

import streamlit as st

from src.ui.shell import render_app


st.set_page_config(
    page_title="OncoMap | Breast Cancer Research Analysis",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto",
)
render_app()
