"""
Page 7 — Risk Monitor
Automated alerts across the entire portfolio with severity levels.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import fetch_fundamentals, fetch_price_history, calculate_returns, calculate_risk_metrics
from analytics.scoring import SECTOR_BENCHMARKS

UNIVERSE_CSV = Path(__file__).parent.parent.parent / "config" / "universe.csv"


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">⚠️ Risk Monitor</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">
            Real-time alerts — valuation, leverage, momentum, macro, and drawdown signals
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Thresholds
    with st.expander("⚙️ Alert Thresholds", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            dd_thresh    = st.slider("Drawdown Alert (%)",       -50, -5, -20) / 100
            ev_ebitda_th = st.slider("EV/EBITDA Alert (x)",       10, 60, 30)
        with c2:
            nd_ebitda_th = st.slider("ND/EBITDA Alert (x)",       2.0, 10.0, 5.0)
            score_th     = st.slider("Score Alert (below)",        0, 60, 40)
        with c3:
            ytd_th       = st.slider("YTD Return Alert (%)",      -50, -5, -20) / 100
            vol_th       = st.slider("Volatility Alert (%)",      10, 80, 40) / 100

    universe = pd.read_csv(UNIVERSE_CSV)
    companies = universe[universe["is_etf"] == False]

    with st.spinner("Running risk scan..."):
        all_alerts = []
        summary_rows = []
        for _, meta in companies.iterrows():
            ticker = meta["ticker"]
            sector = meta.get("sector", "Default")
            bench  = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])
            fd = fetch_fundamentals(ticker)
            prices_df = fetch_price_history(ticker, period="1y")
            prices    = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
            rets      = calculate_returns(prices) if not prices.empty else {}
            risk_m    = calculate_risk_metrics(prices) if not prices.empty else {}

            ticker_alerts = []

            # Drawdown
            dd = risk_m.get("current_drawdown_from_52w")
            if dd and dd < dd_thresh:
                ticker_alerts.append(("🔴 CRITICAL", f"Drawdown {dd*100:.1f}% from 52W high", "alert-critical"))

            # YTD
            ytd = rets.get("ytd")
            if ytd and ytd < ytd_th:
                ticker_alerts.append(("🟠 WARNING", f"YTD return {ytd*100:.1f}%", "alert-warning"))

            # EV/EBITDA
            ev_e = fd.get("ev_ebitda")
            if ev_e and ev_e > ev_ebitda_th:
                ticker_alerts.append(("🟡 VALUATION", f"EV/EBITDA elevated at {ev_e:.1f}x (threshold: {ev_ebitda_th}x)", "alert-warning"))

            # ND/EBITDA
            net_d  = fd.get("net_debt", 0) or 0
            ebitda = fd.get("ebitda") or 1
            nd_ev  = net_d / ebitda if ebitda and ebitda > 0 else None
            if nd_ev and nd_ev > nd_ebitda_th:
                ticker_alerts.append(("🔴 LEVERAGE", f"ND/EBITDA high at {nd_ev:.1f}x (threshold: {nd_ebitda_th}x)", "alert-critical"))

            # Volatility
            vol = risk_m.get("volatility_ann")
            if vol and vol > vol_th:
                ticker_alerts.append(("🟡 VOLATILITY", f"Annualized volatility {vol*100:.1f}% (threshold: {vol_th*100:.0f}%)", "alert-warning"))

            # Negative margin
            op_m = fd.get("operating_margin")
            if op_m and op_m < 0:
                ticker_alerts.append(("🟠 MARGIN", f"Negative operating margin ({op_m*100:.1f}%)", "alert-warning"))

            # Low FCF conversion
            fcf = fd.get("fcf")
            ni  = fd.get("net_income_ttm")
            if fcf and ni and ni > 0:
                conv = fcf / ni
                if conv < 0.5:
                    ticker_alerts.append(("🟡 CASH FLOW", f"Low FCF conversion ({conv:.2f}x)", "alert-warning"))

            summary_rows.append({
                "Ticker":    ticker,
                "Sector":    sector,
                "# Alerts":  len(ticker_alerts),
                "Drawdown":  dd,
                "YTD":       ytd,
                "Volatility":vol,
                "ND/EBITDA": nd_ev,
                "EV/EBITDA": ev_e,
            })

            for severity, msg, css in ticker_alerts:
                all_alerts.append({
                    "Ticker":   ticker,
                    "Sector":   sector,
                    "Severity": severity,
                    "Alert":    msg,
                    "CSS":      css,
                })

    # ── Summary ────────────────────────────────────────────────────────
    n_critical = sum(1 for a in all_alerts if "CRITICAL" in a["Severity"])
    n_warning  = sum(1 for a in all_alerts if "WARNING"  in a["Severity"] or "VALUATION" in a["Severity"] or "CASH FLOW" in a["Severity"] or "VOLATILITY" in a["Severity"])
    n_clean    = len(companies) - len({a["Ticker"] for a in all_alerts})

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><p style="color:#94a3b8;font-size:0.75rem;">Critical Alerts</p><p style="font-size:2rem;font-weight:700;color:#ef233c;">{n_critical}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><p style="color:#94a3b8;font-size:0.75rem;">Warnings</p><p style="font-size:2rem;font-weight:700;color:#ffd60a;">{n_warning}</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><p style="color:#94a3b8;font-size:0.75rem;">Clean Positions</p><p style="font-size:2rem;font-weight:700;color:#06d6a0;">{n_clean}</p></div>', unsafe_allow_html=True)

    # ── Alert Feed ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Alert Feed</div>', unsafe_allow_html=True)

    filter_sector = st.multiselect("Filter by Sector", options=universe["sector"].unique().tolist())
    filter_sev    = st.multiselect("Filter by Severity", options=["🔴 CRITICAL", "🔴 LEVERAGE", "🟠 WARNING", "🟠 MARGIN", "🟡 VALUATION", "🟡 VOLATILITY", "🟡 CASH FLOW"])

    filtered = [a for a in all_alerts
                if (not filter_sector or a["Sector"] in filter_sector)
                and (not filter_sev or a["Severity"] in filter_sev)]

    if not filtered:
        st.markdown('<div class="alert-box alert-ok">✅ No alerts match the current filters</div>', unsafe_allow_html=True)
    else:
        for a in filtered:
            st.markdown(f"""
            <div class="alert-box {a['CSS']}">
                <span style="color:#94a3b8; font-size:0.75rem;">{a['Ticker']} · {a['Sector']}</span>
                <span style="color:#64748b;"> — </span>
                <strong>{a['Severity']}</strong>: {a['Alert']}
            </div>
            """, unsafe_allow_html=True)

    # ── Risk Table ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Risk Summary Table</div>', unsafe_allow_html=True)
    sum_df = pd.DataFrame(summary_rows).sort_values("# Alerts", ascending=False)
    st.dataframe(sum_df, use_container_width=True, hide_index=True)
