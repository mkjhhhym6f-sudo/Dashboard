"""
Page 2 — Sector Overview
Dynamic sector analysis with peer comparison within the sector.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import fetch_fundamentals, fetch_price_history, calculate_returns, calculate_risk_metrics
from analytics.scoring import compute_composite_score, get_score_color
from utils.charts import heatmap, sector_allocation_pie, SECTOR_COLORS, COLORS, _apply_theme
import plotly.graph_objects as go

UNIVERSE_CSV = Path(__file__).parent.parent.parent / "config" / "universe.csv"
SECTOR_CFG   = Path(__file__).parent.parent.parent / "config" / "sector_config.yaml"


def _pct_raw(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
    return f"{v*100:.1f}%"


def _fmt(v, fmt="{:.1f}", sfx=""):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
    try: return f"{fmt.format(v)}{sfx}"
    except: return "N/A"


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">📂 Sector Overview</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">
            Deep dive into a specific sector — performance, fundamentals, and ranking
        </p>
    </div>
    """, unsafe_allow_html=True)

    universe = pd.read_csv(UNIVERSE_CSV)
    companies = universe[universe["is_etf"] == False]
    sectors = sorted(companies["sector"].unique().tolist())

    selected_sector = st.selectbox("Select Sector", options=sectors)
    sector_tickers  = companies[companies["sector"] == selected_sector]["ticker"].tolist()

    if not sector_tickers:
        st.warning("No tickers found for this sector.")
        return

    st.markdown(f"**{len(sector_tickers)} companies covered** in {selected_sector}")

    with st.spinner("Loading sector data..."):
        rows = []
        for ticker in sector_tickers:
            fd = fetch_fundamentals(ticker)
            prices_df = fetch_price_history(ticker, period="1y")
            prices    = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
            rets      = calculate_returns(prices) if not prices.empty else {}
            risk_m    = calculate_risk_metrics(prices) if not prices.empty else {}
            score_r   = compute_composite_score(fd, rets, selected_sector, "Neutral", False)
            meta      = universe[universe["ticker"] == ticker].iloc[0].to_dict()

            net_d = fd.get("net_debt", 0) or 0
            ebit  = fd.get("ebitda", 1) or 1

            rows.append({
                "Ticker":    ticker,
                "Name":      fd.get("name") or meta.get("name", ticker),
                "1D":        rets.get("1d"),
                "1M":        rets.get("1m"),
                "3M":        rets.get("3m"),
                "YTD":       rets.get("ytd"),
                "1Y":        rets.get("1y"),
                "Mkt Cap":   fd.get("market_cap"),
                "Rev Growth":fd.get("revenue_growth_yoy"),
                "EBITDA Mgn":fd.get("ebitda_margin"),
                "Op Margin": fd.get("operating_margin"),
                "Gross Mgn": fd.get("gross_margin"),
                "ROIC/ROE":  fd.get("roic") or fd.get("roe"),
                "EV/EBITDA": fd.get("ev_ebitda"),
                "P/E":       fd.get("pe_trailing") or fd.get("pe_forward"),
                "FCF Yield": (fd.get("fcf") / fd.get("market_cap")) * 100 if fd.get("fcf") and fd.get("market_cap") else None,
                "ND/EBITDA": net_d / ebit if ebit and ebit != 1 else None,
                "Div Yield": fd.get("dividend_yield"),
                "Beta":      fd.get("beta") or risk_m.get("beta_calc"),
                "Volatility":risk_m.get("volatility_ann"),
                "Score":     score_r.get("total"),
                "Rec":       score_r.get("recommendation", "N/A"),
            })

    df = pd.DataFrame(rows)

    # ── Sector KPIs ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Sector Averages</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    avg = lambda col: df[col].mean() if df[col].notna().any() else None

    c1.metric("Avg Score",      f"{avg('Score'):.0f}/100" if avg("Score") else "N/A")
    c2.metric("Avg Rev Growth", _pct_raw(avg("Rev Growth")))
    c3.metric("Avg EBITDA Mgn", _pct_raw(avg("EBITDA Mgn")))
    c4.metric("Avg EV/EBITDA",  _fmt(avg("EV/EBITDA"), "{:.1f}", "x"))
    c5.metric("Avg ND/EBITDA",  _fmt(avg("ND/EBITDA"), "{:.1f}", "x"))
    c6.metric("Avg YTD Ret",    _pct_raw(avg("YTD")))

    # ── Performance heatmap ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Performance Comparison</div>', unsafe_allow_html=True)
    hm_cols = ["1D", "1M", "3M", "YTD", "1Y"]
    hm_df   = df[["Ticker"] + hm_cols].set_index("Ticker")
    hm_pct  = hm_df.applymap(lambda v: v * 100 if v is not None else np.nan)
    fig_hm  = heatmap(hm_pct, f"{selected_sector} — Return Heatmap (%)", fmt="+.1f", zmin=-25, zmax=25)
    st.plotly_chart(fig_hm, use_container_width=True)

    # ── Fundamentals table ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Fundamentals Snapshot</div>', unsafe_allow_html=True)

    display_cols = ["Ticker", "Name", "Rev Growth", "EBITDA Mgn", "ROIC/ROE", "EV/EBITDA", "P/E", "FCF Yield", "ND/EBITDA", "Score", "Rec"]
    df_disp = df[display_cols].copy()

    for col in ["Rev Growth", "EBITDA Mgn", "ROIC/ROE"]:
        df_disp[col] = df_disp[col].apply(_pct_raw)
    for col in ["EV/EBITDA", "P/E", "ND/EBITDA"]:
        df_disp[col] = df_disp[col].apply(lambda v: _fmt(v, "{:.1f}", "x"))
    df_disp["FCF Yield"] = df_disp["FCF Yield"].apply(lambda v: _fmt(v, "{:.1f}", "%"))
    df_disp["Score"]     = df_disp["Score"].apply(lambda v: f"{v:.0f}" if v and not np.isnan(v) else "N/A")

    st.dataframe(df_disp, use_container_width=True, hide_index=True)

    # ── Top / Bottom performers ──────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🏆 Top Performers (YTD)**")
        top = df.sort_values("YTD", ascending=False).head(5)
        for _, row in top.iterrows():
            v = row["YTD"]
            color = "#06d6a0" if v and v > 0 else "#ef233c"
            pct   = f"{v*100:+.1f}%" if v else "N/A"
            st.markdown(f"<div style='display:flex; justify-content:space-between; padding:0.25rem 0;'><span style='color:#cbd5e1;'>{row['Ticker']}</span><span style='color:{color}; font-weight:600;'>{pct}</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("**📉 Worst Performers (YTD)**")
        bot = df.sort_values("YTD", ascending=True).head(5)
        for _, row in bot.iterrows():
            v = row["YTD"]
            color = "#06d6a0" if v and v > 0 else "#ef233c"
            pct   = f"{v*100:+.1f}%" if v else "N/A"
            st.markdown(f"<div style='display:flex; justify-content:space-between; padding:0.25rem 0;'><span style='color:#cbd5e1;'>{row['Ticker']}</span><span style='color:{color}; font-weight:600;'>{pct}</span></div>", unsafe_allow_html=True)
