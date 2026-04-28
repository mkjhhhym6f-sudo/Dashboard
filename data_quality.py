"""data_quality.py — Page 9: Data source health & ticker coverage check."""
import streamlit as st
import pandas as pd
from datetime import datetime

from theme import (render_hero, render_section,
                    UDES_GOLD, POSITIVE, NEGATIVE, NEUTRAL, INFO,
                    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER)
from market_data import (load_universe, load_analyst_coverage,
                          fetch_fundamentals, fetch_price_history, get_yf_ticker)
from macro_data import _get_fred_key
from formatting import is_valid


def render():
    render_hero("Data Quality Monitor",
                 "API health · Coverage check · Source inventory",
                 "🔧")

    universe = load_universe()
    coverage = load_analyst_coverage()

    render_section("Data Sources Inventory")

    fred_key = _get_fred_key()
    fred_status = ("🟢 Configured", POSITIVE) if fred_key else ("🟡 Not configured", UDES_GOLD)

    sources = [
        ("yfinance",                     "Stock prices, fundamentals, financials",  "Free",     "Always",                      ("🟢 Active", POSITIVE)),
        ("FRED API",                     "US macro indicators (Fed, CPI, etc.)",   "Free",     "API key required",            fred_status),
        ("Bank of Canada Valet",         "BoC rates, CAD/USD, CA yields",          "Free",     "No key needed",               ("🟢 Active", POSITIVE)),
        ("Manual CSV (analyst_coverage)", "Theses, recommendations, notes",        "Internal", "Editable in Analyst Center",  ("🟢 Active", POSITIVE)),
    ]

    for src, desc, cost, auth, (status, color) in sources:
        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
                    border-left:3px solid {color};border-radius:8px;
                    padding:14px 18px;margin:6px 0">
            <div style="display:grid;grid-template-columns:200px 1fr 100px 200px 120px;gap:16px;align-items:center">
                <div><div style="color:{UDES_GOLD};font-weight:700;font-size:13px">{src}</div></div>
                <div style="color:{TEXT_PRIMARY};font-size:12px">{desc}</div>
                <div style="color:{TEXT_MUTED};font-size:11px">{cost}</div>
                <div style="color:{TEXT_SECONDARY};font-size:11px">{auth}</div>
                <div style="color:{color};font-weight:600;font-size:12px;text-align:right">{status}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    render_section("Universe Inventory")
    n_total = len(universe) if not universe.empty else 0
    n_etfs = int(universe["is_etf"].sum()) if not universe.empty and "is_etf" in universe else 0
    n_companies = n_total - n_etfs
    n_covered = len(coverage) if not coverage.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, (label, val, color) in zip(
        [c1, c2, c3, c4],
        [("Total Tickers", n_total, TEXT_PRIMARY),
         ("Companies", n_companies, UDES_GOLD),
         ("ETF Benchmarks", n_etfs, INFO),
         ("Analyst Coverage", n_covered, POSITIVE)]
    ):
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
                    border-radius:10px;padding:14px 16px">
            <div style="color:{TEXT_MUTED};font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase">{label}</div>
            <div style="color:{color};font-size:28px;font-weight:800;margin-top:4px">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    render_section("yfinance Health Check")
    st.caption("Verify yfinance returns valid data for every ticker (~30-60s).")

    if st.button("🩺 Run Live Health Check", type="primary"):
        if universe.empty:
            st.error("No universe loaded.")
        else:
            results = []
            progress = st.progress(0)
            status_box = st.empty()

            for i, (_, row) in enumerate(universe.iterrows()):
                ticker = row["ticker"]
                status_box.text(f"Checking {ticker}...")
                yf_t = get_yf_ticker(ticker, row.get("ticker_yf"))
                fd_ok = False; price_ok = False; price = None; missing = []
                try:
                    fd = fetch_fundamentals(ticker)
                    if fd.get("data_quality") == "live":
                        fd_ok = True
                        price = fd.get("price")
                        for f in ["market_cap", "revenue_ttm", "ebitda"]:
                            if not is_valid(fd.get(f)):
                                missing.append(f)
                except Exception:
                    pass
                try:
                    p_df = fetch_price_history(ticker, period="1mo")
                    price_ok = not p_df.empty
                except Exception:
                    pass

                if fd_ok and price_ok and not missing:
                    status, color = "✅ Healthy", POSITIVE
                elif fd_ok and price_ok:
                    status, color = f"🟡 Partial ({len(missing)} missing)", UDES_GOLD
                elif fd_ok or price_ok:
                    status, color = "🟡 Degraded", UDES_GOLD
                else:
                    status, color = "🔴 Failed", NEGATIVE

                results.append({"Ticker": ticker, "yfinance": yf_t, "Status": status,
                                 "Price": f"${price:.2f}" if is_valid(price) else "N/A",
                                 "Missing": ", ".join(missing) if missing else "—"})
                progress.progress((i + 1) / len(universe))

            progress.empty()
            status_box.empty()

            df_health = pd.DataFrame(results)
            n_healthy = sum(1 for r in results if "Healthy" in r["Status"])
            n_partial = sum(1 for r in results if "Partial" in r["Status"] or "Degraded" in r["Status"])
            n_failed = sum(1 for r in results if "Failed" in r["Status"])

            c1, c2, c3 = st.columns(3)
            c1.metric("Healthy", n_healthy)
            c2.metric("Partial / Degraded", n_partial)
            c3.metric("Failed", n_failed)
            st.dataframe(df_health, use_container_width=True, hide_index=True)

    render_section("How to Add a New Company")
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};
                border-radius:8px;padding:18px 24px">
        <p style="color:{TEXT_PRIMARY};font-size:13px;line-height:1.7">
            To add a new ticker to the universe:
        </p>
        <ol style="color:{TEXT_SECONDARY};font-size:13px;line-height:1.8">
            <li>Open <code style="color:{UDES_GOLD}">config/universe.csv</code> in GitHub</li>
            <li>Click the pencil (✏️) icon to edit</li>
            <li>Add a new row with these columns:
                <pre style="background:{BORDER};padding:8px 12px;border-radius:4px;font-size:11px;color:{TEXT_PRIMARY};margin:6px 0">ticker,ticker_yf,name,sector,subsector,market,currency,is_etf,analyst,weight_pct
TSX:NEW,NEW.TO,New Company Inc,Technology,Software,TSX,CAD,False,TBD,0</pre>
            </li>
            <li>For TSX special tickers (.B/.UN/.A): use hyphen format like <code style="color:{UDES_GOLD}">QBR-B.TO</code></li>
            <li>For NYSE/NASDAQ tickers: leave the ticker as is (e.g., <code style="color:{UDES_GOLD}">LULU</code>)</li>
            <li>Commit changes — Streamlit Cloud auto-redeploys in ~30s</li>
            <li>Add analyst coverage in the <strong style="color:{UDES_GOLD}">Analyst Center</strong> page</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
