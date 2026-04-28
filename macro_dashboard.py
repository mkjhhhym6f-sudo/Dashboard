"""
Page 3 — Macro Dashboard
Key macro indicators, regime scoring, and sector impact matrix.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.macro_data import get_all_macro_data, compute_macro_regime, SECTOR_MACRO_IMPACT
from utils.charts import macro_indicator_chart, gauge_chart, COLORS


def _val(v, fmt="{:.2f}", suffix="", na="N/A"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return na
    try:
        return f"{fmt.format(v)}{suffix}"
    except Exception:
        return na


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">🌍 Macro Dashboard</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">
            Key macro indicators · Regime scoring · Sector impact matrix
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Fetching macro data (FRED + Bank of Canada)..."):
        macro = get_all_macro_data()
        regime = compute_macro_regime(macro)

    # ── Regime Banner ────────────────────────────────────────────────────
    rc = regime["color"]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {rc}22, #111827); border:1px solid {rc}44;
                border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1rem;
                display:flex; align-items:center; gap:1.5rem;">
        <div>
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">MACRO REGIME</p>
            <p style="color:{rc}; font-size:2rem; font-weight:800; margin:0;">{regime['regime'].upper()}</p>
        </div>
        <div style="flex:1;">
            <div style="background:#1e293b; border-radius:6px; height:10px; margin-bottom:0.5rem;">
                <div style="background:{rc}; width:{regime['score']}%; height:10px; border-radius:6px;"></div>
            </div>
            <p style="color:#64748b; font-size:0.8rem; margin:0;">Regime Score: {regime['score']}/100</p>
        </div>
        <div>
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">Status</p>
            <p style="color:#f8fafc; font-size:0.9rem; margin:0;">
                {'🟢 Risk-On' if regime['regime'] == 'Favorable' else
                 '🟡 Cautious' if regime['regime'] == 'Neutral' else
                 '🟠 Defensive' if regime['regime'] == 'Unfavorable' else
                 '🔴 Risk-Off'}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Macro Signal Cards ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Macro Signals</div>', unsafe_allow_html=True)

    impact_colors = {
        "positive":          "#06d6a0",
        "slightly_positive": "#a8f0d8",
        "neutral":           "#8d99ae",
        "mixed":             "#ffd60a",
        "slightly_negative": "#fca5a5",
        "negative":          "#ef233c",
        "highly_negative":   "#dc143c",
        "highly_positive":   "#00ff9f",
    }

    for sig in regime["signals"]:
        color = impact_colors.get(sig["impact"], "#8d99ae")
        icon  = "✅" if "positive" in sig["impact"] else "⚠️" if sig["impact"] == "neutral" else "🔴" if "negative" in sig["impact"] else "⚡"
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:1rem; padding:0.6rem 1rem;
                    background:#111827; border-left:3px solid {color};
                    border-radius:0 8px 8px 0; margin:0.2rem 0;">
            <span style="font-size:1.1rem;">{icon}</span>
            <div style="flex:1;">
                <span style="color:#f8fafc; font-size:0.85rem; font-weight:600;">{sig['indicator']}</span>
                <span style="color:#94a3b8; font-size:0.8rem;"> — {sig['note']}</span>
            </div>
            <span style="color:{color}; font-weight:700; font-size:0.9rem; min-width:80px; text-align:right;">
                {sig['value']}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Key Indicators Grid ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Key Indicators</div>', unsafe_allow_html=True)

    tabs = st.tabs(["🇨🇦 Canada", "🇺🇸 United States", "📈 Rates & FX", "🛢️ Commodities"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        boc = macro.get("boc_policy_rate")
        c1.metric("BoC Policy Rate", _val(boc, "{:.2f}", "%"), help="Bank of Canada overnight rate target")
        c2.metric("CA 10Y Yield", _val(macro.get("ca_10y_yield"), "{:.2f}", "%"))
        c3.metric("CA 2Y Yield",  _val(macro.get("ca_2y_yield"),  "{:.2f}", "%"))

        ca_curve = macro.get("ca_yield_curve")
        ca_curve_color = "#06d6a0" if ca_curve and ca_curve > 0 else "#ef233c"
        c1.markdown(f"<span style='color:{ca_curve_color}; font-weight:600;'>CA Yield Curve: {_val(ca_curve, '{:.2f}', '%')}</span>", unsafe_allow_html=True)

        boc_series = macro.get("boc_policy_rate_series")
        if boc_series is not None and not boc_series.empty:
            fig = macro_indicator_chart(boc_series.tail(60), "BoC Policy Rate (%)", color=COLORS["primary"], threshold=2.0)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='data-source'>Source: Bank of Canada Valet API</span>", unsafe_allow_html=True)

    with tabs[1]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fed Funds Rate", _val(macro.get("fed_funds_rate"), "{:.2f}", "%"))
        c2.metric("US CPI YoY",     _val(macro.get("us_cpi_yoy"), "{:.1f}", "%"))
        c3.metric("US Unemployment", _val(macro.get("us_unemployment"), "{:.1f}", "%"))
        c4.metric("US Consumer Conf", _val(macro.get("us_consumer_conf"), "{:.1f}"))

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("US Retail Sales", _val(macro.get("us_retail_sales"), "${:.0f}B") if macro.get("us_retail_sales") else "N/A")
        c6.metric("Housing Starts",  _val(macro.get("us_housing_starts"), "{:.0f}K") if macro.get("us_housing_starts") else "N/A")
        c7.metric("Auto Sales",      _val(macro.get("us_auto_sales"), "{:.1f}M") if macro.get("us_auto_sales") else "N/A")
        c8.metric("Wage Growth",     _val(macro.get("us_wages_growth"), "${:.2f}/hr") if macro.get("us_wages_growth") else "N/A")

        # Chart
        fed_series = macro.get("fed_funds_rate_series")
        if fed_series is not None and not fed_series.empty:
            fig = macro_indicator_chart(fed_series.tail(60), "US Federal Funds Rate (%)", color=COLORS["accent"], threshold=2.5)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='data-source'>Source: Federal Reserve (FRED)</span>", unsafe_allow_html=True)

    with tabs[2]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("US 10Y Yield",   _val(macro.get("us_10y_yield"), "{:.2f}", "%"))
        c2.metric("US 2Y Yield",    _val(macro.get("us_2y_yield"),  "{:.2f}", "%"))
        yc = macro.get("us_yield_curve")
        yc_color = "normal" if yc and yc > 0 else "inverse"
        c3.metric("US Yield Curve (10Y-2Y)", _val(yc, "{:.2f}", "%"), delta=yc_color)
        cad_usd = macro.get("cad_usd")
        cad_disp = 1 / cad_usd if cad_usd and cad_usd > 1 else cad_usd
        c4.metric("USD/CAD", _val(cad_disp, "{:.4f}"))

        cad_series = macro.get("cad_usd_series")
        if cad_series is not None and not cad_series.empty:
            # Convert to CAD/USD from USD/CAD
            cad_plot = 1 / cad_series if (cad_series > 1).mean() > 0.5 else cad_series
            fig = macro_indicator_chart(cad_plot.tail(120), "USD/CAD Exchange Rate", color=COLORS["warning"])
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='data-source'>Source: Bank of Canada Valet API / FRED</span>", unsafe_allow_html=True)

    with tabs[3]:
        c1, c2, c3 = st.columns(3)
        c1.metric("WTI Crude (USD)", _val(macro.get("wti_oil"), "${:.2f}"))
        c2.metric("Gas Prices", "N/A — Premium Data", help="Requires EIA API or manual input")
        c3.metric("Energy Impact", "See Sector Matrix ↓")

        wti_series = macro.get("wti_oil_series")
        if wti_series is not None and not wti_series.empty:
            fig = macro_indicator_chart(wti_series.tail(120), "WTI Crude Oil (USD/bbl)", color=COLORS["accent"], threshold=80)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='data-source'>Source: FRED (DCOILWTICO)</span>", unsafe_allow_html=True)

    # ── Sector Impact Matrix ─────────────────────────────────────────────
    st.markdown('<div class="section-header">Sector Impact Matrix</div>', unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>How current macro conditions affect each sector in the portfolio.</p>", unsafe_allow_html=True)

    impact_icon = {
        "highly_positive":   ("🟢🟢", "#00ff9f"),
        "positive":          ("🟢",   "#06d6a0"),
        "slightly_positive": ("🟢",   "#a8f0d8"),
        "neutral":           ("⚪",   "#8d99ae"),
        "mixed":             ("🟡",   "#ffd60a"),
        "slightly_negative": ("🔴",   "#fca5a5"),
        "negative":          ("🔴",   "#ef233c"),
        "highly_negative":   ("🔴🔴", "#dc143c"),
    }

    for sector, impacts in SECTOR_MACRO_IMPACT.items():
        note = impacts.get("note", "")
        factors = {k: v for k, v in impacts.items() if k != "note"}

        html = f"""
        <div style="background:#111827; border-radius:10px; padding:0.75rem 1rem; margin:0.4rem 0;
                    border:1px solid #1e293b;">
            <div style="display:flex; align-items:flex-start; gap:1rem; flex-wrap:wrap;">
                <div style="min-width:180px;">
                    <span style="color:#00b4d8; font-weight:700; font-size:0.9rem;">{sector.replace('_', ' ')}</span><br>
                    <span style="color:#64748b; font-size:0.75rem;">{note}</span>
                </div>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap; flex:1;">
        """
        for factor, impact in factors.items():
            icon_str, color = impact_icon.get(impact, ("⚪", "#8d99ae"))
            label = factor.replace("_", " ").title()
            html += f"""
                <span style="background:#0f172a; border:1px solid #1e293b; border-radius:6px;
                             padding:0.2rem 0.5rem; font-size:0.75rem; color:{color};">
                    {icon_str} {label}
                </span>
            """
        html += "</div></div></div>"
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(f"<span class='data-source'>Last updated: {macro.get('last_updated', 'Unknown')}</span>", unsafe_allow_html=True)
