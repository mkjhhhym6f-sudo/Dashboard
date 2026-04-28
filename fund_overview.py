"""
fund_overview.py — Page 1: Portfolio overview & alerts.
FIEUS — Fonds d'investissement étudiant de l'Université de Sherbrooke

Fix: DataFrame.applymap() removed in pandas 3 — replaced with DataFrame.map()
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from theme import (render_hero, render_section, UDES_GOLD, POSITIVE, NEGATIVE,
                    TEXT_PRIMARY, TEXT_MUTED, BG_CARD, color_for_value,
                    color_for_score)
from market_data import load_universe, fetch_portfolio_snapshot
from scoring import compute_composite_score
from charts import sector_allocation_pie, heatmap, _apply_theme
from formatting import fmt_pct, fmt_price, is_valid


def render():
    render_hero(
        "Fund Overview",
        "Performance · Sector allocation · Composite scoring · Alerts",
        "🏠",
    )

    universe = load_universe()
    if universe.empty:
        st.error("Could not load `config/universe.csv`. Make sure the file exists.")
        return

    companies = universe[~universe["is_etf"]].copy()
    tickers = companies["ticker"].tolist()

    col_l, col_r = st.columns([4, 1])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner(f"Loading data for {len(tickers)} positions..."):
        snap = fetch_portfolio_snapshot(tickers, period="1y")

    if snap.empty:
        st.warning("No portfolio data available. This may be due to a yfinance rate limit — try again in a few minutes.")
        return

    scores, recs = [], []
    for _, row in snap.iterrows():
        fund = row.get("fundamentals", {}) or {}
        rets = {
            "1d": row.get("ret_1d"), "1m": row.get("ret_1m"),
            "3m": row.get("ret_3m"), "6m": row.get("ret_6m"),
            "1y": row.get("ret_1y"), "ytd": row.get("ret_ytd"),
        }
        result = compute_composite_score(
            fund, rets, row.get("sector", "Default"),
            regime="Neutral", is_etf=row.get("is_etf", False),
        )
        scores.append(result["total"])
        recs.append(result["recommendation"])
    snap["score"] = scores
    snap["rec"] = recs

    n = len(snap)
    if n > 0:
        snap["weight"] = 1 / n

    # ── Disclaimer ──────────────────────────────────────────────────────────
    st.markdown(
        """<div style="background:#1a2e24;border-left:3px solid #FFB81C;
                       padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:12px;
                       font-size:11px;color:#7A8C82;">
            <strong style="color:#FFB81C;">ℹ️ FIEUS Internal Tool</strong>
            &nbsp;—&nbsp;Scores are screening signals only. All data from yfinance (free/public).
            Verify with Capital IQ or company filings before any investment decision.
        </div>""",
        unsafe_allow_html=True,
    )

    render_section("Portfolio Performance")

    def weighted_avg(col):
        valid = snap[snap[col].notna()]
        if valid.empty:
            return None
        return (valid[col] * valid["weight"]).sum() / valid["weight"].sum()

    valid_scores = [s for s in scores if is_valid(s)]
    avg_score = np.nanmean(valid_scores) if valid_scores else None

    kpis = [
        ("Positions", str(len(snap)), TEXT_PRIMARY),
        ("Avg Score", f"{avg_score:.0f}/100" if avg_score is not None else "N/A",
         color_for_score(avg_score)),
        ("1-Day", fmt_pct(weighted_avg("ret_1d"), signed=True),
         color_for_value(weighted_avg("ret_1d"))),
        ("1-Month", fmt_pct(weighted_avg("ret_1m"), signed=True),
         color_for_value(weighted_avg("ret_1m"))),
        ("YTD", fmt_pct(weighted_avg("ret_ytd"), signed=True),
         color_for_value(weighted_avg("ret_ytd"))),
        ("1-Year", fmt_pct(weighted_avg("ret_1y"), signed=True),
         color_for_value(weighted_avg("ret_1y"))),
    ]

    cols = st.columns(len(kpis))
    for col, (label, val, color) in zip(cols, kpis):
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid #1F3A2E;border-radius:10px;padding:14px 16px">
            <div style="color:{TEXT_MUTED};font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase">{label}</div>
            <div style="color:{color};font-size:22px;font-weight:700;margin-top:4px">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("Source: yfinance adjusted close · Returns calculated · Score: FIEUS screening model")

    render_section("Sector Allocation & Performance")

    sector_grp = snap.groupby("sector").agg(
        weight=("weight", "sum"),
        avg_ytd=("ret_ytd", "mean"),
        avg_score=("score", "mean"),
        count=("ticker", "count"),
    ).reset_index()

    c1, c2 = st.columns([1, 1.4])
    with c1:
        sector_wts = dict(zip(sector_grp["sector"], sector_grp["weight"] * 100))
        st.plotly_chart(sector_allocation_pie(sector_wts), use_container_width=True)

    with c2:
        sector_grp_sorted = sector_grp.sort_values("avg_ytd", ascending=True)
        ytds = sector_grp_sorted["avg_ytd"].fillna(0) * 100
        colors = [POSITIVE if v >= 0 else NEGATIVE for v in ytds]
        fig = go.Figure(go.Bar(
            x=ytds, y=sector_grp_sorted["sector"],
            orientation="h", marker=dict(color=colors),
            text=[f"{v:+.1f}%" for v in ytds],
            textposition="outside",
        ))
        fig.update_xaxes(title_text="YTD Return (%)")
        fig.update_layout(showlegend=False)
        st.plotly_chart(
            _apply_theme(fig, "Average Sector YTD Return", height=380),
            use_container_width=True,
        )

    # ── Performance Heatmap ─────────────────────────────────────────────────
    render_section("Performance Heatmap")

    metric_options = {
        "Returns (%)": ["ret_1d", "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y"],
    }
    label_map = {
        "ret_1d": "1D", "ret_1m": "1M", "ret_3m": "3M",
        "ret_6m": "6M", "ret_ytd": "YTD", "ret_1y": "1Y",
    }

    hm_cols = metric_options["Returns (%)"]
    # pandas 3 fix: use .map() instead of .applymap()
    try:
        hm_df = snap[["ticker"] + hm_cols].set_index("ticker")
        hm_df.columns = [label_map[c] for c in hm_df.columns]
        # .map() is pandas 2.1+ / 3.x compatible; .applymap() was removed in pandas 3
        hm_pct = hm_df.map(lambda v: float(v) * 100 if is_valid(v) else np.nan)
        st.plotly_chart(
            heatmap(hm_pct, "Return Heatmap (%) — All Positions", zmin=-30, zmax=30, fmt="+.1f"),
            use_container_width=True,
        )
        st.caption("Source: yfinance · Returns = price change vs. period start · Missing = N/A")
    except Exception as e:
        st.warning(f"Heatmap unavailable: {e}")

    # ── Holdings Ranking ────────────────────────────────────────────────────
    render_section("Holdings Ranking")

    tab_all, tab_top, tab_bot = st.tabs(["All Holdings", "🏆 Top 10 (YTD)", "📉 Bottom 10 (YTD)"])

    def render_ranking(df_in: pd.DataFrame):
        cols_show = ["ticker", "name", "sector", "price", "ret_1m", "ret_ytd",
                     "ret_1y", "ev_ebitda", "score", "rec"]
        df_show = df_in[cols_show].copy()
        df_show["price"] = df_show["price"].apply(fmt_price)
        for c in ["ret_1m", "ret_ytd", "ret_1y"]:
            df_show[c] = df_show[c].apply(lambda v: fmt_pct(v, signed=True))
        df_show["ev_ebitda"] = df_show["ev_ebitda"].apply(
            lambda v: f"{v:.1f}x" if is_valid(v) and v > 0 else "N/A"
        )
        df_show["score"] = df_show["score"].apply(
            lambda v: f"{v:.0f}/100" if is_valid(v) else "N/A"
        )
        df_show.columns = ["Ticker", "Company", "Sector", "Price",
                            "1M", "YTD", "1Y", "EV/EBITDA", "Score (FIEUS)", "Signal"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(
            "Score = FIEUS screening model (quality, valuation, growth, balance sheet, "
            "momentum, macro) — preliminary signal only, not investment advice."
        )

    with tab_all:
        render_ranking(snap.sort_values("score", ascending=False, na_position="last"))
    with tab_top:
        render_ranking(snap.nlargest(10, "ret_ytd"))
    with tab_bot:
        render_ranking(snap.nsmallest(10, "ret_ytd"))

    # ── Automated Alerts ────────────────────────────────────────────────────
    render_section("Automated Alerts")

    alerts = []
    for _, row in snap.iterrows():
        t = row["ticker"]
        dd = row.get("drawdown")
        if is_valid(dd) and dd < -0.20:
            alerts.append(("critical", f"⚠️ {t} — Drawdown {dd*100:.1f}% from 52W high"))
        ytd = row.get("ret_ytd")
        if is_valid(ytd) and ytd < -0.20:
            alerts.append(("warning", f"📉 {t} — YTD return {ytd*100:.1f}%"))
        s = row.get("score")
        if is_valid(s) and s < 35:
            alerts.append(("critical", f"🔴 {t} — Low composite score {s:.0f}/100"))
        ee = row.get("ev_ebitda")
        if is_valid(ee) and ee > 30:
            alerts.append(("warning", f"💰 {t} — EV/EBITDA {ee:.1f}x — elevated"))

    if not alerts:
        st.success("✅ No critical alerts — portfolio appears healthy across monitored thresholds.")
    else:
        c1, c2 = st.columns(2)
        for i, (level, msg) in enumerate(alerts[:20]):
            css = "alert-critical" if level == "critical" else "alert-warning"
            target = c1 if i % 2 == 0 else c2
            with target:
                st.markdown(f'<div class="alert-box {css}">{msg}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    csv_data = snap.drop(columns=["fundamentals"], errors="ignore").to_csv(index=False)
    st.download_button(
        "📥 Export Portfolio Snapshot to CSV",
        data=csv_data,
        file_name="fieus_portfolio_snapshot.csv",
        mime="text/csv",
    )
    st.caption("Data: yfinance (market prices, returns). Fundamentals may be incomplete for some tickers.")
