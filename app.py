"""
app.py — SIF Analytics: Université de Sherbrooke Student Investment Fund
Vert & Or — Main Streamlit entry point.

All page modules are at the root level (flat structure) — no subfolders.
Run locally:    streamlit run app.py
Deploy:         Streamlit Cloud, Main file path = app.py
"""

import streamlit as st
from datetime import datetime

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="SIF Analytics · Vert & Or",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme + CSS ─────────────────────────────────────────────────────────────
from theme import (GLOBAL_CSS, UDES_GREEN_DARK, UDES_GREEN, UDES_GOLD,
                    UDES_GOLD_LIGHT, TEXT_PRIMARY, TEXT_MUTED)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Page modules (flat — same dir as app.py, no "pages." prefix) ───────────
import fund_overview
import sector_overview
import macro_dashboard
import company_deep_dive
import peer_comparison
import valuation_center
import risk_monitor
import analyst_center
import data_quality

# ── Page registry ──────────────────────────────────────────────────────────
PAGES = {
    "Fund Overview":     ("🏠", fund_overview),
    "Sector Overview":   ("📂", sector_overview),
    "Macro Dashboard":   ("🌍", macro_dashboard),
    "Company Deep Dive": ("🔍", company_deep_dive),
    "Peer Comparison":   ("⚖️", peer_comparison),
    "Valuation Center":  ("💰", valuation_center),
    "Risk Monitor":      ("⚠️", risk_monitor),
    "Analyst Center":    ("👤", analyst_center),
    "Data Quality":      ("🔧", data_quality),
}

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{UDES_GREEN_DARK} 0%,{UDES_GREEN} 100%);
                border-radius:10px;padding:18px 18px;margin-bottom:18px;
                border-left:4px solid {UDES_GOLD}">
        <div style="color:{UDES_GOLD};font-size:11px;font-weight:700;letter-spacing:1.5px">SIF ANALYTICS</div>
        <div style="color:{TEXT_PRIMARY};font-size:18px;font-weight:800;font-family:Merriweather,Georgia,serif;margin-top:2px">
            Vert &amp; Or
        </div>
        <div style="color:{UDES_GOLD_LIGHT};font-size:10px;letter-spacing:0.5px;margin-top:4px">
            Université de Sherbrooke
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div style="color:{TEXT_MUTED};font-size:10px;font-weight:700;'
                 f'letter-spacing:1.5px;margin:8px 0 6px 0">NAVIGATION</div>',
                 unsafe_allow_html=True)

    page_name = st.radio(
        "Navigation",
        options=list(PAGES.keys()),
        format_func=lambda k: f"{PAGES[k][0]}  {k}",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f'<div style="color:{TEXT_MUTED};font-size:10px;font-weight:700;'
                 f'letter-spacing:1.5px;margin:8px 0 6px 0">SESSION</div>',
                 unsafe_allow_html=True)

    if st.button("🔄 Clear Cache & Reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Footer
    st.markdown(f"""
    <div style="margin-top:60px;color:{TEXT_MUTED};font-size:10px;line-height:1.6">
        <div>Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        <div style="margin-top:4px">Data: yfinance · FRED · BoC Valet</div>
        <div style="margin-top:6px;color:{TEXT_MUTED};font-size:9px;font-style:italic">
            Educational tool — not investment advice
        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# RENDER PAGE
# ════════════════════════════════════════════════════════════════════════════

try:
    _, module = PAGES[page_name]
    module.render()
except Exception as e:
    st.error(f"⚠️ Error rendering page '{page_name}'")
    st.exception(e)
    st.info("Try clicking '🔄 Clear Cache & Reload' in the sidebar. "
             "If the issue persists, check your internet connection.")
