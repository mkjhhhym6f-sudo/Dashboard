"""
PAGE 6 — VALUATION CENTER
DCF, Reverse DCF, multiples historiques, sensitivity tables, valuation bands.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_providers.market_data import MarketDataProvider
from analytics.valuation import ValuationEngine
from utils.charts import ChartFactory
from utils.formatting import fmt_currency, fmt_pct, fmt_multiple, fmt_number

DARK = "#0e1117"
CARD = "#1a1d27"
ACCENT = "#00d4aa"
TEXT = "#e0e0e0"
MUTED = "#888"
RED = "#ff4b4b"
GREEN = "#00d4aa"
YELLOW = "#ffa500"


def render():
    st.markdown("## 📐 Valuation Center")
    st.markdown("*DCF analysis, reverse DCF, historical multiples, and sensitivity tables*")

    mdp = MarketDataProvider()
    ve = ValuationEngine()
    cf = ChartFactory()

    universe = mdp.get_universe()
    equities = universe[universe['is_etf'] == False].copy()

    # ── Ticker selector ──────────────────────────────────────────────────────
    col_sel, col_mode = st.columns([3, 2])
    with col_sel:
        ticker = st.selectbox(
            "Select Company",
            equities['ticker'].tolist(),
            format_func=lambda t: f"{t} — {equities[equities['ticker']==t]['name'].values[0]}"
        )
    with col_mode:
        mode = st.radio("Analysis Mode", ["DCF Model", "Reverse DCF", "Multiples Analysis"], horizontal=True)

    info = equities[equities['ticker'] == ticker].iloc[0]
    fundamentals = mdp.get_fundamentals(ticker)
    price_hist = mdp.get_price_history(ticker, period="5y")
    current_price = float(fundamentals.get('currentPrice', 0) or 0)
    shares = float(fundamentals.get('sharesOutstanding', 0) or 0)

    # ── Snapshot bar ─────────────────────────────────────────────────────────
    snap_cols = st.columns(6)
    snap_metrics = [
        ("Price", fmt_currency(current_price, info.get('currency', 'CAD'))),
        ("Market Cap", fmt_currency(float(fundamentals.get('marketCap', 0) or 0) / 1e9, 'CAD') + "B"),
        ("EV/EBITDA", fmt_multiple(float(fundamentals.get('enterpriseToEbitda', 0) or 0))),
        ("P/E (TTM)", fmt_multiple(float(fundamentals.get('trailingPE', 0) or 0))),
        ("FCF Yield", fmt_pct(float(fundamentals.get('freeCashflow', 0) or 0) / max(float(fundamentals.get('marketCap', 1) or 1), 1))),
        ("Sector", info.get('sector', 'N/A')),
    ]
    for col, (label, val) in zip(snap_cols, snap_metrics):
        col.metric(label, val)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    if mode == "DCF Model":
        _render_dcf(ticker, fundamentals, current_price, shares, ve, cf)
    elif mode == "Reverse DCF":
        _render_reverse_dcf(ticker, fundamentals, current_price, shares, ve, cf)
    else:
        _render_multiples(ticker, fundamentals, current_price, price_hist, equities, mdp, cf)


# ════════════════════════════════════════════════════════════════════════════
# DCF MODEL
# ════════════════════════════════════════════════════════════════════════════

def _render_dcf(ticker, fundamentals, current_price, shares, ve, cf):
    st.markdown("### 📊 DCF Model — Intrinsic Value Estimation")
    st.caption("Base the model on FCF. Adjust assumptions below.")

    # ── Inputs ───────────────────────────────────────────────────────────────
    with st.expander("⚙️ DCF Assumptions", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            base_fcf = st.number_input(
                "Base FCF (M $)",
                value=round(float(fundamentals.get('freeCashflow', 0) or 0) / 1e6, 1),
                step=10.0,
                help="Trailing twelve months free cash flow in millions"
            )
            rev_growth_y1_3 = st.slider("Revenue Growth Yr 1-3 (%)", -10.0, 50.0, 10.0, 0.5)
            rev_growth_y4_7 = st.slider("Revenue Growth Yr 4-7 (%)", -5.0, 30.0, 7.0, 0.5)
        with c2:
            fcf_margin = st.slider("FCF Margin (%)", 1.0, 40.0, 15.0, 0.5)
            terminal_growth = st.slider("Terminal Growth Rate (%)", 0.5, 5.0, 2.5, 0.25)
            projection_years = st.slider("Projection Period (years)", 5, 15, 10)
        with c3:
            wacc = st.slider("WACC (%)", 5.0, 20.0, 9.0, 0.25)
            net_debt = st.number_input(
                "Net Debt (M $)",
                value=round(float(fundamentals.get('totalDebt', 0) or 0) / 1e6 -
                            float(fundamentals.get('totalCash', 0) or 0) / 1e6, 1),
                step=50.0
            )
            shares_out = st.number_input(
                "Shares Outstanding (M)",
                value=round(float(shares / 1e6) if shares else 100.0, 1),
                step=1.0
            )

    # ── Compute DCF ──────────────────────────────────────────────────────────
    result = ve.dcf_model(
        base_fcf=base_fcf * 1e6,
        growth_phase1=rev_growth_y1_3 / 100,
        growth_phase2=rev_growth_y4_7 / 100,
        fcf_margin=fcf_margin / 100,
        terminal_growth=terminal_growth / 100,
        wacc=wacc / 100,
        projection_years=projection_years,
        net_debt=net_debt * 1e6,
        shares_outstanding=shares_out * 1e6
    )

    intrinsic = result.get('intrinsic_value_per_share', 0)
    upside = (intrinsic / max(current_price, 0.01) - 1) if current_price else 0
    pv_fcfs = result.get('pv_fcfs', [])
    terminal_value = result.get('pv_terminal_value', 0)
    total_ev = result.get('enterprise_value', 0)

    # ── Output cards ─────────────────────────────────────────────────────────
    out_cols = st.columns(4)
    upside_color = GREEN if upside > 0.10 else (RED if upside < -0.10 else YELLOW)
    out_cols[0].metric("Intrinsic Value", f"${intrinsic:.2f}")
    out_cols[1].metric("Current Price", f"${current_price:.2f}")
    out_cols[2].metric("Upside / (Downside)", f"{upside:+.1%}", delta=f"{upside:+.1%}")
    recommendation = "BUY" if upside > 0.15 else ("SELL" if upside < -0.15 else "HOLD")
    out_cols[3].metric("Model Signal", recommendation)

    # ── Value bridge waterfall ────────────────────────────────────────────────
    st.markdown("#### 📊 Value Bridge")
    phases = []
    cumulative = 0
    if pv_fcfs:
        for i, v in enumerate(pv_fcfs):
            phases.append({
                'label': f"Year {i+1}",
                'value': v / 1e6,
                'type': 'relative'
            })
            cumulative += v / 1e6
        phases.append({'label': 'Terminal Value', 'value': terminal_value / 1e6, 'type': 'relative'})
        phases.append({'label': 'Enterprise Value', 'value': total_ev / 1e6, 'type': 'total'})

    if phases:
        fig_bridge = cf.waterfall_contribution(
            [p['label'] for p in phases],
            [p['value'] for p in phases],
            title="DCF Value Bridge (M $)"
        )
        st.plotly_chart(fig_bridge, use_container_width=True)

    # ── FCF projection table ──────────────────────────────────────────────────
    if result.get('projections'):
        st.markdown("#### 📋 FCF Projections")
        proj_df = pd.DataFrame(result['projections'])
        proj_df.columns = [c.replace('_', ' ').title() for c in proj_df.columns]
        st.dataframe(proj_df.style.format({
            col: "${:,.1f}M" for col in proj_df.columns if proj_df[col].dtype in [float, int]
        }), use_container_width=True)

    # ── Sensitivity table ─────────────────────────────────────────────────────
    st.markdown("#### 🔧 Sensitivity Analysis — Intrinsic Value per Share")
    _render_sensitivity(ticker, fundamentals, shares, net_debt, base_fcf,
                        rev_growth_y1_3, fcf_margin, terminal_growth, projection_years, ve)

    # ── Bull / Base / Bear ────────────────────────────────────────────────────
    st.markdown("#### 🎯 Scenario Analysis")
    _render_scenarios(ticker, fundamentals, current_price, shares, net_debt, base_fcf,
                      rev_growth_y1_3, fcf_margin, terminal_growth, projection_years, ve)


# ════════════════════════════════════════════════════════════════════════════
# REVERSE DCF
# ════════════════════════════════════════════════════════════════════════════

def _render_reverse_dcf(ticker, fundamentals, current_price, shares, ve, cf):
    st.markdown("### 🔄 Reverse DCF — Implied Growth Rate")
    st.markdown("""
    > *"What growth rate does the market assume at the current price?"*
    
    This model solves for the revenue growth rate that would justify today's stock price,
    given your WACC and FCF margin assumptions.
    """)

    with st.expander("⚙️ Reverse DCF Assumptions", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            base_fcf_rev = st.number_input(
                "Base FCF (M $)",
                value=round(float(fundamentals.get('freeCashflow', 0) or 0) / 1e6, 1),
                step=10.0, key="rev_fcf"
            )
            fcf_margin_rev = st.slider("FCF Margin Assumption (%)", 1.0, 40.0, 15.0, 0.5, key="rev_margin")
        with c2:
            wacc_rev = st.slider("WACC (%)", 5.0, 20.0, 9.0, 0.25, key="rev_wacc")
            terminal_growth_rev = st.slider("Terminal Growth (%)", 0.5, 5.0, 2.5, 0.25, key="rev_tg")
        with c3:
            projection_years_rev = st.slider("Projection Period", 5, 15, 10, key="rev_proj")
            net_debt_rev = st.number_input(
                "Net Debt (M $)",
                value=round(float(fundamentals.get('totalDebt', 0) or 0) / 1e6 -
                            float(fundamentals.get('totalCash', 0) or 0) / 1e6, 1),
                step=50.0, key="rev_nd"
            )

    shares_rev = float(shares / 1e6) if shares else 100.0

    rev_result = ve.reverse_dcf(
        current_price=current_price,
        base_fcf=base_fcf_rev * 1e6,
        fcf_margin=fcf_margin_rev / 100,
        wacc=wacc_rev / 100,
        terminal_growth=terminal_growth_rev / 100,
        projection_years=projection_years_rev,
        net_debt=net_debt_rev * 1e6,
        shares_outstanding=shares_rev * 1e6
    )

    implied_growth = rev_result.get('implied_growth_rate', 0)
    confidence = rev_result.get('confidence', 'Medium')

    # ── Result card ───────────────────────────────────────────────────────────
    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown(f"""
        <div style="background:{CARD};padding:24px;border-radius:12px;text-align:center;border:1px solid {ACCENT}">
            <div style="color:{MUTED};font-size:13px">Implied Growth Rate (Yr 1-5)</div>
            <div style="color:{ACCENT};font-size:42px;font-weight:700">{implied_growth:.1%}</div>
            <div style="color:{TEXT};font-size:12px">Per Year</div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        assessment = (
            ("🔴 Demanding", RED) if implied_growth > 0.20 else
            ("🟡 Moderate", YELLOW) if implied_growth > 0.10 else
            ("🟢 Conservative", GREEN)
        )
        st.markdown(f"""
        <div style="background:{CARD};padding:24px;border-radius:12px;text-align:center">
            <div style="color:{MUTED};font-size:13px">Market Expectation</div>
            <div style="color:{assessment[1]};font-size:28px;font-weight:700">{assessment[0]}</div>
            <div style="color:{TEXT};font-size:12px">vs. typical sector growth</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        interpretation = (
            "The market prices in exceptional growth. Only justified if the company has a structural competitive moat."
            if implied_growth > 0.20 else
            "Moderate growth expectations. Achievable for quality compounders."
            if implied_growth > 0.10 else
            "Conservative growth implied. The market may be underpricing future potential."
        )
        st.markdown(f"""
        <div style="background:{CARD};padding:24px;border-radius:12px">
            <div style="color:{MUTED};font-size:13px;margin-bottom:8px">Interpretation</div>
            <div style="color:{TEXT};font-size:13px;line-height:1.6">{interpretation}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Growth rate scenarios ─────────────────────────────────────────────────
    st.markdown("#### 📈 Price vs. Assumed Growth Rate")
    growth_range = np.linspace(-0.05, 0.35, 50)
    prices_at_growth = []
    for g in growth_range:
        r = ve.dcf_model(
            base_fcf=base_fcf_rev * 1e6,
            growth_phase1=g,
            growth_phase2=max(g * 0.6, 0.02),
            fcf_margin=fcf_margin_rev / 100,
            terminal_growth=terminal_growth_rev / 100,
            wacc=wacc_rev / 100,
            projection_years=projection_years_rev,
            net_debt=net_debt_rev * 1e6,
            shares_outstanding=shares_rev * 1e6
        )
        prices_at_growth.append(r.get('intrinsic_value_per_share', 0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[g * 100 for g in growth_range],
        y=prices_at_growth,
        mode='lines',
        name='Intrinsic Value',
        line=dict(color=ACCENT, width=2)
    ))
    fig.add_hline(y=current_price, line_dash="dash", line_color=RED,
                  annotation_text=f"Current Price ${current_price:.2f}")
    fig.add_vline(x=implied_growth * 100, line_dash="dot", line_color=YELLOW,
                  annotation_text=f"Implied Growth {implied_growth:.1%}")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
        height=380, title="Intrinsic Value per Share vs. Growth Assumption",
        xaxis_title="Revenue Growth Rate (%)", yaxis_title="Intrinsic Value ($)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Sensitivity ───────────────────────────────────────────────────────────
    st.markdown("#### 🔧 Implied Growth — WACC Sensitivity")
    wacc_range = [w / 100 for w in np.arange(6.0, 14.5, 0.5)]
    implied_by_wacc = []
    for w in wacc_range:
        r = ve.reverse_dcf(
            current_price=current_price,
            base_fcf=base_fcf_rev * 1e6,
            fcf_margin=fcf_margin_rev / 100,
            wacc=w,
            terminal_growth=terminal_growth_rev / 100,
            projection_years=projection_years_rev,
            net_debt=net_debt_rev * 1e6,
            shares_outstanding=shares_rev * 1e6
        )
        implied_by_wacc.append(r.get('implied_growth_rate', 0) * 100)

    fig2 = go.Figure(go.Bar(
        x=[f"{w*100:.1f}%" for w in wacc_range],
        y=implied_by_wacc,
        marker_color=[GREEN if v < 10 else (YELLOW if v < 20 else RED) for v in implied_by_wacc],
        text=[f"{v:.1f}%" for v in implied_by_wacc],
        textposition='outside'
    ))
    fig2.update_layout(
        template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
        height=320, title="Implied Growth Rate by WACC",
        xaxis_title="WACC", yaxis_title="Implied Growth Rate (%)"
    )
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# MULTIPLES ANALYSIS
# ════════════════════════════════════════════════════════════════════════════

def _render_multiples(ticker, fundamentals, current_price, price_hist, equities, mdp, cf):
    st.markdown("### 📊 Multiples Analysis")

    tab_hist, tab_peer, tab_bands = st.tabs(["📅 Historical Multiples", "🔁 Peer Comparison", "📏 Valuation Bands"])

    with tab_hist:
        _render_historical_multiples(ticker, fundamentals, current_price, price_hist, cf)

    with tab_peer:
        _render_peer_multiples(ticker, fundamentals, equities, mdp)

    with tab_bands:
        _render_valuation_bands(ticker, fundamentals, current_price, price_hist, cf)


def _render_historical_multiples(ticker, fundamentals, current_price, price_hist, cf):
    st.markdown("#### Historical EV/EBITDA and P/E vs. Current")

    ev_ebitda = float(fundamentals.get('enterpriseToEbitda', 0) or 0)
    pe = float(fundamentals.get('trailingPE', 0) or 0)
    pb = float(fundamentals.get('priceToBook', 0) or 0)
    ps = float(fundamentals.get('priceToSalesTrailing12Months', 0) or 0)
    pfcf = float(fundamentals.get('marketCap', 0) or 0) / max(float(fundamentals.get('freeCashflow', 1) or 1), 1)

    # Simulate historical range (yfinance doesn't provide this natively)
    st.info("""
    ℹ️ **Note:** Historical multiple time-series require a premium data source (Capital IQ, Bloomberg, etc.).
    The table below shows current multiples. For historical ranges, connect a premium provider.
    """)

    multiples_data = {
        'Metric': ['EV/EBITDA', 'P/E (TTM)', 'P/B', 'P/S', 'P/FCF'],
        'Current': [
            fmt_multiple(ev_ebitda), fmt_multiple(pe),
            fmt_multiple(pb), fmt_multiple(ps), fmt_multiple(pfcf)
        ],
        '3Y Avg (est.)': ['N/A — Premium', 'N/A — Premium', 'N/A — Premium', 'N/A — Premium', 'N/A — Premium'],
        'Percentile': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
        'Signal': [
            _multiple_signal(ev_ebitda, 8, 14),
            _multiple_signal(pe, 15, 25),
            _multiple_signal(pb, 1.5, 3.5),
            _multiple_signal(ps, 1.0, 3.0),
            _multiple_signal(pfcf, 15, 30)
        ]
    }
    st.dataframe(pd.DataFrame(multiples_data), use_container_width=True, hide_index=True)

    # Current price vs rough fair value bands
    if ev_ebitda > 0 and pe > 0:
        col1, col2 = st.columns(2)
        with col1:
            _gauge_multiple(ev_ebitda, 0, 30, "EV/EBITDA", 8, 14)
        with col2:
            _gauge_multiple(pe, 0, 60, "P/E (TTM)", 12, 25)


def _render_peer_multiples(ticker, fundamentals, equities, mdp):
    st.markdown("#### Peer Multiple Comparison")

    ticker_sector = equities[equities['ticker'] == ticker]['sector'].values[0] if len(equities[equities['ticker'] == ticker]) > 0 else None
    sector_peers = equities[equities['sector'] == ticker_sector]['ticker'].tolist()

    st.caption(f"Sector: **{ticker_sector}** — {len(sector_peers)} companies")

    rows = []
    progress = st.progress(0)
    for i, t in enumerate(sector_peers[:10]):
        try:
            f = mdp.get_fundamentals(t)
            rows.append({
                'Ticker': t,
                'Name': equities[equities['ticker'] == t]['name'].values[0] if len(equities[equities['ticker'] == t]) > 0 else t,
                'EV/EBITDA': float(f.get('enterpriseToEbitda', 0) or 0),
                'P/E': float(f.get('trailingPE', 0) or 0),
                'P/B': float(f.get('priceToBook', 0) or 0),
                'P/S': float(f.get('priceToSalesTrailing12Months', 0) or 0),
                'FCF Yield %': float(f.get('freeCashflow', 0) or 0) / max(float(f.get('marketCap', 1) or 1), 1) * 100,
                'EV/Rev': float(f.get('enterpriseToRevenue', 0) or 0),
            })
        except Exception:
            pass
        progress.progress((i + 1) / min(len(sector_peers), 10))

    progress.empty()
    if rows:
        df_peer = pd.DataFrame(rows)
        # Highlight the selected ticker
        def highlight_ticker(row):
            return ['background-color: #1a3d2e' if row['Ticker'] == ticker else '' for _ in row]
        st.dataframe(
            df_peer.set_index('Ticker').style
            .format({
                'EV/EBITDA': '{:.1f}x', 'P/E': '{:.1f}x', 'P/B': '{:.1f}x',
                'P/S': '{:.1f}x', 'FCF Yield %': '{:.1f}%', 'EV/Rev': '{:.1f}x'
            })
            .apply(highlight_ticker, axis=1),
            use_container_width=True
        )

        # Bubble chart
        df_valid = df_peer[(df_peer['EV/EBITDA'] > 0) & (df_peer['FCF Yield %'].abs() < 30)]
        if len(df_valid) > 1:
            fig = go.Figure()
            for _, row in df_valid.iterrows():
                color = ACCENT if row['Ticker'] == ticker else '#555'
                size = 20 if row['Ticker'] == ticker else 12
                fig.add_trace(go.Scatter(
                    x=[row['EV/EBITDA']],
                    y=[row['FCF Yield %']],
                    mode='markers+text',
                    name=row['Ticker'],
                    text=[row['Ticker']],
                    textposition='top center',
                    marker=dict(size=size, color=color, line=dict(width=1, color='white')),
                    showlegend=False
                ))
            fig.update_layout(
                template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
                height=380, title=f"{ticker_sector} — EV/EBITDA vs FCF Yield",
                xaxis_title="EV/EBITDA (x)", yaxis_title="FCF Yield (%)"
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_valuation_bands(ticker, fundamentals, current_price, price_hist, cf):
    st.markdown("#### Valuation Bands — Price History with Multiples Overlay")
    st.info("ℹ️ Historical per-share earnings required for EPS-based bands. Using estimated bands below.")

    if price_hist is not None and not price_hist.empty:
        eps_ttm = float(fundamentals.get('trailingEps', 0) or 0)
        pe_current = float(fundamentals.get('trailingPE', 0) or 0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=price_hist.index, y=price_hist['Close'],
            name='Price', line=dict(color=TEXT, width=2)
        ))

        if eps_ttm > 0 and pe_current > 0:
            for band_pe, label, color in [(pe_current * 0.7, 'Bear (0.7x P/E)', RED),
                                           (pe_current, 'Current P/E', YELLOW),
                                           (pe_current * 1.3, 'Bull (1.3x P/E)', GREEN)]:
                fig.add_hline(
                    y=eps_ttm * band_pe, line_dash="dot",
                    line_color=color, annotation_text=label
                )

        fig.update_layout(
            template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
            height=400, title=f"{ticker} — Price History with Valuation Bands",
            xaxis_title="Date", yaxis_title="Price ($)"
        )
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _render_sensitivity(ticker, fundamentals, shares, net_debt, base_fcf,
                        base_growth, fcf_margin, terminal_growth, proj_years, ve):
    wacc_range = [w / 100 for w in np.arange(7.0, 13.5, 1.0)]
    growth_range = [g / 100 for g in np.arange(0, 25.5, 5.0)]
    shares_m = float(shares / 1e6) if shares else 100.0

    grid = []
    for g in growth_range:
        row = []
        for w in wacc_range:
            r = ve.dcf_model(
                base_fcf=base_fcf * 1e6,
                growth_phase1=g,
                growth_phase2=max(g * 0.6, 0.02),
                fcf_margin=fcf_margin / 100,
                terminal_growth=terminal_growth / 100,
                wacc=w,
                projection_years=proj_years,
                net_debt=net_debt * 1e6,
                shares_outstanding=shares_m * 1e6
            )
            row.append(r.get('intrinsic_value_per_share', 0))
        grid.append(row)

    df_sens = pd.DataFrame(
        grid,
        index=[f"{g:.0f}% growth" for g in np.arange(0, 25.5, 5.0)],
        columns=[f"{w:.1f}% WACC" for w in np.arange(7.0, 13.5, 1.0)]
    )

    fig = go.Figure(go.Heatmap(
        z=df_sens.values,
        x=df_sens.columns.tolist(),
        y=df_sens.index.tolist(),
        colorscale='RdYlGn',
        text=[[f"${v:.0f}" for v in row] for row in df_sens.values],
        texttemplate="%{text}",
        colorbar=dict(title="Intrinsic Value ($)")
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=DARK, plot_bgcolor=CARD,
        height=340, title="Intrinsic Value per Share — Growth vs WACC",
        xaxis_title="WACC", yaxis_title="Revenue Growth (Yr 1-7)"
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_scenarios(ticker, fundamentals, current_price, shares, net_debt, base_fcf,
                      base_growth, fcf_margin, terminal_growth, proj_years, ve):
    shares_m = float(shares / 1e6) if shares else 100.0

    scenarios = {
        'Bear 🐻': dict(growth_phase1=max(base_growth / 100 - 0.08, -0.05),
                        growth_phase2=max(base_growth / 100 - 0.05, 0.01),
                        fcf_margin=(fcf_margin - 3) / 100,
                        wacc=0.11, terminal_growth=0.015),
        'Base 📊': dict(growth_phase1=base_growth / 100,
                        growth_phase2=base_growth / 100 * 0.7,
                        fcf_margin=fcf_margin / 100,
                        wacc=0.09, terminal_growth=terminal_growth / 100),
        'Bull 🐂': dict(growth_phase1=base_growth / 100 + 0.06,
                        growth_phase2=base_growth / 100 + 0.03,
                        fcf_margin=(fcf_margin + 3) / 100,
                        wacc=0.08, terminal_growth=min(terminal_growth / 100 + 0.005, 0.04)),
    }

    cols = st.columns(3)
    colors = [RED, YELLOW, GREEN]
    for col, (scenario, params), color in zip(cols, scenarios.items(), colors):
        r = ve.dcf_model(
            base_fcf=base_fcf * 1e6,
            growth_phase1=params['growth_phase1'],
            growth_phase2=params['growth_phase2'],
            fcf_margin=params['fcf_margin'],
            terminal_growth=params['terminal_growth'],
            wacc=params['wacc'],
            projection_years=proj_years,
            net_debt=net_debt * 1e6,
            shares_outstanding=shares_m * 1e6
        )
        val = r.get('intrinsic_value_per_share', 0)
        upside = (val / max(current_price, 0.01) - 1) if current_price else 0
        col.markdown(f"""
        <div style="background:{CARD};padding:20px;border-radius:10px;border-left:4px solid {color};text-align:center">
            <div style="font-size:18px;font-weight:700;color:{color}">{scenario}</div>
            <div style="font-size:32px;font-weight:800;color:{TEXT};margin:8px 0">${val:.2f}</div>
            <div style="font-size:14px;color:{color}">{upside:+.1%} vs current</div>
            <div style="font-size:11px;color:{MUTED};margin-top:8px">
                G1: {params['growth_phase1']:.0%} | WACC: {params['wacc']:.0%} | FCF%: {params['fcf_margin']:.0%}
            </div>
        </div>
        """, unsafe_allow_html=True)


def _multiple_signal(value, low_threshold, high_threshold):
    if value <= 0:
        return "N/A"
    if value < low_threshold:
        return "🟢 Cheap"
    elif value > high_threshold:
        return "🔴 Expensive"
    else:
        return "🟡 Fair"


def _gauge_multiple(value, min_val, max_val, title, green_max, red_min):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': ACCENT},
            'steps': [
                {'range': [min_val, green_max], 'color': '#1a3d2e'},
                {'range': [green_max, red_min], 'color': '#3d3a1a'},
                {'range': [red_min, max_val], 'color': '#3d1a1a'},
            ],
            'threshold': {
                'line': {'color': RED, 'width': 3},
                'thickness': 0.75,
                'value': red_min
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor=CARD, height=220, margin=dict(l=20, r=20, t=40, b=10),
        font=dict(color=TEXT)
    )
    st.plotly_chart(fig, use_container_width=True)
