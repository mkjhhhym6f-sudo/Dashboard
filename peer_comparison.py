"""
Page 5 — Peer Comparison
Side-by-side multi-company analysis with composite rankings.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import fetch_fundamentals, fetch_price_history, calculate_returns, calculate_risk_metrics
from analytics.scoring import compute_composite_score, get_score_color, score_quality, score_valuation, score_growth, score_balance_sheet, score_momentum
from utils.charts import heatmap, scatter_bubble, COLORS

UNIVERSE_CSV = Path(__file__).parent.parent.parent / "config" / "universe.csv"


def _fmt(v, fmt="{:.1f}", sfx="", na="N/A"):
    if v is None or (isinstance(v, float) and np.isnan(v)): return na
    try: return f"{fmt.format(v)}{sfx}"
    except: return na


def _pct_raw(v): return _fmt(v, "{:.1f}", "%") if v is None else _fmt(v * 100, "{:.1f}", "%")


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">⚖️ Peer Comparison</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">
            Side-by-side comparison of selected securities across all dimensions
        </p>
    </div>
    """, unsafe_allow_html=True)

    universe = pd.read_csv(UNIVERSE_CSV)
    companies = universe[universe["is_etf"] == False]
    all_tickers = companies["ticker"].tolist()
    name_map = {r["ticker"]: f"{r['ticker']} — {r['name']}" for _, r in companies.iterrows()}

    selected = st.multiselect(
        "Select companies to compare (2-8 recommended)",
        options=all_tickers,
        format_func=lambda x: name_map.get(x, x),
        default=all_tickers[:5],
    )

    if len(selected) < 2:
        st.info("Select at least 2 companies to compare.")
        return

    with st.spinner("Loading comparison data..."):
        rows = []
        for ticker in selected:
            fd = fetch_fundamentals(ticker)
            prices_df = fetch_price_history(ticker, period="1y")
            prices    = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
            rets      = calculate_returns(prices) if not prices.empty else {}
            risk_m    = calculate_risk_metrics(prices) if not prices.empty else {}
            meta      = companies[companies["ticker"] == ticker].iloc[0].to_dict()
            sector    = meta.get("sector", "Default")

            q_s  = score_quality(fd, sector)["score"]
            v_s  = score_valuation(fd, sector)["score"]
            g_s  = score_growth(fd)["score"]
            b_s  = score_balance_sheet(fd, sector)["score"]
            m_s  = score_momentum(rets)["score"]
            comp = compute_composite_score(fd, rets, sector, "Neutral", False)

            net_d = fd.get("net_debt", 0) or 0
            ebit  = fd.get("ebitda") or 1
            fcf   = fd.get("fcf")
            mktc  = fd.get("market_cap")

            rows.append({
                "Ticker":      ticker,
                "Name":        fd.get("name") or meta.get("name", ticker),
                "Sector":      sector,
                "Mkt Cap":     fd.get("market_cap"),
                "EV":          fd.get("enterprise_value"),
                "Price":       fd.get("price"),
                "Revenue":     fd.get("revenue_ttm"),
                "Rev Growth":  fd.get("revenue_growth_yoy"),
                "Gross Mgn":   fd.get("gross_margin"),
                "EBITDA Mgn":  fd.get("ebitda_margin"),
                "Op Margin":   fd.get("operating_margin"),
                "Net Margin":  fd.get("profit_margin"),
                "ROIC/ROE":    fd.get("roic") or fd.get("roe"),
                "ROA":         fd.get("roa"),
                "FCF Margin":  (fcf / fd.get("revenue_ttm")) if fcf and fd.get("revenue_ttm") else None,
                "ND/EBITDA":   net_d / ebit if ebit and ebit != 1 else None,
                "Curr Ratio":  fd.get("current_ratio"),
                "P/E":         fd.get("pe_trailing") or fd.get("pe_forward"),
                "EV/EBITDA":   fd.get("ev_ebitda"),
                "EV/Revenue":  fd.get("ev_revenue"),
                "P/Sales":     fd.get("ps_ratio"),
                "FCF Yield":   (fcf / mktc * 100) if fcf and mktc else None,
                "Div Yield":   (fd.get("dividend_yield") or 0) * 100,
                "Beta":        fd.get("beta") or risk_m.get("beta_calc"),
                "Volatility":  (risk_m.get("volatility_ann") or 0) * 100,
                "Drawdown":    (risk_m.get("current_drawdown_from_52w") or 0) * 100,
                "YTD":         (rets.get("ytd") or 0) * 100,
                "1Y":          (rets.get("1y") or 0) * 100,
                "Score Quality":    q_s,
                "Score Valuation":  v_s,
                "Score Growth":     g_s,
                "Score BalSheet":   b_s,
                "Score Momentum":   m_s,
                "Score Total":      comp.get("total", 0),
                "Rec":              comp.get("recommendation", "N/A"),
            })

    df = pd.DataFrame(rows).set_index("Ticker")

    # ── Comparison Tables ─────────────────────────────────────────────
    tabs = st.tabs(["📊 Fundamentals", "💰 Valuation", "📈 Growth & Profit", "🏦 Balance Sheet", "🎯 Scores & Ranking"])

    def render_compare(cols, pct_cols=[], mult_cols=[], money_cols=[]):
        html = '<table style="width:100%; border-collapse:collapse; font-size:0.82rem;">'
        html += '<tr style="border-bottom:1px solid #1e293b; color:#64748b; background:#0f172a;">'
        html += '<th style="padding:0.4rem; text-align:left;">Metric</th>'
        for t in df.index:
            html += f'<th style="padding:0.4rem; text-align:right; color:#00b4d8;">{t}</th>'
        html += '</tr>'
        for col in cols:
            if col not in df.columns:
                continue
            html += f'<tr style="border-bottom:1px solid #0f172a; color:#cbd5e1;">'
            html += f'<td style="padding:0.35rem 0.5rem; color:#94a3b8; font-size:0.8rem;">{col}</td>'
            vals = df[col]
            best = vals.max() if col not in ["P/E", "EV/EBITDA", "EV/Revenue", "Beta", "Volatility", "ND/EBITDA", "Drawdown"] else vals.min()
            for ticker in df.index:
                v = df.loc[ticker, col]
                is_best = abs(v - best) < 0.01 if pd.notna(v) and pd.notna(best) else False
                color = "#06d6a0" if is_best else "#cbd5e1"
                if pd.isna(v):
                    disp = "N/A"
                elif col in pct_cols:
                    disp = f"{v*100:.1f}%"
                elif col in mult_cols:
                    disp = f"{v:.1f}x"
                elif col in money_cols:
                    disp = f"${v/1e9:.2f}B" if abs(v) >= 1e9 else f"${v/1e6:.0f}M"
                else:
                    disp = f"{v:.1f}"
                html += f'<td style="padding:0.35rem 0.5rem; text-align:right; color:{color}; font-weight:{"600" if is_best else "400"};">{disp}</td>'
            html += '</tr>'
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)

    with tabs[0]:
        render_compare(
            ["Revenue", "Rev Growth", "Gross Mgn", "EBITDA Mgn", "Op Margin", "Net Margin", "ROIC/ROE", "ROA"],
            pct_cols=["Rev Growth", "Gross Mgn", "EBITDA Mgn", "Op Margin", "Net Margin", "ROIC/ROE", "ROA"],
            money_cols=["Revenue"],
        )

    with tabs[1]:
        render_compare(
            ["P/E", "EV/EBITDA", "EV/Revenue", "P/Sales", "FCF Yield", "Div Yield"],
            mult_cols=["P/E", "EV/EBITDA", "EV/Revenue", "P/Sales"],
        )

    with tabs[2]:
        render_compare(
            ["YTD", "1Y", "FCF Margin", "Beta", "Volatility", "Drawdown"],
        )

    with tabs[3]:
        render_compare(
            ["ND/EBITDA", "Curr Ratio"],
            mult_cols=["ND/EBITDA", "Curr Ratio"],
        )

    with tabs[4]:
        # Score ranking table
        score_cols = ["Score Quality", "Score Valuation", "Score Growth", "Score BalSheet", "Score Momentum", "Score Total", "Rec"]
        df_scores = df[score_cols].copy().reset_index()
        df_scores = df_scores.sort_values("Score Total", ascending=False).reset_index(drop=True)
        st.dataframe(df_scores, use_container_width=True, hide_index=True)

        # Bubble chart: EV/EBITDA vs Rev Growth, size = Mkt Cap
        plot_df = df[["EV/EBITDA", "Rev Growth", "Mkt Cap", "Sector"]].copy().reset_index()
        plot_df = plot_df.dropna(subset=["EV/EBITDA", "Rev Growth", "Mkt Cap"])
        if not plot_df.empty:
            plot_df["Rev Growth"] = plot_df["Rev Growth"] * 100
            fig = scatter_bubble(plot_df, "Rev Growth", "EV/EBITDA", "Mkt Cap", "Sector", "Ticker",
                                 "EV/EBITDA vs Revenue Growth (bubble = Market Cap)")
            st.plotly_chart(fig, use_container_width=True)
