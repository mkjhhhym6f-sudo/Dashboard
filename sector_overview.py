"""sector_overview.py — Page 2: Sector deep dive."""
import streamlit as st
import pandas as pd
import numpy as np

from theme import (render_hero, render_section, UDES_GOLD, POSITIVE, NEGATIVE,
                    TEXT_PRIMARY, TEXT_MUTED, BG_CARD,
                    color_for_value, color_for_score)
from market_data import load_universe, fetch_portfolio_snapshot
from scoring import compute_composite_score
from charts import heatmap
from formatting import fmt_pct, is_valid


def render():
    render_hero("Sector Overview",
                 "Deep dive into a sector — fundamentals, performance, ranking",
                 "📂")

    universe = load_universe()
    if universe.empty:
        st.error("Could not load universe.csv")
        return

    companies = universe[~universe["is_etf"]].copy()
    sectors = sorted(companies["sector"].dropna().unique().tolist())

    if not sectors:
        st.warning("No sectors found.")
        return

    c1, c2 = st.columns([3, 1])
    with c1:
        selected_sector = st.selectbox("Select Sector", options=sectors)
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    sector_tickers = companies[companies["sector"] == selected_sector]["ticker"].tolist()
    st.caption(f"**{len(sector_tickers)} companies** covered in {selected_sector}")

    if not sector_tickers:
        st.info(f"No companies in {selected_sector}.")
        return

    with st.spinner(f"Loading {selected_sector}..."):
        snap = fetch_portfolio_snapshot(sector_tickers, period="1y")

    if snap.empty:
        st.warning("No data available.")
        return

    scores, recs = [], []
    for _, row in snap.iterrows():
        fund = row.get("fundamentals", {}) or {}
        rets = {"1d": row.get("ret_1d"), "1m": row.get("ret_1m"),
                "3m": row.get("ret_3m"), "6m": row.get("ret_6m"),
                "1y": row.get("ret_1y"), "ytd": row.get("ret_ytd")}
        result = compute_composite_score(fund, rets, selected_sector,
                                          regime="Neutral", is_etf=False)
        scores.append(result["total"])
        recs.append(result["recommendation"])
    snap["score"] = scores
    snap["rec"] = recs

    render_section("Sector Averages")

    def avg_metric(rows, fund_key):
        vals = [r.get("fundamentals", {}).get(fund_key) for _, r in rows.iterrows()]
        valid = [v for v in vals if is_valid(v)]
        return np.nanmean(valid) if valid else None

    valid_scores = [s for s in scores if is_valid(s)]
    avg_score = np.nanmean(valid_scores) if valid_scores else None
    ev_avg = avg_metric(snap, "ev_ebitda")
    pe_avg = avg_metric(snap, "pe_trailing")

    kpi_specs = [
        ("Avg Score", f"{avg_score:.0f}/100" if avg_score is not None else "N/A",
         color_for_score(avg_score)),
        ("Avg YTD", fmt_pct(snap["ret_ytd"].mean(), signed=True),
         color_for_value(snap["ret_ytd"].mean())),
        ("Avg Rev Growth", fmt_pct(avg_metric(snap, "revenue_growth_yoy"), signed=True), TEXT_PRIMARY),
        ("Avg EBITDA Mgn", fmt_pct(avg_metric(snap, "ebitda_margin")), TEXT_PRIMARY),
        ("Avg EV/EBITDA", f"{ev_avg:.1f}x" if is_valid(ev_avg) else "N/A", TEXT_PRIMARY),
        ("Avg P/E", f"{pe_avg:.1f}x" if is_valid(pe_avg) else "N/A", TEXT_PRIMARY),
    ]

    cols = st.columns(len(kpi_specs))
    for col, (label, val, color) in zip(cols, kpi_specs):
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid #1F3A2E;border-radius:10px;padding:14px 16px">
            <div style="color:{TEXT_MUTED};font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase">{label}</div>
            <div style="color:{color};font-size:22px;font-weight:700;margin-top:4px">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    render_section("Performance Comparison")

    hm_cols = ["ret_1d", "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y"]
    label_map = {"ret_1d": "1D", "ret_1m": "1M", "ret_3m": "3M",
                 "ret_6m": "6M", "ret_ytd": "YTD", "ret_1y": "1Y"}
    hm_df = snap[["ticker"] + hm_cols].set_index("ticker")
    hm_df.columns = [label_map[c] for c in hm_df.columns]
    hm_pct = hm_df.applymap(lambda v: v * 100 if is_valid(v) else np.nan)
    st.plotly_chart(heatmap(hm_pct, f"{selected_sector} — Return Heatmap (%)",
                             zmin=-25, zmax=25, fmt="+.1f"),
                     use_container_width=True)

    render_section("Fundamentals Snapshot")

    rows_data = []
    for _, row in snap.iterrows():
        fund = row.get("fundamentals", {}) or {}
        rev_g = fund.get("revenue_growth_yoy")
        ebm = fund.get("ebitda_margin")
        roe = fund.get("roe")
        ev_e = fund.get("ev_ebitda")
        pe = fund.get("pe_trailing") or fund.get("pe_forward")
        fcf = fund.get("fcf")
        mc = fund.get("market_cap")
        fcf_y = (fcf / mc) if (is_valid(fcf) and is_valid(mc) and mc > 0) else None

        rows_data.append({
            "Ticker": row["ticker"],
            "Company": (row["name"] or "")[:25],
            "Rev Growth": fmt_pct(rev_g, signed=True),
            "EBITDA Mgn": fmt_pct(ebm),
            "ROE": fmt_pct(roe),
            "EV/EBITDA": f"{ev_e:.1f}x" if is_valid(ev_e) and ev_e > 0 else "N/A",
            "P/E": f"{pe:.1f}x" if is_valid(pe) and pe > 0 else "N/A",
            "FCF Yield": fmt_pct(fcf_y),
            "YTD": fmt_pct(row.get("ret_ytd"), signed=True),
            "Score": f"{row['score']:.0f}" if is_valid(row.get("score")) else "N/A",
            "Rec": row.get("rec", "N/A"),
        })

    st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)

    def render_perf_card(rows, title):
        st.markdown(f"**{title}**")
        for _, r in rows.iterrows():
            v = r.get("ret_ytd")
            color = color_for_value(v)
            pct = fmt_pct(v, signed=True)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;
                        padding:8px 12px;background:{BG_CARD};border-radius:6px;
                        margin-bottom:4px;border-left:3px solid {color}">
                <div>
                    <span style="color:{UDES_GOLD};font-weight:600">{r['ticker']}</span>
                    <span style="color:{TEXT_MUTED};font-size:11px;margin-left:8px">{(r['name'] or '')[:30]}</span>
                </div>
                <span style="color:{color};font-weight:600">{pct}</span>
            </div>
            """, unsafe_allow_html=True)

    with c1:
        render_perf_card(snap.nlargest(5, "ret_ytd"), "🏆 Top Performers (YTD)")
    with c2:
        render_perf_card(snap.nsmallest(5, "ret_ytd"), "📉 Worst Performers (YTD)")
