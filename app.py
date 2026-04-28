"""
Fund Dashboard - Main Application Entry Point
Student Investment Fund - Institutional Grade Analytics Platform
"""

import streamlit as st
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Page configuration
st.set_page_config(
    page_title="Fund Dashboard | SIF Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Student Investment Fund Analytics Platform v1.0"
    }
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme */
    :root {
        --primary: #0f4c81;
        --accent: #00b4d8;
        --positive: #06d6a0;
        --negative: #ef233c;
        --warning: #ffd60a;
        --neutral: #8d99ae;
        --bg-dark: #0a0e1a;
        --bg-card: #111827;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }

    .main-header {
        background: linear-gradient(135deg, #0f4c81 0%, #1a1a2e 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(0, 180, 216, 0.2);
    }

    .metric-card {
        background: #111827;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }

    .positive { color: #06d6a0 !important; }
    .negative { color: #ef233c !important; }
    .warning  { color: #ffd60a !important; }
    .neutral  { color: #8d99ae !important; }

    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
    }

    .score-high   { background: rgba(6,214,160,0.2); color: #06d6a0; border: 1px solid #06d6a0; }
    .score-medium { background: rgba(255,214,10,0.2); color: #ffd60a; border: 1px solid #ffd60a; }
    .score-low    { background: rgba(239,35,60,0.2);  color: #ef233c; border: 1px solid #ef233c; }

    .alert-box {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    .alert-critical { background: rgba(239,35,60,0.15);  border-left: 3px solid #ef233c; }
    .alert-warning  { background: rgba(255,214,10,0.15); border-left: 3px solid #ffd60a; }
    .alert-info     { background: rgba(0,180,216,0.15);  border-left: 3px solid #00b4d8; }
    .alert-ok       { background: rgba(6,214,160,0.15);  border-left: 3px solid #06d6a0; }

    /* Sidebar styling */
    .css-1d391kg { background-color: #0d1117; }

    /* Data source tag */
    .data-source {
        font-size: 0.7rem;
        color: #64748b;
        font-style: italic;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #00b4d8;
        border-bottom: 1px solid rgba(0,180,216,0.3);
        padding-bottom: 0.5rem;
        margin: 1rem 0 0.75rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Navigation
def main():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0;">
            <h2 style="color:#00b4d8; margin:0; font-size:1.4rem;">📊 SIF Analytics</h2>
            <p style="color:#64748b; font-size:0.75rem; margin:0.25rem 0 0 0;">Student Investment Fund</p>
        </div>
        <hr style="border-color:rgba(255,255,255,0.1); margin:0.5rem 0 1rem 0;">
        """, unsafe_allow_html=True)

        page = st.selectbox(
            "Navigation",
            options=[
                "🏠 Fund Overview",
                "📂 Sector Overview",
                "🌍 Macro Dashboard",
                "🔍 Company Deep Dive",
                "⚖️ Peer Comparison",
                "💰 Valuation Center",
                "⚠️ Risk Monitor",
                "👤 Analyst Center",
                "🔧 Data Quality",
            ],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("<p style='color:#64748b; font-size:0.75rem;'>Data sources: yfinance · FRED · Banque du Canada · Manual</p>", unsafe_allow_html=True)

        # Cache management
        with st.expander("⚙️ Settings"):
            st.button("🔄 Refresh All Data", help="Clears cache and re-fetches all data")
            st.button("📥 Export to CSV", help="Export current view to CSV")
            st.checkbox("Show Data Sources", value=True, key="show_sources")
            st.checkbox("CAD Display", value=True, key="display_cad")

    # Route to pages
    if page == "🏠 Fund Overview":
        from pages.fund_overview import render
        render()
    elif page == "📂 Sector Overview":
        from pages.sector_overview import render
        render()
    elif page == "🌍 Macro Dashboard":
        from pages.macro_dashboard import render
        render()
    elif page == "🔍 Company Deep Dive":
        from pages.company_deep_dive import render
        render()
    elif page == "⚖️ Peer Comparison":
        from pages.peer_comparison import render
        render()
    elif page == "💰 Valuation Center":
        from pages.valuation_center import render
        render()
    elif page == "⚠️ Risk Monitor":
        from pages.risk_monitor import render
        render()
    elif page == "👤 Analyst Center":
        from pages.analyst_center import render
        render()
    elif page == "🔧 Data Quality":
        from pages.data_quality import render
        render()


if __name__ == "__main__":
    main()
