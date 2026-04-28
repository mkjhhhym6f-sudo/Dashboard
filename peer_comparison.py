"""
Page 5 — Peer Comparison
Multi-ticker side-by-side analysis with best-in-class highlighting.
"""
import streamlit as st
import pandas as pd
import numpy as np

from theme import (UDES_GOLD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                   POSITIVE, NEGATIVE, NEUTRAL, BG_CARD, BORDER,
                   render_hero, render_section, rec_badge,
                   color_for_value, color_for_score)
from formatting import fmt_pct, fmt_multiple, fmt_large, fmt_number, is_valid
from market_data import load_universe, fetch_portfolio_snapshot
from scoring import (compute_composite_score, score_quality, score_valuation,
                     score_growth, score_balance_sheet, score_momentum)
from charts import scatter_bubble


def render():
    st.markdown(render_hero(
        "Peer Comparison",
        "Compare up to 8 securities across all dimensions — best-in-class highlighted",
        "⚖️"
    ), unsafe_allow_html=True)

    universe = load_universe()
    if universe.empty:
        st.error("Universe not available.")
        return

    equities = universe[universe["is_etf"] == False]
    name_map = {r["ticker"]: f"{r['ticker']} — {r['name']}"
                for _, r in equities.iterrows()}

    selected = st.multiselect(
        "Select 2-8 companies",
        options=equities["ticker"].tolist(),
        format_func=lambda x: name_map.get(x, x),
        default=equities["ticker"].head(5).tolist(),
        max_selections=8,
    )

    if len(selected) < 2:
        st.info("Select at least 2 companies.")
        return

    with st.spinner("Loading peer data..."):
        snap = fetch_portfolio_snapshot(selected, period="1y")

    if snap.empty:
        st.warning("No data available.")
        return

    # Compute scores
    rows = []
    for _, r in snap.iterrows():
        rets = {"1d": r.get("ret_1d"), "1m": r.get("ret_1m"),
                "3m": r.get("ret_3m"), "ytd": r.get("ret_ytd"), "1y": r.get("ret_1y")}
        sector = r["sector"]
        fund = r["fundamentals"]

        q = score_quality(fund, sector)["score"]
        v = score_valuation(fund, sector)["score"]
        g = score_growth(fund)["score"]
        b = score_balance_sheet(fund, sector)["score"]
        m = score_momentum(rets)["score"]
        composite = compute_composite_score(fund, rets, sector, "Neutral", False)

        rows.append({
            "Ticker": r["ticker"], "Name": r["name"], "Sector": sector,
            "Mkt Cap": fund.get("market_cap"),
            "Revenue": fund.get("revenue_ttm"),
            "Rev Growth": fund.get("revenue_growth_yoy"),
            "Gross Mgn": fund.get("gross_margin"),
            "EBITDA Mgn": fund.get("ebitda_margin"),
            "Op Margin": fund.get("operating_margin"),
            "Net Margin": fund.get("profit_margin"),
            "ROE": fund.get("roe"), "ROIC": fund.get("roic"),
            "FCF Margin": (fund.get("fcf") / fund.get("revenue_ttm"))
                          if is_valid(fund.get("fcf")) and is_valid(fund.get("revenue_ttm")) and fund.get("revenue_ttm") > 0
                          else None,
            "Net Debt": fund.get("net_debt"),
            "ND/EBITDA": (fund.get("net_debt") / fund.get("ebitda"))
                         if is_valid(fund.get("net_debt")) and is_valid(fund.get("ebitda")) and fund.get("ebitda") > 0
                         else None,
            "Curr Ratio": fund.get("current_ratio"),
            "P/E": fund.get("pe_trailing") or fund.get("pe_forward"),
            "EV/EBITDA": fund.get("ev_ebitda"),
            "EV/Rev": fund.get("ev_revenue"),
            "P/B": fund.get("pb_ratio"),
            "Div Yield": fund.get("dividend_yield"),
            "FCF Yield": (fund.get("fcf") / fund.get("market_cap"))
                         if is_valid(fund.get("fcf")) and is_valid(fund.get("market_cap")) and fund.get("market_cap") > 0
                         else None,
            "Beta": fund.get("beta"),
            "Volatility": r.get("volatility"),
            "Drawdown": r.get("drawdown"),
            "YTD": r.get("ret_ytd"),
            "1Y": r.get("ret_1y"),
            "S Quality": q, "S Valuation": v, "S Growth": g,
            "S BalSheet": b, "S Momentum": m,
            "Score": composite["total"],
            "Rec": composite["recommendation"],
        })
    df = pd.DataFrame(rows).set_index("Ticker")

    # Render comparison table helper
    def _comp_table(cols, fmt_map):
        """fmt_map: {col_name: ('pct'|'mult'|'large'|'num', good_high)}"""
        rows_html = []
        # Header
        rows_html.append(f'<tr><th>Metric</th>{"".join(f"<th>{t}</th>" for t in df.index)}</tr>')
        for col in cols:
            if col not in df.columns:
                continue
            fmt_type, good_high = fmt_map.get(col, ("num", True))
            vals = df[col]
            valid_vals = vals.dropna()
            if valid_vals.empty:
                best_idx = None
            else:
                best_idx = valid_vals.idxmax() if good_high else valid_vals.idxmin()
            cells = []
            for ticker in df.index:
                v = df.loc[ticker, col]
                if not is_valid(v):
                    cells.append(f'<td style="color:{TEXT_MUTED};">N/A</td>')
                    continue
                if fmt_type == "pct":      disp = fmt_pct(v)
                elif fmt_type == "mult":   disp = fmt_multiple(v)
                elif fmt_type == "large":  disp = fmt_large(v)
                else:                      disp = fmt_number(v)
                color = POSITIVE if ticker == best_idx else TEXT_PRIMARY
                weight = 700 if ticker == best_idx else 400
                cells.append(f'<td style="color:{color}; font-weight:{weight};">{disp}</td>')
            rows_html.append(f'<tr><td style="color:{TEXT_SECONDARY}; font-size:0.82rem;">{col}</td>{"".join(cells)}</tr>')
        st.markdown(f"<table>{''.join(rows_html)}</table>", unsafe_allow_html=True)

    tabs = st.tabs(["📊 Fundamentals", "💰 Valuation", "📈 Returns & Risk", "🏦 Balance Sheet", "🎯 Scores"])

    with tabs[0]:
        _comp_table(
            ["Revenue", "Rev Growth", "Gross Mgn", "EBITDA Mgn", "Op Margin", "Net Margin", "ROE", "ROIC", "FCF Margin"],
            {"Revenue": ("large", True),
             "Rev Growth": ("pct", True), "Gross Mgn": ("pct", True),
             "EBITDA Mgn": ("pct", True), "Op Margin": ("pct", True), "Net Margin": ("pct", True),
             "ROE": ("pct", True), "ROIC": ("pct", True), "FCF Margin": ("pct", True)}
        )

    with tabs[1]:
        _comp_table(
            ["P/E", "EV/EBITDA", "EV/Rev", "P/B", "FCF Yield", "Div Yield"],
            {"P/E": ("mult", False), "EV/EBITDA": ("mult", False),
             "EV/Rev": ("mult", False), "P/B": ("mult", False),
             "FCF Yield": ("pct", True), "Div Yield": ("pct", True)}
        )

    with tabs[2]:
        _comp_table(
            ["YTD", "1Y", "Beta", "Volatility", "Drawdown"],
            {"YTD": ("pct", True), "1Y": ("pct", True),
             "Beta": ("num", False), "Volatility": ("pct", False),
             "Drawdown": ("pct", True)}
        )

    with tabs[3]:
        _comp_table(
            ["Net Debt", "ND/EBITDA", "Curr Ratio"],
            {"Net Debt": ("large", False), "ND/EBITDA": ("mult", False),
             "Curr Ratio": ("num", True)}
        )

    with tabs[4]:
        score_cols = ["S Quality", "S Valuation", "S Growth", "S BalSheet", "S Momentum", "Score"]
        rows_html = [f'<tr><th>Score Component</th>{"".join(f"<th>{t}</th>" for t in df.index)}</tr>']
        for col in score_cols:
            cells = []
            best = df[col].max() if df[col].notna().any() else None
            for ticker in df.index:
                v = df.loc[ticker, col]
                if not is_valid(v):
                    cells.append(f'<td style="color:{TEXT_MUTED};">N/A</td>')
                else:
                    color = color_for_score(v) if col == "Score" else (POSITIVE if v == best else TEXT_PRIMARY)
                    weight = 700 if v == best else 500
                    cells.append(f'<td style="color:{color}; font-weight:{weight};">{v:.0f}</td>')
            label = col.replace("S ", "")
            rows_html.append(f'<tr><td style="color:{TEXT_SECONDARY};">{label}</td>{"".join(cells)}</tr>')
        # Recommendation row
        rec_cells = "".join(f'<td>{rec_badge(df.loc[t, "Rec"])}</td>' for t in df.index)
        rows_html.append(f'<tr><td style="color:{TEXT_SECONDARY};">Recommendation</td>{rec_cells}</tr>')
        st.markdown(f"<table>{''.join(rows_html)}</table>", unsafe_allow_html=True)

        # Bubble chart
        st.markdown(render_section("EV/EBITDA vs Revenue Growth"), unsafe_allow_html=True)
        plot_df = df[["EV/EBITDA", "Rev Growth", "Mkt Cap", "Sector"]].copy().reset_index()
        plot_df = plot_df.dropna(subset=["EV/EBITDA", "Rev Growth", "Mkt Cap"])
        if not plot_df.empty:
            plot_df["Rev Growth"] = plot_df["Rev Growth"] * 100
            fig = scatter_bubble(plot_df, "Rev Growth", "EV/EBITDA", "Mkt Cap",
                                  "Sector", "Ticker",
                                  "EV/EBITDA vs Revenue Growth (bubble = Market Cap)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient data for bubble chart.")
