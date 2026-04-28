"""
Page 5 — Peer Comparison
FIEUS Analytics — multi-ticker side-by-side analysis.

Data: manual_fundamentals.csv / manual_valuation.csv > yfinance
"""
import streamlit as st
import pandas as pd
import numpy as np

from theme import (UDES_GOLD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                   POSITIVE, NEGATIVE, NEUTRAL, BG_CARD, BORDER,
                   render_hero, render_section, rec_badge,
                   color_for_value, color_for_score)
from formatting import fmt_pct, fmt_multiple, fmt_large, fmt_number, is_valid
from market_data import load_universe, fetch_portfolio_snapshot, SRC_CIQ, SRC_YF, SRC_PREMIUM
from scoring import (compute_composite_score, score_quality, score_valuation,
                     score_growth, score_balance_sheet, score_momentum)
from charts import scatter_bubble


def render():
    # render_hero() calls st.markdown internally — do NOT wrap in st.markdown()
    render_hero(
        "Peer Comparison",
        "Compare up to 8 securities — best-in-class highlighted",
        "⚖️",
    )

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

    # ── Build comparison DataFrame ───────────────────────────────────────────
    rows = []
    for _, r in snap.iterrows():
        rets  = {"1d": r.get("ret_1d"), "1m": r.get("ret_1m"),
                 "3m": r.get("ret_3m"), "ytd": r.get("ret_ytd"), "1y": r.get("ret_1y")}
        sector = r["sector"]
        fund   = r["fundamentals"] if isinstance(r["fundamentals"], dict) else {}

        has_mf = fund.get("has_manual_fundamentals", False)
        has_mv = fund.get("has_manual_valuation", False)

        q = score_quality(fund, sector)["score"]
        v = score_valuation(fund, sector)["score"]
        g = score_growth(fund)["score"]
        b = score_balance_sheet(fund, sector)["score"]
        m = score_momentum(rets)["score"]
        composite = compute_composite_score(fund, rets, sector, "Neutral", False)

        # FCF values — prefer CSV sources
        fcf = fund.get("fcf") or fund.get("free_cash_flow")
        rev = fund.get("revenue_ttm")
        mc  = fund.get("market_cap")
        eb  = fund.get("ebitda")
        nd  = fund.get("net_debt")

        rows.append({
            "Ticker":    r["ticker"],
            "Name":      r.get("name", r["ticker"]),
            "Sector":    sector,
            "Data":      ("CSV" if (has_mf or has_mv) else "yf"),
            "Mkt Cap":   mc,
            "Revenue":   rev,
            "Rev Growth": fund.get("revenue_growth_yoy"),
            "Gross Mgn": fund.get("gross_margin"),
            "EBITDA Mgn": fund.get("ebitda_margin"),
            "Op Margin": fund.get("operating_margin"),
            "Net Margin": fund.get("profit_margin"),
            "ROE":       fund.get("roe"),
            "ROIC":      fund.get("roic"),
            "FCF Margin": (fcf / rev) if is_valid(fcf) and is_valid(rev) and rev > 0 else None,
            "Net Debt":  nd,
            "ND/EBITDA": (nd / eb) if is_valid(nd) and is_valid(eb) and eb > 0
                          else fund.get("net_debt_ebitda"),
            "Curr Ratio": fund.get("current_ratio"),
            "P/E":       fund.get("pe_trailing") or fund.get("pe_forward"),
            "EV/EBITDA": fund.get("ev_ebitda"),
            "EV/Rev":    fund.get("ev_revenue") or fund.get("ev_sales"),
            "P/B":       fund.get("pb_ratio") or fund.get("price_book"),
            "Div Yield": fund.get("dividend_yield"),
            "FCF Yield": (fcf / mc) if is_valid(fcf) and is_valid(mc) and mc > 0
                          else fund.get("fcf_yield"),
            "Beta":      fund.get("beta"),
            "Volatility": r.get("volatility"),
            "Drawdown":  r.get("drawdown"),
            "YTD":       r.get("ret_ytd"),
            "1Y":        r.get("ret_1y"),
            "S Quality":   q,
            "S Valuation": v,
            "S Growth":    g,
            "S BalSheet":  b,
            "S Momentum":  m,
            "Score":     composite["total"],
            "Rec":       composite["recommendation"],
        })

    df = pd.DataFrame(rows).set_index("Ticker")

    # ── Data quality warning ─────────────────────────────────────────────────
    csv_tickers = [r["Ticker"] for r in rows if r["Data"] == "CSV"]
    yf_only     = [r["Ticker"] for r in rows if r["Data"] == "yf"]
    if yf_only:
        st.warning(
            f"⚠️ **Fundamentals from yfinance only** (may be N/A for TSX): "
            f"{', '.join(yf_only)}. "
            f"Fill `config/manual_fundamentals.csv` from Capital IQ for accurate data."
        )
    if csv_tickers:
        st.success(f"✅ CSV/Capital IQ fundamentals loaded for: {', '.join(csv_tickers)}")

    # ── Comparison table helper ──────────────────────────────────────────────
    def _comp_table(cols_spec, fmt_map):
        """
        cols_spec : list of column names to display
        fmt_map   : {col: ('pct'|'mult'|'large'|'num', good_high)}
        """
        rows_html = [
            f'<tr><th style="text-align:left;color:{TEXT_MUTED};font-size:11px;">Metric</th>'
            + "".join(
                f'<th style="color:{UDES_GOLD};font-size:12px;">{t}<br>'
                f'<span style="color:{TEXT_MUTED};font-size:9px;font-weight:400;">'
                f'{"CSV" if t in csv_tickers else "yfinance"}</span></th>'
                for t in df.index
            )
            + "</tr>"
        ]
        for col in cols_spec:
            if col not in df.columns:
                continue
            fmt_type, good_high = fmt_map.get(col, ("num", True))
            vals       = df[col]
            valid_vals = vals.dropna()
            if valid_vals.empty:
                best_idx = None
            else:
                best_idx = valid_vals.idxmax() if good_high else valid_vals.idxmin()
            cells = []
            for ticker in df.index:
                v = df.loc[ticker, col]
                if not is_valid(v):
                    cells.append(
                        f'<td style="color:{TEXT_MUTED};font-size:12px;">'
                        f'N/A</td>'
                    )
                    continue
                if fmt_type == "pct":     disp = fmt_pct(v)
                elif fmt_type == "mult":  disp = fmt_multiple(v)
                elif fmt_type == "large": disp = fmt_large(v)
                else:                     disp = fmt_number(v)
                color  = POSITIVE if ticker == best_idx else TEXT_PRIMARY
                weight = 700 if ticker == best_idx else 400
                cells.append(
                    f'<td style="color:{color};font-weight:{weight};font-size:12px;">'
                    f'{disp}</td>'
                )
            rows_html.append(
                f'<tr><td style="color:{TEXT_SECONDARY};font-size:11px;'
                f'white-space:nowrap;">{col}</td>'
                + "".join(cells)
                + "</tr>"
            )
        st.markdown(
            f'<div style="overflow-x:auto;">'
            f'<table style="border-collapse:collapse;width:100%;">'
            f'{"".join(rows_html)}'
            f'</table></div>',
            unsafe_allow_html=True,
        )

    # ── Tab layout ────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📊 Fundamentals", "💰 Valuation",
        "📈 Returns & Risk", "🏦 Balance Sheet", "🎯 Scores",
    ])

    with tabs[0]:
        _comp_table(
            ["Revenue", "Rev Growth", "Gross Mgn", "EBITDA Mgn",
             "Op Margin", "Net Margin", "ROE", "ROIC", "FCF Margin"],
            {"Revenue": ("large", True),
             "Rev Growth": ("pct", True), "Gross Mgn": ("pct", True),
             "EBITDA Mgn": ("pct", True), "Op Margin": ("pct", True),
             "Net Margin": ("pct", True), "ROE": ("pct", True),
             "ROIC": ("pct", True), "FCF Margin": ("pct", True)},
        )
        st.caption(
            "Green = best in peer group.  "
            "N/A = unavailable from current source.  "
            "Fill `config/manual_fundamentals.csv` for accurate data."
        )

    with tabs[1]:
        _comp_table(
            ["P/E", "EV/EBITDA", "EV/Rev", "P/B", "FCF Yield", "Div Yield"],
            {"P/E": ("mult", False), "EV/EBITDA": ("mult", False),
             "EV/Rev": ("mult", False), "P/B": ("mult", False),
             "FCF Yield": ("pct", True), "Div Yield": ("pct", True)},
        )
        st.caption("Source: manual_valuation.csv (Capital IQ) where available, else yfinance.")

    with tabs[2]:
        _comp_table(
            ["YTD", "1Y", "Beta", "Volatility", "Drawdown"],
            {"YTD": ("pct", True), "1Y": ("pct", True),
             "Beta": ("num", False), "Volatility": ("pct", False),
             "Drawdown": ("pct", True)},
        )
        st.caption(f"Source: {SRC_YF} adjusted close · Returns calculated from price history")

    with tabs[3]:
        _comp_table(
            ["Net Debt", "ND/EBITDA", "Curr Ratio"],
            {"Net Debt": ("large", False), "ND/EBITDA": ("mult", False),
             "Curr Ratio": ("num", True)},
        )
        st.caption("Source: manual_fundamentals.csv (Capital IQ) where available, else yfinance.")

    with tabs[4]:
        score_cols = ["S Quality", "S Valuation", "S Growth", "S BalSheet", "S Momentum", "Score"]
        rows_html = [
            f'<tr><th style="text-align:left;color:{TEXT_MUTED};font-size:11px;">Score Component</th>'
            + "".join(
                f'<th style="color:{UDES_GOLD};font-size:12px;">{t}</th>' for t in df.index
            )
            + "</tr>"
        ]
        for col in score_cols:
            cells = []
            best  = df[col].max() if df[col].notna().any() else None
            for ticker in df.index:
                v = df.loc[ticker, col]
                if not is_valid(v):
                    cells.append(f'<td style="color:{TEXT_MUTED};">N/A</td>')
                else:
                    color  = color_for_score(v) if col == "Score" else (POSITIVE if v == best else TEXT_PRIMARY)
                    weight = 700 if v == best else 500
                    cells.append(f'<td style="color:{color};font-weight:{weight};font-size:12px;">{v:.0f}</td>')
            label = col.replace("S ", "")
            rows_html.append(
                f'<tr><td style="color:{TEXT_SECONDARY};font-size:11px;">{label}</td>'
                + "".join(cells)
                + "</tr>"
            )
        # Recommendation row
        rec_cells = "".join(
            f'<td>{rec_badge(df.loc[t,"Rec"])}</td>' for t in df.index
        )
        rows_html.append(
            f'<tr><td style="color:{TEXT_SECONDARY};font-size:11px;">Signal</td>{rec_cells}</tr>'
        )
        st.markdown(
            f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;">'
            f'{"".join(rows_html)}</table></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "FIEUS screening scores: Quality 25% · Valuation 25% · Growth 20% · "
            "Balance Sheet 15% · Momentum 10% · Macro 5%  —  "
            "Preliminary signals only. Not investment recommendations."
        )

        # Bubble chart
        render_section("EV/EBITDA vs Revenue Growth")
        plot_df = df[["EV/EBITDA", "Rev Growth", "Mkt Cap", "Sector"]].copy().reset_index()
        plot_df = plot_df.dropna(subset=["EV/EBITDA", "Rev Growth", "Mkt Cap"])
        if not plot_df.empty:
            plot_df["Rev Growth"] = plot_df["Rev Growth"] * 100
            fig = scatter_bubble(
                plot_df, "Rev Growth", "EV/EBITDA", "Mkt Cap", "Sector", "Ticker",
                "EV/EBITDA vs Revenue Growth (bubble = Market Cap)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Insufficient data for bubble chart — "
                "EV/EBITDA and revenue growth needed. "
                "Fill `config/manual_fundamentals.csv` and `config/manual_valuation.csv`."
            )
