"""
app.py — FIEUS Analytics Dashboard
Fonds d'investissement étudiant de l'Université de Sherbrooke

Main Streamlit entry point. All page modules are at the root level (flat).

Run locally:  streamlit run app.py
Deploy:       Streamlit Cloud — Main file path = app.py
"""

import streamlit as st
from datetime import datetime

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="FIEUS Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",   # sidebar always open on load
)

# ── Minimal CSS — does NOT hide header or the sidebar toggle button ───────────
from theme import (UDES_GREEN_DARK, UDES_GREEN, UDES_GOLD, UDES_GOLD_LIGHT,
                    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG_DARK)

# We inject a reduced CSS that:
#   - keeps the sidebar collapse/expand arrow visible
#   - hides Streamlit's top-right hamburger menu and footer (cosmetic)
#   - does NOT hide 'header' (which in newer Streamlit contains the collapse btn)
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Merriweather:wght@400;700;900&display=swap');

.stApp {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

/* Hide Streamlit footer and the top-right deploy/menu button — NOT header */
footer {{ visibility: hidden; }}
#MainMenu {{ visibility: hidden; }}

/* Sidebar background */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {UDES_GREEN_DARK} 0%, #003D2D 100%);
}}
section[data-testid="stSidebar"] * {{ color: {TEXT_PRIMARY} !important; }}
</style>
""", unsafe_allow_html=True)

# ── Then apply the full theme CSS (which may hide header — we override below) ──
from theme import GLOBAL_CSS
# Inject GLOBAL_CSS but patch out the header-hiding rule on the fly
# theme.py's GLOBAL_CSS hides 'header' which in newer Streamlit versions
# includes the sidebar collapse/expand button. We patch it out before injecting.
# GLOBAL_CSS is already an evaluated f-string (single braces in output).
_safe_css = GLOBAL_CSS.replace(
    "#MainMenu, footer, header {visibility: hidden;}",
    "footer {visibility: hidden;} #MainMenu {visibility: hidden;}",
)
st.markdown(_safe_css, unsafe_allow_html=True)

# ── Page modules (flat — no "pages." prefix) ──────────────────────────────────
import fund_overview
import sector_overview
import macro_dashboard
import company_deep_dive
import peer_comparison
import valuation_center
import risk_monitor
import analyst_center
import data_quality

# ── Page registry ─────────────────────────────────────────────────────────────
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

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Brand block
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{UDES_GREEN_DARK} 0%,{UDES_GREEN} 100%);
                border-radius:10px;padding:18px;margin-bottom:18px;
                border-left:4px solid {UDES_GOLD}">
        <div style="color:{UDES_GOLD};font-size:10px;font-weight:700;
                    letter-spacing:2px;text-transform:uppercase;">
            FIEUS
        </div>
        <div style="color:{TEXT_PRIMARY};font-size:16px;font-weight:800;
                    font-family:Merriweather,Georgia,serif;margin-top:3px;line-height:1.3;">
            Analytics Dashboard
        </div>
        <div style="color:{UDES_GOLD_LIGHT};font-size:9.5px;letter-spacing:0.3px;
                    margin-top:5px;line-height:1.4;opacity:0.9;">
            Fonds d'investissement étudiant<br>
            de l'Université de Sherbrooke
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    st.markdown(
        f'<div style="color:{TEXT_MUTED};font-size:10px;font-weight:700;'
        f'letter-spacing:1.5px;margin:8px 0 6px 0">NAVIGATION</div>',
        unsafe_allow_html=True,
    )

    page_name = st.radio(
        "Navigation",
        options=list(PAGES.keys()),
        format_func=lambda k: f"{PAGES[k][0]}  {k}",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown(
        f'<div style="color:{TEXT_MUTED};font-size:10px;font-weight:700;'
        f'letter-spacing:1.5px;margin:8px 0 6px 0">SESSION</div>',
        unsafe_allow_html=True,
    )

    if st.button("🔄 Clear Cache & Reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Footer
    st.markdown(f"""
    <div style="margin-top:40px;color:{TEXT_MUTED};font-size:10px;line-height:1.7">
        <div>Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        <div style="margin-top:2px">Data: yfinance · FRED · BoC Valet</div>
        <div style="margin-top:6px;color:{TEXT_MUTED};font-size:9px;
                    font-style:italic;line-height:1.5;opacity:0.8;">
            Internal analytical tool — not investment advice.<br>
            Scores are screening signals only.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# RENDER PAGE
# ════════════════════════════════════════════════════════════════════════════════
try:
    _, module = PAGES[page_name]
    module.render()
except Exception as e:
    st.error(f"⚠️ Error rendering page '{page_name}'")
    st.exception(e)
    st.info(
        "Try clicking '🔄 Clear Cache & Reload' in the sidebar. "
        "If the issue persists, check your internet connection or contact the FIEUS tech team."
    )
