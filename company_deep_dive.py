"""
Page 4 — Company Deep Dive
Complete fundamental analysis for a single security.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import fetch_fundamentals, fetch_price_history, calculate_returns, calculate_risk_metrics, TICKER_MAP
from analytics.scoring import compute_composite_score, get_score_color, get_score_badge_class, SECTOR_BENCHMARKS
from analytics.valuation import estimate_wacc, dcf_valuation, reverse_dcf, bull_base_bear_dcf, sensitivity_table
from utils.charts import price_chart, returns_bar, gauge_chart, risk_radar, sensitivity_heatmap, waterfall_contribution, financial_trend

UNIVERSE_CSV = Path(__file__).parent.parent.parent / "config" / "universe.csv"
ANALYST_CSV  = Path(__file__).parent.parent.parent / "config" / "analyst_coverage.csv"


def _fmt(val, fmt="{:.1f}", suffix="", prefix="", na="N/A"):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return na
    try:
        return f"{prefix}{fmt.format(val)}{suffix}"
    except Exception:
        return str(val)


def _pct(val, na="N/A"):
    return _fmt(val, "{:.1f}", "%") if val is not None else na


def _pct_raw(val, na="N/A"):
    """For values already in decimal (0.15 = 15%)."""
    if val is None: return na
    return _fmt(val * 100, "{:.1f}", "%")


def _millions(val, na="N/A"):
    if val is None: return na
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


def _color_val(val, good_positive=True):
    if val is None: return "#8d99ae"
    if good_positive:
        return "#06d6a0" if val >= 0 else "#ef233c"
    else:
        return "#ef233c" if val >= 0 else "#06d6a0"


BUSINESS_DESCRIPTIONS = {
    "TSX:SHOP": {
        "model": "Shopify is a cloud-based commerce platform enabling merchants globally to build, manage, and scale multi-channel retail businesses. Revenue generated through subscriptions (merchant plans) and Merchant Solutions (payment processing, fulfillment, lending).",
        "segments": ["Subscription Solutions (recurring SaaS)", "Merchant Solutions (payments, fulfillment, capital)"],
        "geographies": ["North America (~75%)", "International (growing)"],
        "revenue_drivers": ["GMV growth", "Take rate expansion via payment adoption", "Plus merchant growth", "Offline POS penetration"],
        "margin_drivers": ["Operating leverage on fixed cost base", "Merchant Solutions margin improving at scale", "R&D as moat investment"],
        "catalysts": ["Shopify Payments adoption in new markets", "B2B commerce (Shopify Plus)", "AI features monetization", "International merchant growth"],
        "risks": ["High valuation requires sustained 20%+ growth", "Amazon/TikTok Shop competition", "Macro sensitivity (GMV tracks consumer spending)"],
    },
    "TSX:CSU": {
        "model": "Constellation Software acquires, manages and builds vertical market software (VMS) businesses globally. Pure capital allocator compounding through M&A at high IRRs. Highly decentralized operating model.",
        "segments": ["Public Sector", "Private Sector", "International"],
        "geographies": ["North America", "Europe", "Rest of World"],
        "revenue_drivers": ["M&A pace and IRR", "Organic revenue retention", "Cross-sell within verticals"],
        "margin_drivers": ["Operating leverage at portfolio companies", "G&A efficiency"],
        "catalysts": ["Continued M&A pipeline in fragmented VMS markets", "Spin-outs (TopLeft, Lumine) unlocking value", "International expansion (Atlas)"],
        "risks": ["M&A market becoming more competitive", "Key person risk (Mark Leonard)", "Premium valuation requires capital allocation excellence"],
    },
    "TSX:CP": {
        "model": "Canadian Pacific Kansas City (CPKC) operates the only single-line railroad connecting Canada, the US, and Mexico. Revenue from bulk commodities, intermodal, automotive, and industrial freight.",
        "segments": ["Grain & Fertilizers", "Energy/Chemicals", "Forest Products", "Intermodal", "Automotive", "Industrial/Consumer"],
        "geographies": ["Canada", "United States", "Mexico"],
        "revenue_drivers": ["Volume growth on new north-south corridor", "Pricing above inflation", "Automotive and intermodal growth"],
        "margin_drivers": ["Precision scheduled railroading (PSR)", "KCS synergy realization ($1B+ target)", "Network density"],
        "catalysts": ["CPKC network synergies ahead of schedule", "Nearshoring to Mexico creating freight demand", "Automotive volumes"],
        "risks": ["Macro trade slowdown reducing volumes", "Regulatory approval complexities", "Railroad labor relations"],
    },
}

GENERIC_DESCRIPTION = {
    "model": "Business description not available. Add to config/business_overviews.yaml for full detail.",
    "segments": ["Data not available — add manually"],
    "geographies": ["Data not available"],
    "revenue_drivers": ["N/A — requires manual input"],
    "margin_drivers": ["N/A — requires manual input"],
    "catalysts": ["N/A — requires analyst input"],
    "risks": ["N/A — requires analyst input"],
}


def render():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.6rem; color:#f8fafc;">🔍 Company Deep Dive</h1>
        <p style="margin:0.25rem 0 0 0; color:#94a3b8; font-size:0.9rem;">Full fundamental analysis — snapshot, financials, valuation, thesis, risks</p>
    </div>
    """, unsafe_allow_html=True)

    # Load universe
    universe = pd.read_csv(UNIVERSE_CSV)
    companies = universe[universe["is_etf"] == False]["ticker"].tolist()
    company_names = {row["ticker"]: f"{row['ticker']} — {row['name']}" for _, row in universe.iterrows() if not row["is_etf"]}

    col_sel, col_opts = st.columns([3, 1])
    with col_sel:
        selected = st.selectbox(
            "Select Company",
            options=companies,
            format_func=lambda x: company_names.get(x, x),
        )
    with col_opts:
        refresh = st.button("🔄 Refresh Data")

    if not selected:
        st.info("Select a company to begin analysis.")
        return

    # Fetch data
    with st.spinner(f"Loading data for {selected}..."):
        fund_data = fetch_fundamentals(selected, force_refresh=refresh)
        prices_df  = fetch_price_history(selected, period="5y", force_refresh=refresh)
        prices     = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
        returns    = calculate_returns(prices) if not prices.empty else {}
        risk_m     = calculate_risk_metrics(prices) if not prices.empty else {}

    meta = universe[universe["ticker"] == selected].iloc[0].to_dict() if selected in universe["ticker"].values else {}
    sector  = meta.get("sector", "Default")
    is_etf  = meta.get("is_etf", False)
    name    = fund_data.get("name") or meta.get("name", selected)

    # Load analyst notes
    try:
        analyst_df = pd.read_csv(ANALYST_CSV)
        analyst_row = analyst_df[analyst_df["ticker"] == selected]
        analyst_data = analyst_row.iloc[0].to_dict() if not analyst_row.empty else {}
    except Exception:
        analyst_data = {}

    # Compute score
    macro_regime = "Neutral"  # Would come from macro_data in full version
    score_result = compute_composite_score(fund_data, returns, sector, macro_regime, is_etf)

    # ────────────────────────────────────────────────────────
    # A. SNAPSHOT
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">A. Snapshot</div>', unsafe_allow_html=True)

    price = fund_data.get("price")
    prev  = fund_data.get("prev_close")
    day_chg = ((price / prev - 1) * 100) if price and prev else None
    day_chg_color = _color_val(day_chg)

    beta = fund_data.get("beta") or risk_m.get("beta_calc")
    vol  = risk_m.get("volatility_ann")
    drawdown = risk_m.get("current_drawdown_from_52w")

    rec = score_result.get("recommendation", "N/A")
    rec_color = score_result.get("rec_color", "#8d99ae")
    score_total = score_result.get("total")

    # Header row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = [
        (c1, "Price",        f"${price:.2f}" if price else "N/A",  f"{day_chg:+.2f}%" if day_chg else None, day_chg_color),
        (c2, "Market Cap",   _millions(fund_data.get("market_cap")), None, None),
        (c3, "EV",           _millions(fund_data.get("enterprise_value")), None, None),
        (c4, "52W H/L",      f"${fund_data.get('week_52_high', 0):.2f} / ${fund_data.get('week_52_low', 0):.2f}" if fund_data.get("week_52_high") else "N/A", None, None),
        (c5, "Beta",         _fmt(beta, "{:.2f}") if beta else "N/A", None, None),
        (c6, "Div Yield",    _pct_raw(fund_data.get("dividend_yield")), None, None),
    ]
    for col, label, val, delta, dc in metrics:
        with col:
            st.metric(label, val, delta=delta)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">Composite Score</p>
            <p style="font-size:2rem; font-weight:700; color:{get_score_color(score_total)}; margin:0.25rem 0;">{score_total or 'N/A'}</p>
            <span class="score-badge {get_score_badge_class(score_total)}">{rec}</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        vw = f"{vol*100:.1f}%" if vol else "N/A"
        st.markdown(f"""
        <div class="metric-card">
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">Annualized Volatility</p>
            <p style="font-size:1.8rem; font-weight:700; color:#ffd60a; margin:0.25rem 0;">{vw}</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        dd = f"{drawdown*100:.1f}%" if drawdown else "N/A"
        dd_color = "#ef233c" if drawdown and drawdown < -0.15 else "#ffd60a" if drawdown and drawdown < -0.07 else "#06d6a0"
        st.markdown(f"""
        <div class="metric-card">
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">DD from 52W High</p>
            <p style="font-size:1.8rem; font-weight:700; color:{dd_color}; margin:0.25rem 0;">{dd}</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        vol_avg = fund_data.get("avg_volume")
        cur_vol = fund_data.get("volume")
        vol_ratio = (cur_vol / vol_avg) if cur_vol and vol_avg and vol_avg > 0 else None
        st.markdown(f"""
        <div class="metric-card">
            <p style="color:#94a3b8; font-size:0.75rem; margin:0;">Volume vs Avg</p>
            <p style="font-size:1.8rem; font-weight:700; color:#00b4d8; margin:0.25rem 0;">{f'{vol_ratio:.2f}x' if vol_ratio else 'N/A'}</p>
        </div>
        """, unsafe_allow_html=True)

    # Price chart
    if not prices.empty:
        fig = price_chart(prices, selected)
        st.plotly_chart(fig, use_container_width=True)

    # Returns bar
    if returns:
        fig_ret = returns_bar(returns, selected)
        st.plotly_chart(fig_ret, use_container_width=True)

    # ────────────────────────────────────────────────────────
    # B. BUSINESS OVERVIEW
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">B. Business Overview</div>', unsafe_allow_html=True)
    biz = BUSINESS_DESCRIPTIONS.get(selected, GENERIC_DESCRIPTION)

    desc_from_yf = fund_data.get("description", "")
    display_desc = desc_from_yf if desc_from_yf and len(desc_from_yf) > 50 else biz["model"]

    with st.expander("Business Model & Context", expanded=True):
        st.markdown(f"<p style='color:#cbd5e1; line-height:1.7;'>{display_desc[:600]}{'...' if len(display_desc) > 600 else ''}</p>", unsafe_allow_html=True)
        st.markdown("<span class='data-source'>Source: yfinance / Manual</span>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Revenue Drivers**")
            for d in biz["revenue_drivers"]:
                st.markdown(f"• {d}")
            st.markdown("**Catalysts**")
            for c in biz["catalysts"]:
                st.markdown(f"✅ {c}")
        with c2:
            st.markdown("**Key Risks**")
            for r in biz["risks"]:
                st.markdown(f"⚠️ {r}")
            st.markdown("**Margin Drivers**")
            for m in biz["margin_drivers"]:
                st.markdown(f"• {m}")

    # ────────────────────────────────────────────────────────
    # C. PROFITABILITY & FINANCIALS
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">C. Profitability & Financials</div>', unsafe_allow_html=True)

    tabs = st.tabs(["📊 Profitability", "💵 Cash Flow", "🏦 Balance Sheet", "📈 Valuation Multiples"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        metrics_prof = [
            ("Gross Margin",    _pct_raw(fund_data.get("gross_margin"))),
            ("EBITDA Margin",   _pct_raw(fund_data.get("ebitda_margin"))),
            ("Op. Margin",      _pct_raw(fund_data.get("operating_margin"))),
            ("Net Margin",      _pct_raw(fund_data.get("profit_margin"))),
            ("ROE",             _pct_raw(fund_data.get("roe"))),
            ("ROA",             _pct_raw(fund_data.get("roa"))),
        ]
        for i, (label, val) in enumerate(metrics_prof):
            with [c1, c2, c3][i % 3]:
                st.metric(label, val)

    with tabs[1]:
        rev  = fund_data.get("revenue_ttm")
        ocf  = fund_data.get("operating_cashflow")
        fcf  = fund_data.get("fcf")
        capex_v = fund_data.get("capex")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue (TTM)", _millions(rev))
        c2.metric("Op. Cash Flow", _millions(ocf))
        c3.metric("Free Cash Flow", _millions(fcf))
        c4.metric("FCF Margin", _pct_raw(fcf / rev if fcf and rev and rev > 0 else None))

        if rev and ocf and fcf:
            rev_g = fund_data.get("revenue_growth_yoy", 0) or 0
            st.markdown(f"<span class='data-source'>Revenue growth YoY: {rev_g*100:.1f}%</span>", unsafe_allow_html=True)

    with tabs[2]:
        net_d = fund_data.get("net_debt")
        ebitda_v = fund_data.get("ebitda")
        lev = (net_d / ebitda_v) if net_d and ebitda_v and ebitda_v > 0 else None
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cash", _millions(fund_data.get("cash")))
        c2.metric("Total Debt", _millions(fund_data.get("total_debt")))
        c3.metric("Net Debt", _millions(net_d))
        c4.metric("ND/EBITDA", _fmt(lev, "{:.1f}", "x") if lev else "N/A")

        c5, c6, c7 = st.columns(3)
        c5.metric("Current Ratio", _fmt(fund_data.get("current_ratio"), "{:.1f}"))
        c6.metric("Quick Ratio",   _fmt(fund_data.get("quick_ratio"), "{:.1f}"))
        c7.metric("D/E",           _fmt(fund_data.get("debt_to_equity"), "{:.1f}", "%"))

    with tabs[3]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("P/E (TTM)",   _fmt(fund_data.get("pe_trailing"), "{:.1f}", "x"))
        c2.metric("P/E (Fwd)",   _fmt(fund_data.get("pe_forward"),  "{:.1f}", "x"))
        c3.metric("EV/EBITDA",   _fmt(fund_data.get("ev_ebitda"),   "{:.1f}", "x"))
        c4.metric("EV/Revenue",  _fmt(fund_data.get("ev_revenue"),  "{:.1f}", "x"))

        c5, c6, c7, c8 = st.columns(4)
        fcf_yield_v = (fcf / fund_data.get("market_cap")) * 100 if fcf and fund_data.get("market_cap") else None
        c5.metric("FCF Yield",   _pct(fcf_yield_v))
        c6.metric("P/Sales",     _fmt(fund_data.get("ps_ratio"),     "{:.1f}", "x"))
        c7.metric("P/Book",      _fmt(fund_data.get("pb_ratio"),     "{:.1f}", "x"))
        c8.metric("PEG",         _fmt(fund_data.get("peg_ratio"),    "{:.2f}", "x"))

    # ────────────────────────────────────────────────────────
    # D. COMPOSITE SCORE BREAKDOWN
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">D. Investment Score Breakdown</div>', unsafe_allow_html=True)

    sub_scores = score_result.get("sub_scores", {})

    c1, c2 = st.columns([1, 1])
    with c1:
        # Gauge
        if score_total:
            fig_gauge = gauge_chart(score_total, f"Composite Score — {rec}")
            st.plotly_chart(fig_gauge, use_container_width=True)

    with c2:
        # Score table
        score_labels = {
            "quality": "Quality (25%)",
            "valuation": "Valuation (25%)",
            "growth": "Growth (20%)",
            "balance_sheet": "Balance Sheet (15%)",
            "momentum": "Momentum (10%)",
            "macro_fit": "Macro Fit (5%)",
        }
        for key, label in score_labels.items():
            s = sub_scores.get(key, {})
            val = s.get("score", 0)
            color = get_score_color(val)
            bar_width = f"{val}%"
            st.markdown(f"""
            <div style="margin-bottom:0.5rem;">
                <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                    <span style="color:#94a3b8; font-size:0.8rem;">{label}</span>
                    <span style="color:{color}; font-weight:600; font-size:0.8rem;">{val}/100</span>
                </div>
                <div style="background:#1e293b; border-radius:4px; height:6px;">
                    <div style="background:{color}; width:{bar_width}; height:6px; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Score narrative
    drivers  = score_result.get("top_drivers", [])
    risks_sc = score_result.get("top_risks", [])
    if drivers or risks_sc:
        st.markdown("**Why this score?**")
        for d in drivers:
            st.markdown(f'<div class="alert-box alert-ok">✅ {d}</div>', unsafe_allow_html=True)
        for r in risks_sc:
            st.markdown(f'<div class="alert-box alert-warning">⚠️ {r}</div>', unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────
    # E. VALUATION CENTER (Mini)
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">E. Valuation — DCF & Reverse DCF</div>', unsafe_allow_html=True)

    with st.expander("⚙️ DCF Parameters", expanded=False):
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            beta_input = st.number_input("Beta", value=float(beta or 1.0), step=0.1, key="dcf_beta")
            rfr = st.number_input("Risk-Free Rate (%)", value=4.5, step=0.1, key="dcf_rfr") / 100
            erp = st.number_input("Equity Risk Premium (%)", value=5.5, step=0.1, key="dcf_erp") / 100
        with col_d2:
            dw = st.slider("Debt Weight", 0.0, 0.6, 0.30, step=0.05, key="dcf_dw")
            cod = st.number_input("Cost of Debt (%)", value=5.5, step=0.1, key="dcf_cod") / 100
            tgr = st.number_input("Terminal Growth Rate (%)", value=2.5, step=0.25, key="dcf_tgr") / 100
        with col_d3:
            em_input = st.number_input("EBITDA Margin (%)", value=float((fund_data.get("ebitda_margin") or 0.18) * 100), step=1.0, key="dcf_em") / 100
            capex_in = st.number_input("Capex % Rev", value=4.0, step=0.5, key="dcf_capex") / 100
            years_in = st.selectbox("Projection Years", [5, 7, 10], index=1, key="dcf_years")

    rev_base = fund_data.get("revenue_ttm")
    net_debt_v = fund_data.get("net_debt", 0) or 0
    shares = fund_data.get("shares_outstanding")

    if rev_base and shares and rev_base > 0:
        wacc_result = estimate_wacc(beta_input, rfr, erp, dw, cod)
        wacc_val = wacc_result["wacc"]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Estimated WACC: `{wacc_val*100:.2f}%`**")
            st.markdown(f"- Cost of Equity: {wacc_result['cost_of_equity']*100:.2f}%")
            st.markdown(f"- After-tax CoD: {wacc_result['after_tax_cod']*100:.2f}%")

            # Reverse DCF
            if price:
                rev_result = reverse_dcf(
                    price, net_debt_v, shares, rev_base, em_input,
                    capex_in, 0.265, 0.01, wacc_val, tgr, years=years_in
                )
                impl_g = rev_result["implied_annual_growth_pct"]
                g_color = "#ef233c" if impl_g > 20 else "#ffd60a" if impl_g > 10 else "#06d6a0"
                st.markdown(f"""
                <div class="alert-box alert-info">
                    <strong>Reverse DCF</strong><br>
                    The current price of ${price:.2f} implies <span style="color:{g_color}; font-weight:700;">{impl_g:.1f}% annual revenue growth</span> for {years_in} years.<br>
                    <em>{rev_result['assessment']}</em>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            # Bull/Base/Bear
            scenarios = bull_base_bear_dcf(rev_base, em_input, wacc_val, net_debt_v, shares)
            for sc_name, sc in scenarios.items():
                implied_return = ((sc["price_per_share"] / price) - 1) * 100 if price and sc["price_per_share"] else None
                color = sc["color"]
                ret_str = f"({implied_return:+.1f}% upside)" if implied_return else ""
                st.markdown(f"""
                <div style="border-left: 3px solid {color}; padding: 0.5rem 0.75rem; margin:0.25rem 0; background: rgba(0,0,0,0.3);">
                    <strong style="color:{color};">{sc['label']}</strong>
                    <span style="color:#94a3b8; font-size:0.8rem;"> — {sc['description']}</span><br>
                    <span style="font-size:1.1rem; font-weight:600;">
                        {'$'+f'{sc["price_per_share"]:.2f}' if sc["price_per_share"] else 'N/A'}
                        <span style="color:#8d99ae; font-size:0.85rem;"> {ret_str}</span>
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # Sensitivity table
        wacc_range = [wacc_val - 0.02, wacc_val - 0.01, wacc_val, wacc_val + 0.01, wacc_val + 0.02]
        g_range = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
        try:
            sens_df = sensitivity_table(rev_base, wacc_range, g_range, em_input, capex_in, 0.265, 0.01, net_debt_v, shares, tgr, years_in)
            fig_sens = sensitivity_heatmap(sens_df, current_price=price, title="DCF Sensitivity: Implied Price vs WACC & Growth")
            st.plotly_chart(fig_sens, use_container_width=True)
        except Exception as e:
            st.warning(f"Sensitivity table error: {e}")
    else:
        st.info("⚠️ Revenue or share count not available from yfinance. Enter manually or use Premium Data.")

    # ────────────────────────────────────────────────────────
    # F. INVESTMENT THESIS
    # ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">F. Investment Thesis</div>', unsafe_allow_html=True)

    analyst_rec   = analyst_data.get("recommendation", "N/A")
    analyst_tp    = analyst_data.get("target_price_cad", "N/A")
    analyst_thesis = analyst_data.get("thesis_summary", "No thesis available — add in analyst_coverage.csv")
    analyst_risks  = analyst_data.get("key_risks", "No risks documented.")
    analyst_status = analyst_data.get("status", "À revoir")
    analyst_name   = analyst_data.get("analyst_name", "TBD")
    next_earnings  = analyst_data.get("next_earnings", "N/A")

    col_th1, col_th2 = st.columns([2, 1])
    with col_th1:
        st.markdown(f"""
        <div style="background:#111827; border-radius:10px; padding:1rem; border:1px solid #1e293b;">
            <div style="display:flex; gap:1rem; align-items:center; margin-bottom:0.75rem;">
                <span style="background:rgba(0,180,216,0.15); color:#00b4d8; padding:0.2rem 0.6rem; border-radius:12px; font-size:0.8rem; border:1px solid #00b4d8;">Analyst: {analyst_name}</span>
                <span style="background:rgba(6,214,160,0.15); color:#06d6a0; padding:0.2rem 0.6rem; border-radius:12px; font-size:0.8rem; border:1px solid #06d6a0;">{analyst_rec}</span>
                <span style="color:#94a3b8; font-size:0.8rem;">TP: {analyst_tp}</span>
                <span style="color:#ffd60a; font-size:0.8rem;">Status: {analyst_status}</span>
            </div>
            <p style="color:#cbd5e1; line-height:1.7; font-size:0.9rem;"><strong>Thesis:</strong> {analyst_thesis}</p>
            <p style="color:#94a3b8; line-height:1.6; font-size:0.85rem;"><strong>Key Risks:</strong> {analyst_risks}</p>
        </div>
        """, unsafe_allow_html=True)
    with col_th2:
        st.markdown(f"""
        <div style="background:#111827; border-radius:10px; padding:1rem; border:1px solid #1e293b;">
            <p style="color:#94a3b8; font-size:0.8rem; margin:0;">Next Earnings</p>
            <p style="color:#f8fafc; font-size:1.1rem; font-weight:600; margin:0.25rem 0;">{next_earnings}</p>
            <hr style="border-color:#1e293b; margin:0.5rem 0;">
            <p style="color:#94a3b8; font-size:0.8rem; margin:0;">Sector</p>
            <p style="color:#00b4d8; font-size:0.95rem; margin:0.25rem 0;">{sector}</p>
        </div>
        """, unsafe_allow_html=True)
