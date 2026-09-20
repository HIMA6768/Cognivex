"""Static visual tokens and theme injection for the Streamlit shell."""

from __future__ import annotations

import streamlit as st


APP_CSS = """
:root {
    --cv-navy: #0B1F33;
    --cv-slate: #344054;
    --cv-text: #101828;
    --cv-muted-text: #667085;
    --cv-blue: #2563EB;
    --cv-canvas: #F5F7FA;
    --cv-surface: #FFFFFF;
    --cv-border: #DDE3EA;
    --cv-success: #16794B;
    --cv-amber: #B54708;
    --cv-teal: #0F9E9A;
    --cv-soft-blue: #EAF2FF;
    --cv-soft-teal: #E8F8F6;
    --cv-card-radius: 14px;
    --cv-control-radius: 10px;
}

.stApp {
    background: var(--cv-canvas);
    color: var(--cv-text);
}

[data-testid="stSidebar"] {
    background: var(--cv-navy);
}

.cv-sidebar-brand,
.cv-sidebar-brand *,
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:not(:disabled)),
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:not(:disabled)) p {
    color: var(--cv-surface);
}

.cv-sidebar-product-name {
    display: block;
    font-size: 1.3rem;
    font-weight: 700;
    line-height: 1.3;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    color: #B8C7D9;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    margin-top: 1.25rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label {
    border-radius: 8px;
    margin: 0.12rem 0;
    padding: 0.3rem 0.45rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(37, 99, 235, 0.32);
}

.cv-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0.5rem 0 1rem;
    padding: 0.4rem 0.65rem;
    background: #155F3A;
    border: 1px solid #84D3A5;
    border-radius: 999px;
    color: #FFFFFF;
    font-size: 0.875rem;
    font-weight: 600;
}

.block-container {
    max-width: 1120px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.cv-surface {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    border-radius: var(--cv-card-radius);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    padding: 1.5rem;
}

.cv-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
    gap: 1rem;
    margin: 1rem 0;
}

.cv-metric-card,
.cv-status-card {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    border-radius: var(--cv-card-radius);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    padding: 1rem 1.15rem;
}

.cv-metric-card__value {
    color: var(--cv-navy);
    font-size: 1.75rem;
    font-weight: 750;
    line-height: 1.1;
}

.cv-metric-card__label,
.cv-status-badge {
    color: var(--cv-muted-text);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.cv-status-badge--ready {
    color: var(--cv-success);
}

.cv-status-badge--unavailable {
    color: var(--cv-amber);
}

[data-testid="stFileUploader"] section {
    background: var(--cv-surface);
    border: 1px dashed var(--cv-border);
    border-radius: var(--cv-card-radius);
    padding: 0.5rem;
}

[data-testid="stFileUploader"] button {
    border-color: var(--cv-blue);
    color: var(--cv-blue);
}

button,
input,
textarea,
[role="radio"] {
    border-radius: var(--cv-control-radius);
}

button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[role="radio"]:focus-visible,
a:focus-visible {
    outline: 3px solid var(--cv-blue);
    outline-offset: 2px;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 0.35rem;
}

[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button span {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.72);
    color: #FFFFFF !important;
}

[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] button span,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button span {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    color: var(--cv-navy) !important;
}

[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] span {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    color: var(--cv-navy) !important;
}

@media (max-width: 768px) {
    .block-container {
        padding: 1.25rem 1rem 2rem;
    }

    .stHorizontalBlock {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
    }

    [data-testid="stHorizontalBlock"].stHorizontalBlock > [data-testid="stColumn"] {
        width: 100% !important;
        min-width: 100% !important;
        flex-basis: 100% !important;
    }

    .cv-card-grid {
        grid-template-columns: 1fr;
    }
}
""".strip()


def apply_theme() -> None:
    """Inject the package-owned stylesheet into the active Streamlit page."""
    st.markdown(f"<style>{APP_CSS}</style>", unsafe_allow_html=True)
