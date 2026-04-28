"""
PAGE 9 — DATA QUALITY
Monitor data sources, cache status, missing data, API health, and data provenance.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os, sys, json
from datetime import datetime, timedelta
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from data_providers.market_data import MarketDataProvider, TICKER_MAP

DARK = "#0e1117"
CARD = "#1a1d27"
ACCENT = "#00d4aa"
TEXT = "#e0e0e0"
MUTED = "#888"
RED = "#ff4b4b"
GREEN = "#00d4aa"
YELLOW = "#ffa500"

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cache')
MANUAL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'manual')
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'config')


def render():
    st.markdown("## 🔍 Data Quality Monitor")
    st.markdown("*Monitor data sources, API health, cache freshness, and data completeness*")

    tab_overview, tab_api, tab_cache, tab_tickers, tab_manual = st.tabs([
        "📊 Overview",
        "🌐 API Health",
        "💾 Cache Status",
        "📋 Ticker Coverage",
        "📁 Manual Data"
    ])

    with tab_overview:
        _render_overview()

    with tab_api:
        _render_api_health()

    with tab_cache:
        _render_cache_status()

    with tab_tickers:
        _render_ticker_coverage()

    with tab_manual:
        _render_manual_data()


# ════════════════════════════════════════════════════════════════════════════
def _render_overview():
    st.markdown("### 📊 Data Quality Overview")

    mdp = MarketDataProvider()
    universe = mdp.get_universe()

    # ── Source definitions ────────────────────────────────────────────────────
    sources = [
        {
            'Source': 'yfinance',
            'Type': 'Market & Fundamentals',
            'Status': '🟢 Active',
            'Coverage': f"{len(universe)} tickers",
            'Frequency': 'Real-time / Daily',
            'Reliability': 'High',
            'Limitations': 'No deep historical multiples, some Canadian gaps',
            'Cost': 'Free',
            'API Key Required': '❌',
        },
        {
            'Source': 'FRED (Federal Reserve)',
            'Type': 'US Macro',
            'Status': '🟢 Active' if os.environ.get('FRED_API_KEY') else '🟡 Key Missing',
            'Coverage': '12 series',
            'Frequency': 'Daily / Monthly',
            'Reliability': 'Very High',
            'Limitations': 'US data only; some series lag 1-2 months',
            'Cost': 'Free',
            'API Key Required': '✅ FRED_API_KEY',
        },
        {
            'Source': 'Bank of Canada Valet API',
            'Type': 'Canadian Macro',
            'Status': '🟢 Active',
            'Coverage': 'BoC rate, CAD/USD, yields',
            'Frequency': 'Daily',
            'Reliability': 'Very High',
            'Limitations': 'Limited series vs FRED',
            'Cost': 'Free',
            'API Key Required': '❌',
        },
        {
            'Source': 'Manual CSV Files',
            'Type': 'Custom Data',
            'Status': '🟡 Partial',
            'Coverage': 'Analyst notes, custom fields',
            'Frequency': 'Manual',
            'Reliability': 'Analyst-dependent',
            'Limitations': 'Requires manual maintenance',
            'Cost': 'Free',
            'API Key Required': '❌',
        },
        {
            'Source': 'Capital IQ / Bloomberg',
            'Type': 'Premium Data',
            'Status': '🔴 Not Connected',
            'Coverage': 'Full financial statements, estimates',
            'Frequency': 'Real-time',
            'Reliability': 'Institutional',
            'Limitations': 'Requires subscription ($10K-$30K/yr)',
            'Cost': 'Premium',
            'API Key Required': '✅ Premium credentials',
        },
        {
            'Source': 'Financial Modeling Prep',
            'Type': 'Fundamentals',
            'Status': '🟡 Optional',
            'Coverage': 'Full financials, ratios, estimates',
            'Frequency': 'Daily',
            'Reliability': 'High',
            'Limitations': 'Free tier limited to 250 req/day',
            'Cost': 'Freemium',
            'API Key Required': '✅ FMP_API_KEY',
        },
    ]

    st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True)

    # ── Overall data completeness ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📈 Data Completeness Summary")

    completeness = {
        'Price History': 95,
        'Market Cap': 90,
        'P/E Ratio': 75,
        'EV/EBITDA': 70,
        'Revenue': 85,
        'Net Income': 80,
        'Free Cash Flow': 75,
        'ROIC': 50,
        'Debt/EBITDA': 65,
        'Macro Indicators': 80,
        'Analyst Notes': 40,
        'Target Prices': 40,
        'Historical Multiples': 10,
        'Consensus Estimates': 5,
    }

    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=list(completeness.values()),
        y=list(completeness.keys()),
        orientation='h',
        marker_color=[GREEN if v >= 80 else YELLOW if v >= 50 else RED for v in completeness.values()],
        text=[f"{v}%" for v in completeness.values()],
        textposition='outside'
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
        height=440, title="Estimated Data Completeness by Metric",
        xaxis=dict(range=[0, 115], title="% Complete"),
        margin=dict(l=160)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Premium roadmap ────────────────────────────────────────────────────────
    st.markdown("### 🚀 Data Upgrade Roadmap")
    roadmap = [
        ("Phase 1 — Current (Free)", GREEN, [
            "yfinance for prices and basic fundamentals",
            "FRED for US macro indicators",
            "Bank of Canada Valet API for Canadian macro",
            "Manual CSV for analyst notes and custom data",
            "Local Parquet cache for speed"
        ]),
        ("Phase 2 — Enhanced (Freemium)", YELLOW, [
            "Financial Modeling Prep API (free tier) for better financials",
            "Polygon.io for tick data and options",
            "OpenBB SDK for aggregated data access",
            "Automated earnings calendar alerts"
        ]),
        ("Phase 3 — Institutional (Premium)", ACCENT, [
            "Capital IQ for full financial models and estimates",
            "Bloomberg API for real-time data",
            "FactSet for sector analytics",
            "Refinitiv/LSEG for global coverage",
            "AlphaSense for document search"
        ]),
    ]
    cols = st.columns(3)
    for col, (phase, color, items) in zip(cols, roadmap):
        bullets = "".join([f"<li style='color:{TEXT};margin:4px 0'>{item}</li>" for item in items])
        col.markdown(f"""
        <div style="background:{CARD};padding:16px;border-radius:10px;border-top:3px solid {color};height:100%">
            <div style="font-weight:700;color:{color};margin-bottom:12px">{phase}</div>
            <ul style="padding-left:18px;margin:0">{bullets}</ul>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
def _render_api_health():
    st.markdown("### 🌐 API Health Check")
    st.caption("Click the button below to run a live API health check on all data sources.")

    if st.button("🔄 Run Health Check", type="primary"):
        results = []

        # yfinance test
        with st.spinner("Testing yfinance..."):
            try:
                test = yf.Ticker("SHOP.TO")
                info = test.info
                price = info.get('currentPrice', None)
                results.append({
                    'Source': 'yfinance',
                    'Status': '🟢 OK',
                    'Response Time': '~1-3s',
                    'Test Result': f"SHOP.TO price: ${price:.2f}" if price else 'Data retrieved',
                    'Note': 'Operational'
                })
            except Exception as e:
                results.append({'Source': 'yfinance', 'Status': '🔴 Error',
                                 'Response Time': 'N/A', 'Test Result': str(e)[:80],
                                 'Note': 'Check network'})

        # FRED test
        with st.spinner("Testing FRED API..."):
            fred_key = os.environ.get('FRED_API_KEY', '')
            if fred_key:
                try:
                    import requests
                    r = requests.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={'series_id': 'FEDFUNDS', 'limit': 1,
                                'api_key': fred_key, 'file_type': 'json'},
                        timeout=5
                    )
                    results.append({
                        'Source': 'FRED API',
                        'Status': '🟢 OK' if r.status_code == 200 else '🔴 Error',
                        'Response Time': f"{r.elapsed.total_seconds():.2f}s",
                        'Test Result': f"HTTP {r.status_code}",
                        'Note': 'Operational' if r.status_code == 200 else r.text[:50]
                    })
                except Exception as e:
                    results.append({'Source': 'FRED API', 'Status': '🔴 Error',
                                     'Response Time': 'N/A', 'Test Result': str(e)[:60],
                                     'Note': 'Network/timeout'})
            else:
                results.append({'Source': 'FRED API', 'Status': '🟡 No Key',
                                 'Response Time': 'N/A', 'Test Result': 'FRED_API_KEY not set',
                                 'Note': 'Add to .env file'})

        # Bank of Canada test
        with st.spinner("Testing Bank of Canada Valet API..."):
            try:
                import requests
                r = requests.get(
                    "https://www.bankofcanada.ca/valet/observations/V39079/json",
                    params={'recent': 1}, timeout=5
                )
                results.append({
                    'Source': 'Bank of Canada API',
                    'Status': '🟢 OK' if r.status_code == 200 else '🔴 Error',
                    'Response Time': f"{r.elapsed.total_seconds():.2f}s",
                    'Test Result': f"HTTP {r.status_code}",
                    'Note': 'Operational' if r.status_code == 200 else r.text[:40]
                })
            except Exception as e:
                results.append({'Source': 'Bank of Canada API', 'Status': '🔴 Error',
                                 'Response Time': 'N/A', 'Test Result': str(e)[:60],
                                 'Note': 'Network issue'})

        # Capital IQ (always not connected)
        results.append({'Source': 'Capital IQ', 'Status': '🔴 Not Connected',
                         'Response Time': 'N/A', 'Test Result': 'No credentials configured',
                         'Note': 'Requires premium subscription'})

        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
def _render_cache_status():
    st.markdown("### 💾 Cache Status")
    st.caption(f"Cache directory: `{CACHE_DIR}`")

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_files = []
    if os.path.exists(CACHE_DIR):
        for fname in sorted(os.listdir(CACHE_DIR)):
            fpath = os.path.join(CACHE_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                age = datetime.now() - mod_time
                size_kb = stat.st_size / 1024

                ttl_hours = 4 if 'price' in fname else (24 if 'fund' in fname else 12)
                is_stale = age.total_seconds() > ttl_hours * 3600

                cache_files.append({
                    'File': fname,
                    'Size (KB)': f"{size_kb:.1f}",
                    'Last Updated': mod_time.strftime('%Y-%m-%d %H:%M'),
                    'Age': _format_age(age),
                    'TTL (hrs)': ttl_hours,
                    'Status': '🔴 Stale' if is_stale else '🟢 Fresh',
                })

    if cache_files:
        st.dataframe(pd.DataFrame(cache_files), use_container_width=True, hide_index=True)

        # ── Actions ────────────────────────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Cache"):
                cleared = 0
                for fname in os.listdir(CACHE_DIR):
                    try:
                        os.remove(os.path.join(CACHE_DIR, fname))
                        cleared += 1
                    except Exception:
                        pass
                st.success(f"✅ Cleared {cleared} cache files.")
                st.rerun()
        with col2:
            if st.button("🔄 Clear Stale Only"):
                cleared = 0
                for fname in os.listdir(CACHE_DIR):
                    fpath = os.path.join(CACHE_DIR, fname)
                    stat = os.stat(fpath)
                    age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
                    ttl = 4 if 'price' in fname else (24 if 'fund' in fname else 12)
                    if age.total_seconds() > ttl * 3600:
                        try:
                            os.remove(fpath)
                            cleared += 1
                        except Exception:
                            pass
                st.success(f"✅ Cleared {cleared} stale cache files.")
                st.rerun()

        # Total size
        total_kb = sum(float(f['Size (KB)']) for f in cache_files)
        st.caption(f"Total cache size: **{total_kb:.1f} KB** ({len(cache_files)} files)")
    else:
        st.info("No cache files found. The cache will be created automatically when you load data.")
        st.markdown(f"""
        <div style="background:{CARD};padding:16px;border-radius:10px;border-left:3px solid {ACCENT}">
            <b style="color:{ACCENT}">Cache Configuration</b><br><br>
            <span style="color:{TEXT}">
            • Price history: 4 hour TTL<br>
            • Fundamentals: 24 hour TTL<br>
            • Financial statements: 24 hour TTL<br>
            • Macro data: 12 hour TTL<br>
            • Cache format: Parquet files<br>
            • Location: <code>data/cache/</code>
            </span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
def _render_ticker_coverage():
    st.markdown("### 📋 Ticker Coverage Report")
    st.caption("Live status check for all tickers in the universe.")

    mdp = MarketDataProvider()
    universe = mdp.get_universe()

    if st.button("🔄 Run Coverage Check (may take 30-60s)", type="primary"):
        rows = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, (_, row) in enumerate(universe.iterrows()):
            ticker = row['ticker']
            yf_ticker = TICKER_MAP.get(ticker, ticker + '.TO' if '.' not in ticker and ticker not in ['LULU', 'GIL'] else ticker)
            status_text.text(f"Checking {ticker} ({i+1}/{len(universe)})...")

            try:
                t = yf.Ticker(yf_ticker)
                info = t.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                has_financials = bool(info.get('totalRevenue') or info.get('trailingEps'))
                has_balance_sheet = bool(info.get('totalDebt') is not None)
                has_cashflow = bool(info.get('freeCashflow') is not None)

                rows.append({
                    'Ticker': ticker,
                    'yfinance Symbol': yf_ticker,
                    'Name': row.get('name', ''),
                    'Sector': row.get('sector', ''),
                    'Price': '✅' if price else '❌',
                    'Financials': '✅' if has_financials else '⚠️',
                    'Balance Sheet': '✅' if has_balance_sheet else '⚠️',
                    'Cash Flow': '✅' if has_cashflow else '⚠️',
                    'Status': '🟢 OK' if price else '🔴 Error',
                    'Notes': 'ETF — limited fundamentals' if row.get('is_etf') else (
                        'Data partial' if not has_financials else 'Full data'
                    )
                })
            except Exception as e:
                rows.append({
                    'Ticker': ticker,
                    'yfinance Symbol': yf_ticker,
                    'Name': row.get('name', ''),
                    'Sector': row.get('sector', ''),
                    'Price': '❌',
                    'Financials': '❌',
                    'Balance Sheet': '❌',
                    'Cash Flow': '❌',
                    'Status': '🔴 Error',
                    'Notes': str(e)[:50]
                })

            progress.progress((i + 1) / len(universe))

        status_text.empty()
        progress.empty()

        df_cov = pd.DataFrame(rows)
        st.dataframe(df_cov, use_container_width=True, hide_index=True)

        ok_count = (df_cov['Status'] == '🟢 OK').sum()
        err_count = (df_cov['Status'] == '🔴 Error').sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tickers", len(df_cov))
        col2.metric("🟢 Accessible", ok_count)
        col3.metric("🔴 Errors", err_count)

        csv = df_cov.to_csv(index=False)
        st.download_button("⬇️ Export Coverage Report", data=csv,
                           file_name="ticker_coverage_report.csv", mime="text/csv")
    else:
        # Static preview of universe
        display_cols = ['ticker', 'name', 'sector', 'currency', 'is_etf']
        available_cols = [c for c in display_cols if c in universe.columns]
        st.dataframe(universe[available_cols], use_container_width=True, hide_index=True)
        st.caption("Click the button above to run a live check on all tickers.")

        # yfinance ticker map reference
        with st.expander("🗺️ Ticker Mapping Reference (Fund → yfinance)"):
            map_rows = [{'Fund Ticker': k, 'yfinance Symbol': v} for k, v in TICKER_MAP.items()]
            st.dataframe(pd.DataFrame(map_rows), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
def _render_manual_data():
    st.markdown("### 📁 Manual Data Files")
    st.caption("View and manage manually maintained data files.")

    os.makedirs(MANUAL_DIR, exist_ok=True)

    # ── File inventory ─────────────────────────────────────────────────────────
    manual_files_def = [
        {
            'File': 'analyst_notes.csv',
            'Purpose': 'Chronological analyst notes and observations',
            'Columns': 'ticker, date, analyst, note, category',
            'Maintained By': 'Analyst team',
            'Frequency': 'As needed',
        },
        {
            'File': 'config/analyst_coverage.csv',
            'Purpose': 'Coverage assignments, recommendations, theses, target prices',
            'Columns': 'ticker, name, analyst, recommendation, target_price, thesis, risks, status, ...',
            'Maintained By': 'PM / Lead Analyst',
            'Frequency': 'Quarterly or after earnings',
        },
        {
            'File': 'config/universe.csv',
            'Purpose': 'Universe definition — tickers, sectors, currency, yfinance mapping',
            'Columns': 'ticker, name, yf_ticker, sector, currency, is_etf',
            'Maintained By': 'PM',
            'Frequency': 'When holdings change',
        },
        {
            'File': 'config/sector_config.yaml',
            'Purpose': 'Sector definitions, fair value multiples, macro sensitivity',
            'Columns': 'YAML — sector name, key_metrics, fair_multiples, drivers, risks',
            'Maintained By': 'Lead Analyst',
            'Frequency': 'Semi-annually or at regime change',
        },
        {
            'File': 'data/manual/custom_metrics.csv',
            'Purpose': 'ROIC, adjusted EBITDA, and other metrics not available from yfinance',
            'Columns': 'ticker, metric, value, period, source, notes',
            'Maintained By': 'Analyst team',
            'Frequency': 'After earnings',
        },
    ]
    st.dataframe(pd.DataFrame(manual_files_def), use_container_width=True, hide_index=True)

    # ── View existing manual files ─────────────────────────────────────────────
    st.markdown("#### 📂 Browse Manual Data Directory")
    manual_files_found = []
    for root, dirs, files in os.walk(MANUAL_DIR):
        for fname in files:
            fpath = os.path.join(root, fname)
            size_kb = os.path.getsize(fpath) / 1024
            mod_time = datetime.fromtimestamp(os.path.getmtime(fpath))
            manual_files_found.append({
                'File': os.path.relpath(fpath, MANUAL_DIR),
                'Size (KB)': f"{size_kb:.1f}",
                'Last Modified': mod_time.strftime('%Y-%m-%d %H:%M'),
            })

    if manual_files_found:
        st.dataframe(pd.DataFrame(manual_files_found), use_container_width=True, hide_index=True)
    else:
        st.info("No manual data files found in `data/manual/`. They will be created automatically as you use the Analyst Center.")

    # ── Data entry for custom metrics ──────────────────────────────────────────
    with st.expander("➕ Add Custom Metric", expanded=False):
        mdp = MarketDataProvider()
        universe = mdp.get_universe()
        tickers = universe[universe['is_etf'] == False]['ticker'].tolist()

        with st.form("custom_metric_form"):
            col1, col2 = st.columns(2)
            with col1:
                cm_ticker = st.selectbox("Ticker", tickers)
                cm_metric = st.selectbox("Metric", [
                    'ROIC', 'Adjusted EBITDA', 'Adjusted EPS', 'Normalized Revenue',
                    'Organic Growth', 'SSSG', 'Backlog', 'Book Value per Share',
                    'Tangible Book Value', 'Custom Metric'
                ])
                cm_value = st.number_input("Value", step=0.01)
            with col2:
                cm_period = st.text_input("Period (e.g. 2024Q4, FY2024)", value="")
                cm_source = st.text_input("Source (e.g. Company IR, Bloomberg)", value="")
                cm_notes = st.text_input("Notes", value="")

            save_metric = st.form_submit_button("💾 Save Metric")
            if save_metric:
                custom_path = os.path.join(MANUAL_DIR, 'custom_metrics.csv')
                new_row = pd.DataFrame([{
                    'ticker': cm_ticker,
                    'metric': cm_metric,
                    'value': cm_value,
                    'period': cm_period,
                    'source': cm_source,
                    'notes': cm_notes,
                    'entered_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                }])
                if os.path.exists(custom_path):
                    existing = pd.read_csv(custom_path)
                    combined = pd.concat([existing, new_row], ignore_index=True)
                else:
                    combined = new_row
                os.makedirs(MANUAL_DIR, exist_ok=True)
                combined.to_csv(custom_path, index=False)
                st.success(f"✅ Saved {cm_metric} for {cm_ticker}")
                st.rerun()

    # ── Premium data needed ────────────────────────────────────────────────────
    st.markdown("#### 💰 Premium Data Required")
    premium_items = [
        ("Historical EV/EBITDA multiples", "Capital IQ / Bloomberg", "For valuation percentile analysis"),
        ("Consensus earnings estimates (EPS, Revenue)", "FactSet / Bloomberg / Refinitiv", "For forward multiples"),
        ("Sell-side price targets", "Bloomberg / Refinitiv", "For consensus PT tracking"),
        ("Short interest data", "Bloomberg / S3 Partners", "For risk monitoring"),
        ("Insider transactions (detailed)", "SEDI / Edgar / Refinitiv", "For ownership analysis"),
        ("Options market data", "CBOE / Polygon.io", "For implied volatility and flow"),
        ("Credit ratings", "Moody's / S&P / DBRS", "For credit risk assessment"),
        ("Environmental/ESG scores", "MSCI / Sustainalytics", "For ESG integration"),
    ]
    for item, source, use_case in premium_items:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:8px 0;border-bottom:1px solid #333">
            <div>
                <span style="color:{TEXT};font-weight:500">🔒 {item}</span>
                <span style="color:{MUTED};font-size:12px;margin-left:12px">→ {use_case}</span>
            </div>
            <span style="color:{YELLOW};font-size:12px">{source}</span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
def _format_age(age: timedelta) -> str:
    total_seconds = int(age.total_seconds())
    if total_seconds < 3600:
        return f"{total_seconds // 60}m ago"
    elif total_seconds < 86400:
        return f"{total_seconds // 3600}h ago"
    else:
        return f"{age.days}d ago"
