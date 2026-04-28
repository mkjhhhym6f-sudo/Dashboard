"""
valuation_center.py — Page 6: Standalone DCF & valuation tooling.
FIEUS Analytics

Data: manual_fundamentals.csv / manual_valuation.csv > yfinance
If data is missing, always shows manual input panel — never crashes.
"""
import streamlit as st
import pandas as pd

from theme import (render_hero, render_section, UDES_GOLD, POSITIVE, NEGATIVE,
                    TEXT_PRIMARY, TEXT_MUTED, BG_CARD, BORDER, color_for_value)
from market_data import (load_universe, fetch_fundamentals,
                          get_data_source_label,
                          SRC_CIQ, SRC_YF, SRC_FIEUS, SRC_PREMIUM)
from valuation import estimate_wacc, dcf_fcf, reverse_dcf_fcf, sensitivity_table, scenario_dcf
from charts import sensitivity_heatmap
from formatting import fmt_price, fmt_pct, fmt_large, is_valid, safe_float


def render():
    render_hero(
        "Valuation Center",
        "DCF · Reverse DCF · Sensitivity · Bull/Base/Bear scenarios",
        "💰",
    )

    universe = load_universe()
    if universe.empty:
        st.error("Could not load universe.csv")
        return
    companies = universe[~universe["is_etf"]].copy()

    c1, c2 = st.columns([3, 1])
    with c1:
        ticker = st.selectbox(
            "Select Company",
            options=companies["ticker"].tolist(),
            format_func=lambda t: f"{t} — {companies[companies['ticker']==t]['name'].iloc[0]}",
        )
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner(f"Loading {ticker}..."):
        fund = fetch_fundamentals(ticker)

    has_mf = fund.get("has_manual_fundamentals", False)
    has_mv = fund.get("has_manual_valuation", False)

    # ── Auto-populated values from CSV / yfinance ────────────────────────────
    price_auto  = fund.get("price")
    fcf_auto    = fund.get("fcf") or fund.get("free_cash_flow")
    shares_auto = fund.get("shares_outstanding")
    nd_auto     = fund.get("net_debt") or 0.0
    beta_auto   = fund.get("beta") or 1.0
    mktcap_auto = fund.get("market_cap")
    ev_auto     = fund.get("enterprise_value")
    ev_ebitda   = fund.get("ev_ebitda")
    pe          = fund.get("pe_trailing") or fund.get("pe_forward")

    price_src  = get_data_source_label(fund, "price")
    fcf_src    = get_data_source_label(fund, "fcf")
    shr_src    = get_data_source_label(fund, "shares_outstanding")
    nd_src     = get_data_source_label(fund, "net_debt")
    mf_date    = fund.get("manual_fund_last_update") or ""
    mv_date    = fund.get("manual_val_last_update") or ""

    # ── Context cards ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price",   fmt_price(price_auto),   help=f"Source: {price_src}")
    c2.metric("Free Cash Flow",  fmt_large(fcf_auto),     help=f"Source: {fcf_src}")
    c3.metric("Shares Out",      fmt_large(shares_auto),  help=f"Source: {shr_src}")
    c4.metric("Net Debt",        fmt_large(nd_auto),      help=f"Source: {nd_src}")

    if has_mv:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Market Cap", fmt_large(mktcap_auto), help=f"Source: {mv_date or SRC_CIQ}")
        c2.metric("Enterprise Value", fmt_large(ev_auto), help=f"Source: {mv_date or SRC_CIQ}")
        c3.metric("EV/EBITDA", f"{ev_ebitda:.1f}x" if is_valid(ev_ebitda) else "N/A",
                   help=f"Source: {mv_date or SRC_CIQ}")
        c4.metric("P/E", f"{pe:.1f}x" if is_valid(pe) else "N/A",
                   help=f"Source: {mv_date or SRC_CIQ}")

    if not has_mf and not has_mv:
        st.info(
            "No manual fundamentals found for this ticker in the CSV files.  \n"
            "Fill `config/manual_fundamentals.csv` from Capital IQ to enable reliable DCF.  \n"
            "You can still use the manual input panel below."
        )
    else:
        badges = []
        if has_mf:
            badges.append(f"✅ Fundamentals: {fund.get('manual_fund_source') or SRC_CIQ}"
                           + (f" · {mf_date}" if mf_date else ""))
        if has_mv:
            badges.append(f"✅ Valuation: {mv_date or SRC_CIQ}")
        st.success("  |  ".join(badges))

    # ── Always show manual input panel ───────────────────────────────────────
    render_section("DCF Inputs")

    st.caption(
        "Pre-filled from CSV/yfinance where available. "
        "Override manually if needed. "
        "**All DCF outputs are estimates — verify assumptions before use.**"
    )

    with st.expander("📝 Manual Input Override", expanded=not (has_mf or is_valid(fcf_auto))):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Source: {fcf_src}**" if is_valid(fcf_auto) else f"**Source: {SRC_PREMIUM} — enter manually**")
            fcf_input = st.number_input(
                "Free Cash Flow (absolute, e.g. 800000000)",
                value=float(fcf_auto) if is_valid(fcf_auto) else 0.0,
                step=1e6,
                format="%.0f",
                key="vc_fcf",
                help="Enter in company currency (CAD or USD). Source will be shown as FIEUS manual.",
            )
        with col2:
            st.markdown(f"**Source: {shr_src}**" if is_valid(shares_auto) else f"**Source: {SRC_PREMIUM} — enter manually**")
            shares_input = st.number_input(
                "Shares Outstanding (diluted, absolute)",
                value=float(shares_auto) if is_valid(shares_auto) else 1e8,
                step=1e6,
                format="%.0f",
                key="vc_shares",
            )
        col3, col4 = st.columns(2)
        with col3:
            price_input = st.number_input(
                "Current Price",
                value=float(price_auto) if is_valid(price_auto) else 0.0,
                step=0.01,
                key="vc_price",
                help=f"Source: {price_src}",
            )
        with col4:
            nd_input = st.number_input(
                "Net Debt (enter negative if net cash)",
                value=float(nd_auto) if is_valid(nd_auto) else 0.0,
                step=1e6,
                format="%.0f",
                key="vc_nd",
                help=f"Source: {nd_src}",
            )

    # Use manual overrides if CSV not available; CSV otherwise
    fcf    = fcf_input    if fcf_input != 0    else (fcf_auto    or 0)
    shares = shares_input if shares_input != 1e8 else (shares_auto or 1e8)
    price  = price_input  if price_input != 0  else (price_auto  or 0)
    nd     = nd_input

    inputs_ok = is_valid(fcf) and fcf > 0 and is_valid(shares) and shares > 0 and is_valid(price) and price > 0

    if not inputs_ok:
        st.warning(
            "⚠️ DCF requires positive FCF, share count, and price.  \n"
            "Use the manual input panel above to enter assumptions.  \n"
            f"FCF: {fmt_large(fcf)} · Shares: {fmt_large(shares)} · Price: {fmt_price(price)}"
        )
        return

    # ── WACC ─────────────────────────────────────────────────────────────────
    render_section("Cost of Capital (WACC)")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Cost of Capital**")
        beta_in = st.number_input("Beta", value=safe_float(beta_auto, 1.0), step=0.1, key="vc_b")
        rf_in   = st.number_input("Risk-Free Rate (%)", value=4.0, step=0.1, key="vc_rf") / 100
    with c2:
        st.markdown("**Market Parameters**")
        erp_in  = st.number_input("Equity Risk Premium (%)", value=5.5, step=0.1, key="vc_erp") / 100
        dw_in   = st.slider("Debt Weight", 0.0, 0.6, 0.30, step=0.05, key="vc_dw")
    with c3:
        st.markdown("**DCF Structure**")
        tg_in   = st.number_input("Terminal Growth (%)", value=2.5, step=0.1, key="vc_tg") / 100
        proj_y  = st.selectbox("Projection Years", [5, 7, 10], index=2, key="vc_proj")

    wacc_r = estimate_wacc(beta_in, rf_in, erp_in, dw_in, 0.055, 0.265)
    wacc   = wacc_r["wacc"]

    st.markdown(f"""
    <div style="background:{BG_CARD};border-left:3px solid {UDES_GOLD};
                border-radius:0 8px 8px 0;padding:0.8rem 1.2rem;margin:0.5rem 0;">
        <span style="color:{UDES_GOLD};font-size:1.4rem;font-weight:900;">
            WACC = {wacc*100:.2f}%
        </span>
        <span style="color:{TEXT_MUTED};font-size:11px;margin-left:1rem;">
            Cost of equity: {wacc_r['cost_of_equity']*100:.2f}%
            · After-tax cost of debt: {wacc_r['after_tax_cod']*100:.2f}%
        </span>
        <span style="color:{TEXT_MUTED};font-size:9px;margin-left:1rem;">
            Source: FIEUS manual assumptions (CAPM)
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── DCF ──────────────────────────────────────────────────────────────────
    render_section("DCF — Intrinsic Value")

    c1, c2 = st.columns(2)
    with c1:
        g1 = st.number_input("Phase 1 Growth (%)", value=10.0, step=0.5, key="vc_g1") / 100
    with c2:
        g2 = st.number_input("Phase 2 Growth (%)", value=5.0, step=0.5, key="vc_g2") / 100

    dcf = dcf_fcf(fcf, g1, g2, tg_in, wacc, proj_y, nd, shares)
    iv  = dcf.get("intrinsic_value_per_share", 0)
    ev  = dcf.get("enterprise_value", 0)
    pv_fcfs = dcf.get("pv_fcfs", 0)
    pv_tv   = dcf.get("pv_terminal_value", 0)

    if is_valid(iv) and iv > 0:
        upside = (iv / price - 1) * 100
        upside_color = POSITIVE if upside >= 0 else NEGATIVE
        cols = st.columns(4)
        cols[0].metric("Intrinsic Value / Share", fmt_price(iv),
                        delta=f"{upside:+.1f}% vs market")
        cols[1].metric("Enterprise Value (DCF)",  fmt_large(ev))
        cols[2].metric("PV of FCFs",              fmt_large(pv_fcfs))
        cols[3].metric("PV of Terminal Value",    fmt_large(pv_tv))
        st.caption(
            f"DCF inputs: FCF={fmt_large(fcf)} · WACC={wacc*100:.2f}% · "
            f"Phase 1 growth={g1*100:.1f}% · Phase 2 growth={g2*100:.1f}% · "
            f"Terminal growth={tg_in*100:.1f}% · "
            f"Source: {fcf_src} FCF, FIEUS manual assumptions"
        )

    # ── Reverse DCF ──────────────────────────────────────────────────────────
    render_section("Reverse DCF — Implied Growth")

    rev_dcf = reverse_dcf_fcf(price, fcf, wacc, tg_in, proj_y, nd, shares)
    g_pct   = rev_dcf.get("implied_annual_growth_pct", 0)
    assess  = rev_dcf.get("assessment", "")
    g_color = NEGATIVE if g_pct > 20 else "#F59E0B" if g_pct > 10 else POSITIVE

    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};
                border-radius:10px;padding:1rem 1.2rem;">
        <p style="color:{TEXT_MUTED};font-size:11px;margin:0;text-transform:uppercase;">
            Implied Annual FCF Growth Rate
        </p>
        <p style="color:{g_color};font-size:2rem;font-weight:900;
                   margin:0.3rem 0;font-family:Merriweather,serif;">
            {g_pct:.1f}% / year
        </p>
        <p style="color:{TEXT_SECONDARY};font-size:13px;margin:0;">{assess}</p>
        <p style="color:{TEXT_MUTED};font-size:9px;margin-top:6px;">
            To justify current price of {fmt_price(price)} using {fcf_src} FCF.
            This is an estimate — verify assumptions independently.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Bull / Base / Bear Scenarios ─────────────────────────────────────────
    render_section("Scenario Analysis")

    scenarios = scenario_dcf(fcf, wacc, tg_in, proj_y, nd, shares)
    cols = st.columns(3)
    for col, (sc_name, sc) in zip(cols, scenarios.items()):
        implied_ret = (
            ((sc["price_per_share"] / price) - 1) * 100
            if is_valid(sc["price_per_share"]) and price > 0
            else None
        )
        ret_str = f"{implied_ret:+.1f}% vs market" if is_valid(implied_ret) else ""
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {sc['color']}66;
                    border-left:4px solid {sc['color']};border-radius:10px;
                    padding:1rem;">
            <p style="color:{sc['color']};font-weight:700;margin:0;font-size:0.9rem;">
                {sc['label']}
            </p>
            <p style="color:{TEXT_MUTED};font-size:0.75rem;margin:0.2rem 0;">
                {sc['description']}
            </p>
            <p style="color:{TEXT_PRIMARY};font-size:1.5rem;font-weight:900;
                       margin:0.4rem 0;font-family:Merriweather,serif;">
                {fmt_price(sc['price_per_share'])}
            </p>
            <p style="color:{sc['color']};font-size:0.8rem;margin:0;">{ret_str}</p>
        </div>
        """, unsafe_allow_html=True)

    st.caption(
        "Scenarios use FIEUS manual DCF assumptions. "
        "These are illustrative estimates — not price targets. "
        "Verify all inputs with Capital IQ or company filings."
    )

    # ── Sensitivity Table ─────────────────────────────────────────────────────
    render_section("Sensitivity: WACC vs Growth")

    wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
    g_range    = [0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
    try:
        sens_df = sensitivity_table(fcf, wacc_range, g_range, tg_in, proj_y, nd, shares)
        fig_sens = sensitivity_heatmap(
            sens_df, current_price=price,
            title="DCF Sensitivity — Implied Price per Share",
        )
        st.plotly_chart(fig_sens, use_container_width=True)
        st.caption(
            f"Rows = Phase 1 FCF growth rate. Columns = WACC.  "
            f"Gold marker = current market price ({fmt_price(price)}).  "
            f"Source: {fcf_src} FCF, FIEUS assumptions."
        )
    except Exception as e:
        st.caption(f"Sensitivity table unavailable: {e}")
