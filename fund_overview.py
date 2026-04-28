"""
Page 1 — Fund Overview
Portfolio-level performance, attribution, heatmap, alerts, ranking.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import fetch_fundamentals, fetch_price_history, calculate_returns, calculate_risk_metrics
from analytics.scoring import compute_composite_score, get_score_color, get_score_badge_class
from utils.charts import sector_allocation_pie, heatmap, returns_bar, SECTOR_COLORS, COLORS, _apply_theme

UNIVERSE_CSV = Path(__file__).parent.parent.parent / "config" / "universe.csv"
ANALYST_CSV  = Path(__file__).parent.parent.parent / "config" / "analyst_coverage.csv"


@st.cache_data(ttl=3600)
def load_universe_data():
    universe = pd.read_csv(UNIVERSE_CSV)
    return universe


def _millions(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if abs(val) >= 1e12:
        return f"${val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">🏠 Fund Overview</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">Portfolio-level performance, attribution, sector weights, and alerts</p>
    </div>
    """, unsafe_allow_html=True)

    universe = load_universe_data()
    companies = universe[universe["is_etf"] == False].copy()

    # Portfolio weights input
    with st.expander("⚙️ Portfolio Weights (enter % per position — 0 = equal weight)", expanded=False):
        st.info("Enter position weights below. If all are 0, equal weighting is applied.")
        weights_input = {}
        cols = st.columns(4)
        for i, (_, row) in enumerate(companies.iterrows()):
            with cols[i % 4]:
                w = st.number_input(
                    f"{row['ticker']}",
                    min_value=0.0, max_value=100.0, value=0.0, step=0.5,
                    key=f"w_{row['ticker']}"
                )
                weights_input[row["ticker"]] = w

    total_w = sum(weights_input.values())
    if total_w == 0:
        n = len(companies)
        portfolio_weights = {t: 1/n for t in companies["ticker"]}
    else:
        portfolio_weights = {t: w/total_w for t, w in weights_input.items()}

    # Fetch data
    with st.spinner("Loading portfolio data (cached)..."):
        rows = []
        for _, meta_row in companies.iterrows():
            ticker = meta_row["ticker"]
            fd = fetch_fundamentals(ticker)
            prices_df = fetch_price_history(ticker, period="1y")
            prices = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
            rets = calculate_returns(prices) if not prices.empty else {}
            risk_m = calculate_risk_metrics(prices) if not prices.empty else {}

            score_r = compute_composite_score(fd, rets, meta_row.get("sector", "Default"), "Neutral", meta_row.get("is_etf", False))

            rows.append({
                "Ticker":    ticker,
                "Name":      fd.get("name") or meta_row.get("name", ticker),
                "Sector":    meta_row.get("sector", "N/A"),
                "Weight":    portfolio_weights.get(ticker, 0),
                "Price":     fd.get("price"),
                "Mkt Cap":   fd.get("market_cap"),
                "1D Ret":    rets.get("1d"),
                "1M Ret":    rets.get("1m"),
                "3M Ret":    rets.get("3m"),
                "6M Ret":    rets.get("6m"),
                "YTD Ret":   rets.get("ytd"),
                "1Y Ret":    rets.get("1y"),
                "Beta":      fd.get("beta") or risk_m.get("beta_calc"),
                "Volatility":risk_m.get("volatility_ann"),
                "Drawdown":  risk_m.get("current_drawdown_from_52w"),
                "EV/EBITDA": fd.get("ev_ebitda"),
                "P/E":       fd.get("pe_trailing") or fd.get("pe_forward"),
                "Div Yield": fd.get("dividend_yield"),
                "Score":     score_r.get("total"),
                "Rec":       score_r.get("recommendation", "N/A"),
            })

    df = pd.DataFrame(rows)

    # ──────────────────────────────────────────────
    # Portfolio KPIs
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Portfolio Summary</div>', unsafe_allow_html=True)

    def weighted_ret(col):
        valid = df[df[col].notna()]
        if valid.empty: return None
        return (valid[col] * valid["Weight"]).sum() / valid["Weight"].sum()

    port_1d  = weighted_ret("1D Ret")
    port_1m  = weighted_ret("1M Ret")
    port_ytd = weighted_ret("YTD Ret")
    port_1y  = weighted_ret("1Y Ret")

    def _fc(v, is_return=True):
        if v is None: return "N/A", "#8d99ae"
        pct = v * 100
        color = "#06d6a0" if pct >= 0 else "#ef233c"
        return f"{pct:+.2f}%", color

    c1, c2, c3, c4, c5 = st.columns(5)
    cols_kpi = [
        (c1, "1-Day Return",  _fc(port_1d)),
        (c2, "1-Month Return",_fc(port_1m)),
        (c3, "YTD Return",    _fc(port_ytd)),
        (c4, "1-Year Return", _fc(port_1y)),
        (c5, "# Positions",   (str(len(df)), "#00b4d8")),
    ]
    for col, label, (val, color) in cols_kpi:
        col.markdown(f"""
        <div class="metric-card">
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">{label}</p>
            <p style="font-size:1.5rem; font-weight:700; color:{color}; margin:0.25rem 0;">{val}</p>
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # Sector breakdown
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Sector Allocation & Performance</div>', unsafe_allow_html=True)

    sector_grp = df.groupby("Sector").agg(
        Weight=("Weight", "sum"),
        Avg1D=("1D Ret", "mean"),
        Avg1M=("1M Ret", "mean"),
        AvgYTD=("YTD Ret", "mean"),
        AvgScore=("Score", "mean"),
        Count=("Ticker", "count"),
    ).reset_index()

    c1, c2 = st.columns([1, 2])
    with c1:
        sector_wts = dict(zip(sector_grp["Sector"], sector_grp["Weight"] * 100))
        fig_pie = sector_allocation_pie(sector_wts)
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        fig_sector_perf = go.Figure()
        for _, row in sector_grp.iterrows():
            ytd = (row["AvgYTD"] or 0) * 100
            color = SECTOR_COLORS.get(row["Sector"], COLORS["neutral"])
            fig_sector_perf.add_trace(go.Bar(
                name=row["Sector"], x=[row["Sector"]], y=[ytd],
                marker_color=color,
                text=[f"{ytd:+.1f}%"], textposition="outside",
            ))
        fig_sector_perf.add_hline(y=0, line_color="#334155")
        _apply_theme(fig_sector_perf, "Sector YTD Performance (%)")
        fig_sector_perf.update_layout(showlegend=False, height=280)
        st.plotly_chart(fig_sector_perf, use_container_width=True)

    # ──────────────────────────────────────────────
    # Heatmap — returns by ticker
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Performance Heatmap</div>', unsafe_allow_html=True)

    hm_cols = ["1D Ret", "1M Ret", "3M Ret", "6M Ret", "YTD Ret", "1Y Ret"]
    hm_df = df[["Ticker"] + hm_cols].set_index("Ticker")
    hm_pct = hm_df.applymap(lambda v: v * 100 if v is not None else np.nan)
    fig_hm = heatmap(hm_pct, "Return Heatmap — All Positions (%)", fmt="+.1f", zmin=-30, zmax=30)
    st.plotly_chart(fig_hm, use_container_width=True)
    st.markdown("<span class='data-source'>Source: yfinance price history</span>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # Rankings
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Global Ranking</div>', unsafe_allow_html=True)

    df_sorted = df.sort_values("Score", ascending=False).reset_index(drop=True)

    tab1, tab2, tab3 = st.tabs(["🏆 All Holdings", "📈 Top Performers", "📉 Worst Performers"])

    def _colored_ret(v):
        if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
        pct = v * 100
        color = "#06d6a0" if pct >= 0 else "#ef233c"
        return f'<span style="color:{color};">{pct:+.1f}%</span>'

    def _colored_score(v):
        if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
        color = get_score_color(v)
        return f'<span style="color:{color}; font-weight:700;">{v:.0f}</span>'

    def render_table(dataframe):
        html = '<table style="width:100%; border-collapse:collapse; font-size:0.82rem;">'
        html += '<tr style="border-bottom:1px solid #1e293b; color:#64748b;">'
        for col in ["#", "Ticker", "Name", "Sector", "Weight", "1D", "1M", "YTD", "1Y", "Score", "Rec"]:
            html += f'<th style="text-align:left; padding:0.4rem 0.5rem;">{col}</th>'
        html += '</tr>'
        for i, row in dataframe.iterrows():
            rec_c = {"BUY": "#06d6a0", "HOLD": "#ffd60a", "WATCHLIST": "#f77f00", "SELL": "#ef233c"}.get(row.get("Rec", ""), "#8d99ae")
            html += f'''<tr style="border-bottom:1px solid #0f172a; color:#cbd5e1;">
                <td style="padding:0.35rem 0.5rem; color:#64748b;">{i+1}</td>
                <td style="padding:0.35rem 0.5rem; color:#00b4d8; font-weight:600;">{row["Ticker"]}</td>
                <td style="padding:0.35rem 0.5rem;">{str(row["Name"])[:20]}</td>
                <td style="padding:0.35rem 0.5rem; color:#8d99ae; font-size:0.75rem;">{row["Sector"]}</td>
                <td style="padding:0.35rem 0.5rem;">{row["Weight"]*100:.1f}%</td>
                <td style="padding:0.35rem 0.5rem;">{_colored_ret(row["1D Ret"])}</td>
                <td style="padding:0.35rem 0.5rem;">{_colored_ret(row["1M Ret"])}</td>
                <td style="padding:0.35rem 0.5rem;">{_colored_ret(row["YTD Ret"])}</td>
                <td style="padding:0.35rem 0.5rem;">{_colored_ret(row["1Y Ret"])}</td>
                <td style="padding:0.35rem 0.5rem;">{_colored_score(row["Score"])}</td>
                <td style="padding:0.35rem 0.5rem;"><span style="color:{rec_c}; font-weight:600; font-size:0.75rem;">{row.get("Rec", "N/A")}</span></td>
            </tr>'''
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)

    with tab1:
        render_table(df_sorted)
    with tab2:
        top = df.sort_values("YTD Ret", ascending=False).head(10).reset_index(drop=True)
        render_table(top)
    with tab3:
        bottom = df.sort_values("YTD Ret", ascending=True).head(10).reset_index(drop=True)
        render_table(bottom)

    # ──────────────────────────────────────────────
    # Alerts
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-header">🚨 Automated Alerts</div>', unsafe_allow_html=True)

    alerts = []
    for _, row in df.iterrows():
        dd = row.get("Drawdown")
        if dd and dd < -0.20:
            alerts.append(("critical", f"⚠️ {row['Ticker']} — Drawdown {dd*100:.1f}% from 52W high"))
        ev_e = row.get("EV/EBITDA")
        if ev_e and ev_e > 30:
            alerts.append(("warning", f"💰 {row['Ticker']} — Elevated EV/EBITDA: {ev_e:.1f}x"))
        score = row.get("Score")
        if score and score < 35:
            alerts.append(("critical", f"🔴 {row['Ticker']} — Low composite score: {score:.0f}/100"))
        ytd = row.get("YTD Ret")
        if ytd and ytd < -0.20:
            alerts.append(("warning", f"📉 {row['Ticker']} — YTD return: {ytd*100:.1f}%"))

    if alerts:
        col_a1, col_a2 = st.columns(2)
        for i, (level, msg) in enumerate(alerts):
            css = "alert-critical" if level == "critical" else "alert-warning"
            with col_a1 if i % 2 == 0 else col_a2:
                st.markdown(f'<div class="alert-box {css}">{msg}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-box alert-ok">✅ No critical alerts detected across portfolio</div>', unsafe_allow_html=True)

    # Export
    if st.button("📥 Export Portfolio Summary to CSV"):
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "portfolio_summary.csv", "text/csv")
