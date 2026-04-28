"""
data_quality.py — Page 9: Data source health & coverage.
FIEUS Analytics

Shows: CSV coverage, yfinance health, source inventory, confidence per ticker.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from theme import (render_hero, render_section,
                    UDES_GOLD, POSITIVE, NEGATIVE, NEUTRAL, INFO,
                    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER)
from market_data import (load_universe, load_manual_fundamentals, load_manual_valuation,
                          load_manual_targets, load_data_dictionary,
                          fetch_price_history, get_yf_ticker,
                          SRC_CIQ, SRC_YF, SRC_FIEUS, SRC_PREMIUM)
from macro_data import _get_fred_key
from formatting import is_valid


def render():
    render_hero(
        "Data Quality Monitor",
        "CSV coverage · API health · Source inventory",
        "🔧",
    )

    # ── FIEUS Disclaimer ─────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#1a2e24;border:1px solid {UDES_GOLD}44;border-radius:10px;
                padding:1rem 1.3rem;margin-bottom:1rem;">
        <p style="color:{UDES_GOLD};font-weight:700;margin:0 0 4px 0;font-size:13px;">
            ℹ️ FIEUS Data Policy
        </p>
        <p style="color:{TEXT_SECONDARY};font-size:12px;margin:0;line-height:1.6;">
            This dashboard uses free/public data sources (yfinance, FRED, BoC Valet) and
            internal FIEUS manual inputs (Capital IQ exports in CSV format).
            <strong style="color:{TEXT_PRIMARY};">For official investment decisions,
            analysts must verify financial statement data, valuation metrics, and
            target prices with Capital IQ, company filings, or official FIEUS
            research files.</strong>
            Scores are preliminary screening signals only — not final recommendations.
        </p>
    </div>
    """, unsafe_allow_html=True)

    universe = load_universe()
    mf_df    = load_manual_fundamentals()
    mv_df    = load_manual_valuation()
    mt_df    = load_manual_targets()

    # ── Data Sources Inventory ────────────────────────────────────────────────
    render_section("Data Sources Inventory")

    fred_key    = _get_fred_key()
    fred_status = ("🟢 Configured", POSITIVE) if fred_key else ("🟡 Not configured", UDES_GOLD)

    mf_rows = len(mf_df[mf_df[["revenue","ebitda","fcf","gross_margin"]].notna().any(axis=1)]) \
              if not mf_df.empty else 0
    mv_rows = len(mv_df[mv_df[["market_cap","ev_ebitda","pe"]].notna().any(axis=1)]) \
              if not mv_df.empty else 0
    mt_rows = len(mt_df[mt_df[["recommendation","target_price"]].notna().any(axis=1)]) \
              if not mt_df.empty else 0

    mf_status = (f"🟢 {mf_rows} tickers with data", POSITIVE) if mf_rows > 0 \
                else ("🟡 Template present — needs filling", UDES_GOLD) if not mf_df.empty \
                else ("🔴 File missing", NEGATIVE)
    mv_status = (f"🟢 {mv_rows} tickers with data", POSITIVE) if mv_rows > 0 \
                else ("🟡 Template present — needs filling", UDES_GOLD) if not mv_df.empty \
                else ("🔴 File missing", NEGATIVE)
    mt_status = (f"🟢 {mt_rows} tickers with targets", POSITIVE) if mt_rows > 0 \
                else ("🟡 Template present — needs filling", UDES_GOLD) if not mt_df.empty \
                else ("🔴 File missing", NEGATIVE)

    sources = [
        ("yfinance",                    "Price history, returns, volatility, drawdown",    "Free",     "Always active",             ("🟢 Active", POSITIVE)),
        ("FRED API",                    "US macro indicators (Fed, CPI, unemployment)",    "Free",     "API key required",          fred_status),
        ("Bank of Canada Valet",        "BoC policy rate, CAD/USD, yield curve",           "Free",     "No key required",           ("🟢 Active", POSITIVE)),
        ("config/manual_fundamentals.csv", f"Revenue, EBITDA, FCF, margins ({mf_rows} tickers filled)", "Internal/CIQ", "Fill from Capital IQ", mf_status),
        ("config/manual_valuation.csv",    f"EV/EBITDA, P/E, multiples ({mv_rows} tickers filled)",     "Internal/CIQ", "Fill from Capital IQ", mv_status),
        ("config/manual_targets.csv",      f"Analyst views, target prices ({mt_rows} tickers filled)",  "Internal",     "FIEUS analyst entry",  mt_status),
    ]

    for src, desc, cost, auth, (status, color) in sources:
        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
                    border-left:3px solid {color};border-radius:8px;
                    padding:12px 18px;margin:5px 0">
            <div style="display:grid;grid-template-columns:260px 1fr 100px 200px 150px;
                        gap:12px;align-items:center;">
                <div style="color:{UDES_GOLD};font-weight:700;font-size:13px;">{src}</div>
                <div style="color:{TEXT_PRIMARY};font-size:12px;">{desc}</div>
                <div style="color:{TEXT_MUTED};font-size:11px;">{cost}</div>
                <div style="color:{TEXT_SECONDARY};font-size:11px;">{auth}</div>
                <div style="color:{color};font-weight:600;font-size:12px;text-align:right;">{status}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Universe Inventory ────────────────────────────────────────────────────
    render_section("Universe Inventory")

    if universe.empty:
        st.error("universe.csv not found or empty.")
        return

    equities = universe[~universe["is_etf"]] if "is_etf" in universe.columns else universe
    etfs     = universe[universe["is_etf"]]  if "is_etf" in universe.columns else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tickers",   len(universe))
    c2.metric("Companies",       len(equities))
    c3.metric("ETF Benchmarks",  len(etfs))
    c4.metric("Analyst Coverage", len(mt_df) if not mt_df.empty else 0)

    # ── Per-Ticker Coverage Matrix ─────────────────────────────────────────────
    render_section("Per-Ticker Data Coverage")

    st.caption(
        "High = manual/Capital IQ data present.  "
        "Medium = yfinance market data only.  "
        "Low = missing or rate-limited.  "
        "Fill the CSV files to upgrade confidence."
    )

    ciq_tickers = set(mf_df["ciq_symbol"].tolist()) if (not mf_df.empty and "ciq_symbol" in mf_df.columns) else set()
    ciqv_tickers = set(mv_df["ciq_symbol"].tolist()) if (not mv_df.empty and "ciq_symbol" in mv_df.columns) else set()
    target_tickers = set(mt_df["ciq_symbol"].tolist()) if (not mt_df.empty and "ciq_symbol" in mt_df.columns) else set()

    # Check which mf rows actually have non-null fundamental data
    if not mf_df.empty:
        mf_filled = mf_df[mf_df[["revenue","ebitda","fcf","gross_margin"]].notna().any(axis=1)]
        mf_filled_set = set(mf_filled["ciq_symbol"].tolist()) if "ciq_symbol" in mf_filled.columns else set()
    else:
        mf_filled_set = set()

    if not mv_df.empty:
        mv_filled = mv_df[mv_df[["market_cap","ev_ebitda","pe"]].notna().any(axis=1)]
        mv_filled_set = set(mv_filled["ciq_symbol"].tolist()) if "ciq_symbol" in mv_filled.columns else set()
    else:
        mv_filled_set = set()

    if not mt_df.empty:
        mt_filled = mt_df[mt_df[["recommendation","target_price"]].notna().any(axis=1)]
        mt_filled_set = set(mt_filled["ciq_symbol"].tolist()) if "ciq_symbol" in mt_filled.columns else set()
    else:
        mt_filled_set = set()

    coverage_rows = []
    for _, row in equities.iterrows():
        t = row["ticker"]
        name = row.get("name", t)
        sector = row.get("sector", "N/A")
        analyst = row.get("analyst", "TBD")

        has_fund  = t in mf_filled_set
        has_val   = t in mv_filled_set
        has_tgt   = t in mt_filled_set

        if has_fund and has_val:
            confidence = "High"
            conf_color = POSITIVE
        elif has_fund or has_val:
            confidence = "Medium"
            conf_color = UDES_GOLD
        elif has_tgt:
            confidence = "Low"
            conf_color = "#F59E0B"
        else:
            confidence = "yfinance only"
            conf_color = TEXT_MUTED

        fund_status  = "✅ CSV" if has_fund  else "⬜ Needed"
        val_status   = "✅ CSV" if has_val   else "⬜ Needed"
        tgt_status   = "✅ FIEUS" if has_tgt else "⬜ Needed"

        coverage_rows.append({
            "Ticker":       t,
            "Company":      name[:30],
            "Sector":       sector,
            "Analyst":      analyst,
            "Fundamentals": fund_status,
            "Valuation":    val_status,
            "Targets":      tgt_status,
            "Confidence":   confidence,
            "_conf_color":  conf_color,
        })

    cov_df = pd.DataFrame(coverage_rows)
    if not cov_df.empty:
        # Summary counts
        high   = (cov_df["Confidence"] == "High").sum()
        medium = (cov_df["Confidence"] == "Medium").sum()
        low    = (cov_df["Confidence"] == "Low").sum()
        yf_only = (cov_df["Confidence"] == "yfinance only").sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("High confidence",    high,    help="manual_fundamentals + manual_valuation both filled")
        c2.metric("Medium confidence",  medium,  help="One of fundamentals or valuation filled")
        c3.metric("Low confidence",     low,     help="Only analyst target present")
        c4.metric("yfinance only",      yf_only, help="No manual CSV data — may have N/A fundamentals")

        # Render as styled table
        display_df = cov_df.drop(columns=["_conf_color"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Missing fundamentals list
        missing_fund = cov_df[~cov_df["Fundamentals"].str.startswith("✅")]["Ticker"].tolist()
        if missing_fund:
            with st.expander(f"⬜ {len(missing_fund)} tickers missing fundamentals CSV"):
                st.caption("These tickers need data in `config/manual_fundamentals.csv`:")
                st.code(", ".join(missing_fund))

        missing_val = cov_df[~cov_df["Valuation"].str.startswith("✅")]["Ticker"].tolist()
        if missing_val:
            with st.expander(f"⬜ {len(missing_val)} tickers missing valuation CSV"):
                st.caption("These tickers need data in `config/manual_valuation.csv`:")
                st.code(", ".join(missing_val))

    # ── Data Dictionary ───────────────────────────────────────────────────────
    render_section("Data Dictionary")

    dd = load_data_dictionary()
    if not dd.empty:
        st.dataframe(dd, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No data dictionary found. "
            "Add `config/data_dictionary.csv` to document your data schema."
        )

    # ── yfinance Health Check ─────────────────────────────────────────────────
    render_section("yfinance Health Check")

    st.caption(
        "Tests yfinance price data for a sample of tickers (~30-60s for full check). "
        "Failures indicate rate limiting or ticker mapping issues."
    )

    if st.button("🔬 Run Live yfinance Health Check", key="dq_health"):
        sample = equities["ticker"].head(10).tolist()
        results = []
        progress = st.progress(0)
        for i, t in enumerate(sample):
            progress.progress((i + 1) / len(sample))
            yf_t = get_yf_ticker(t)
            try:
                df = fetch_price_history(t, period="1mo")
                if df.empty:
                    status, color, detail = "⚠️ No price data", UDES_GOLD, "Empty response"
                else:
                    last_price = df["Close"].iloc[-1] if "Close" in df.columns else None
                    last_date  = str(df.index[-1].date()) if not df.empty else "N/A"
                    status = "✅ OK"
                    color  = POSITIVE
                    detail = f"Price: {last_price:.2f} · Last: {last_date}" if is_valid(last_price) else f"Last date: {last_date}"
            except Exception as e:
                status, color, detail = "🔴 Error", NEGATIVE, str(e)[:60]
            results.append({"Ticker": t, "yf Symbol": yf_t, "Status": status, "Detail": detail})
        progress.empty()
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    # ── How to add a new company ──────────────────────────────────────────────
    render_section("How to Add a New Company")

    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};
                border-radius:10px;padding:1rem 1.3rem;font-size:12px;color:{TEXT_SECONDARY};">
        <ol style="line-height:2;margin:0;padding-left:1.2rem;">
            <li>Open <code>config/universe.csv</code> in GitHub</li>
            <li>Add a new row with all required columns (ciq_symbol, yahoo_symbol, company, sector, ...)</li>
            <li>For TSX tickers: yahoo_symbol = <code>TICKER.TO</code> (e.g. <code>DOL.TO</code>)</li>
            <li>For NYSE/NASDAQ: yahoo_symbol = ticker as-is (e.g. <code>LULU</code>)</li>
            <li>Add a matching row in <code>config/manual_fundamentals.csv</code> from Capital IQ</li>
            <li>Add a matching row in <code>config/manual_valuation.csv</code> from Capital IQ</li>
            <li>Commit changes → Streamlit Cloud auto-redeploys in ~30 seconds</li>
            <li>Click <strong>Clear Cache &amp; Reload</strong> in the sidebar</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
