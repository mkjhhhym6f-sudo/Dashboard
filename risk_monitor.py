"""risk_monitor.py — Page 7: Real-time alerts across the portfolio."""
import streamlit as st
import pandas as pd

from theme import (render_hero, render_section, UDES_GOLD, POSITIVE, NEGATIVE, NEUTRAL, INFO,
                    TEXT_PRIMARY, TEXT_MUTED, BG_CARD, BORDER)
from market_data import load_universe, fetch_portfolio_snapshot
from scoring import compute_composite_score
from formatting import fmt_pct, is_valid


def render():
    render_hero("Risk Monitor",
                 "Drawdown · Leverage · Valuation · Cash Flow alerts across the portfolio",
                 "⚠️")

    universe = load_universe()
    if universe.empty:
        st.error("Could not load universe.csv")
        return

    companies = universe[~universe["is_etf"]].copy()
    tickers = companies["ticker"].tolist()

    with st.expander("⚙️ Alert Thresholds", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            dd_th = st.slider("Drawdown alert (%)", -50, -5, -20) / 100
            ev_th = st.slider("EV/EBITDA elevated (x)", 10, 60, 30)
        with c2:
            nd_th = st.slider("ND/EBITDA high (x)", 2.0, 10.0, 5.0)
            score_th = st.slider("Score below threshold", 0, 60, 40)
        with c3:
            ytd_th = st.slider("YTD return alert (%)", -50, -5, -20) / 100
            vol_th = st.slider("Volatility high (%)", 10, 80, 40) / 100

    if st.button("🔄 Run Risk Scan"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner(f"Scanning {len(tickers)} positions..."):
        snap = fetch_portfolio_snapshot(tickers, period="1y")

    if snap.empty:
        st.warning("No data available.")
        return

    all_alerts = []
    summary_rows = []
    for _, row in snap.iterrows():
        ticker = row["ticker"]
        sector = row.get("sector", "Default")
        fund = row.get("fundamentals", {}) or {}
        rets = {"1m": row.get("ret_1m"), "3m": row.get("ret_3m"),
                "6m": row.get("ret_6m"), "1y": row.get("ret_1y"),
                "ytd": row.get("ret_ytd")}
        score_r = compute_composite_score(fund, rets, sector, "Neutral", False)
        ticker_alerts = []

        dd = row.get("drawdown")
        if is_valid(dd) and dd < dd_th:
            ticker_alerts.append(("CRITICAL", f"Drawdown {dd*100:.1f}% from 52W high"))

        ytd = row.get("ret_ytd")
        if is_valid(ytd) and ytd < ytd_th:
            ticker_alerts.append(("WARNING", f"YTD return {ytd*100:.1f}%"))

        ee = fund.get("ev_ebitda")
        if is_valid(ee) and ee > ev_th:
            ticker_alerts.append(("VALUATION", f"EV/EBITDA {ee:.1f}x (>{ev_th}x)"))

        ndv = fund.get("net_debt", 0) or 0
        eb = fund.get("ebitda", 0) or 0
        if eb > 0:
            lev = ndv / eb
            if lev > nd_th:
                ticker_alerts.append(("LEVERAGE", f"ND/EBITDA {lev:.1f}x (>{nd_th}x)"))

        vol = row.get("volatility")
        if is_valid(vol) and vol > vol_th:
            ticker_alerts.append(("VOLATILITY", f"Annual volatility {vol*100:.1f}%"))

        op_m = fund.get("operating_margin")
        if is_valid(op_m) and op_m < 0:
            ticker_alerts.append(("MARGIN", f"Negative operating margin ({op_m*100:.1f}%)"))

        fcf = fund.get("fcf")
        ni = fund.get("net_income_ttm")
        if is_valid(fcf) and is_valid(ni) and ni > 0:
            conv = fcf / ni
            if conv < 0.4:
                ticker_alerts.append(("CASH FLOW", f"FCF conversion {conv:.2f}x"))

        s = score_r.get("total")
        if is_valid(s) and s < score_th:
            ticker_alerts.append(("CRITICAL", f"Composite score {s:.0f}/100"))

        summary_rows.append({"Ticker": ticker, "Sector": sector,
                              "Score": s, "# Alerts": len(ticker_alerts),
                              "Drawdown": dd, "YTD": ytd, "Volatility": vol})
        for sev, msg in ticker_alerts:
            all_alerts.append({"Ticker": ticker, "Sector": sector,
                                "Severity": sev, "Alert": msg})

    n_critical = sum(1 for a in all_alerts if a["Severity"] in ("CRITICAL", "LEVERAGE"))
    n_warning = sum(1 for a in all_alerts if a["Severity"] in ("WARNING", "VALUATION", "MARGIN"))
    n_info = sum(1 for a in all_alerts if a["Severity"] in ("VOLATILITY", "CASH FLOW"))
    n_clean = len(snap) - len({a["Ticker"] for a in all_alerts})

    c1, c2, c3, c4 = st.columns(4)
    for col, (label, val, color) in zip(
        [c1, c2, c3, c4],
        [("Critical", n_critical, NEGATIVE), ("Warnings", n_warning, UDES_GOLD),
         ("Info", n_info, INFO), ("Clean", n_clean, POSITIVE)]
    ):
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
                    border-radius:10px;padding:14px 16px">
            <div style="color:{TEXT_MUTED};font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase">{label}</div>
            <div style="color:{color};font-size:32px;font-weight:800;margin-top:4px">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    render_section("Alert Feed")
    c1, c2 = st.columns(2)
    with c1:
        filter_sector = st.multiselect("Filter by sector",
                                         options=sorted(snap["sector"].dropna().unique().tolist()))
    with c2:
        filter_sev = st.multiselect("Filter by severity",
                                       options=["CRITICAL", "WARNING", "VALUATION", "LEVERAGE",
                                                 "MARGIN", "VOLATILITY", "CASH FLOW"])

    sev_styles = {
        "CRITICAL":   (NEGATIVE, "🔴", "alert-critical"),
        "LEVERAGE":   (NEGATIVE, "🔴", "alert-critical"),
        "WARNING":    (UDES_GOLD, "🟠", "alert-warning"),
        "VALUATION":  (UDES_GOLD, "💰", "alert-warning"),
        "MARGIN":     (UDES_GOLD, "📊", "alert-warning"),
        "VOLATILITY": (INFO, "📈", "alert-info"),
        "CASH FLOW":  (INFO, "💵", "alert-info"),
    }

    filtered = [a for a in all_alerts
                 if (not filter_sector or a["Sector"] in filter_sector)
                 and (not filter_sev or a["Severity"] in filter_sev)]

    if not filtered:
        st.markdown('<div class="alert-box alert-success">✅ No alerts match the filters.</div>',
                     unsafe_allow_html=True)
    else:
        for a in filtered:
            color, icon, css = sev_styles.get(a["Severity"], (NEUTRAL, "•", "alert-info"))
            st.markdown(f"""
            <div class="alert-box {css}">
                <span style="color:{TEXT_MUTED};font-size:11px">{a['Ticker']} · {a['Sector']}</span>
                <strong style="color:{color};margin-left:8px">{icon} {a['Severity']}</strong>:
                {a['Alert']}
            </div>
            """, unsafe_allow_html=True)

    render_section("Risk Summary Table")
    df_sum = pd.DataFrame(summary_rows).sort_values(["# Alerts", "Score"],
                                                       ascending=[False, True])
    df_disp = df_sum.copy()
    df_disp["Drawdown"] = df_disp["Drawdown"].apply(lambda v: fmt_pct(v, signed=True))
    df_disp["YTD"] = df_disp["YTD"].apply(lambda v: fmt_pct(v, signed=True))
    df_disp["Volatility"] = df_disp["Volatility"].apply(fmt_pct)
    df_disp["Score"] = df_disp["Score"].apply(lambda v: f"{v:.0f}" if is_valid(v) else "N/A")
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
