"""valuation_center.py — Page 6: Standalone DCF & valuation tooling."""
import streamlit as st
import pandas as pd

from theme import (render_hero, render_section, UDES_GOLD, POSITIVE, NEGATIVE,
                    TEXT_PRIMARY, TEXT_MUTED, BG_CARD, BORDER, color_for_value)
from market_data import load_universe, fetch_fundamentals
from valuation import estimate_wacc, dcf_fcf, reverse_dcf_fcf, sensitivity_table, scenario_dcf
from charts import sensitivity_heatmap
from formatting import fmt_price, fmt_pct, fmt_currency, is_valid, safe_float


def render():
    render_hero("Valuation Center",
                 "DCF · Reverse DCF · Sensitivity · Bull/Base/Bear scenarios",
                 "💰")

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

    price = fund.get("price")
    fcf = fund.get("fcf")
    shares = fund.get("shares_outstanding")
    nd = fund.get("net_debt") or 0
    beta = fund.get("beta") or 1.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", fmt_price(price))
    c2.metric("Free Cash Flow", fmt_currency(fcf))
    c3.metric("Shares Out", fmt_currency(shares, decimals=0)[1:] if is_valid(shares) else "N/A")
    c4.metric("Net Debt", fmt_currency(nd))

    if not (is_valid(fcf) and fcf > 0 and is_valid(shares) and shares > 0 and is_valid(price)):
        st.error("⚠️ Insufficient data for DCF. Need positive FCF, share count, and price.")
        return

    render_section("DCF Assumptions")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Cost of Capital**")
        beta_in = st.number_input("Beta", value=safe_float(beta, 1.0), step=0.1, key="vc_b")
        rfr = st.number_input("Risk-Free Rate (%)", value=4.5, step=0.1, key="vc_rfr") / 100
        erp = st.number_input("Equity Risk Premium (%)", value=5.5, step=0.1, key="vc_erp") / 100
        cod = st.number_input("Cost of Debt (%)", value=5.5, step=0.1, key="vc_cod") / 100
        dw = st.slider("Debt Weight", 0.0, 0.6, 0.30, step=0.05, key="vc_dw")
    with c2:
        st.markdown("**Growth Profile**")
        g1 = st.number_input("FCF Growth Y1-3 (%)", value=10.0, step=0.5, key="vc_g1") / 100
        g2 = st.number_input("FCF Growth Y4-7 (%)", value=6.0, step=0.5, key="vc_g2") / 100
        tg = st.number_input("Terminal Growth (%)", value=2.5, step=0.25, key="vc_tg") / 100
        proj_y = st.selectbox("Projection Years", [5, 7, 10], index=1, key="vc_p")
    with c3:
        st.markdown("**Computed**")
        wacc_r = estimate_wacc(beta_in, rfr, erp, dw, cod)
        wacc = wacc_r["wacc"]
        st.metric("Estimated WACC", fmt_pct(wacc))
        st.caption(f"Cost of Equity: {wacc_r['cost_of_equity']*100:.2f}%")
        st.caption(f"After-tax CoD: {wacc_r['after_tax_cod']*100:.2f}%")

    render_section("Base Case Intrinsic Value")
    base_dcf = dcf_fcf(fcf, g1, g2, tg, wacc, proj_y, nd, shares)
    iv = base_dcf.get("intrinsic_value_per_share", 0)
    upside = (iv / price - 1) if price else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Intrinsic Value", fmt_price(iv))
    c2.metric("Current Price", fmt_price(price))
    c3.metric("Implied Return", fmt_pct(upside, signed=True))

    rev = reverse_dcf_fcf(price, fcf, wacc, tg, proj_y, nd, shares)
    impl_g = rev["implied_growth_rate"] * 100
    g_color = NEGATIVE if impl_g > 20 else (UDES_GOLD if impl_g > 10 else POSITIVE)
    st.markdown(f"""
    <div class="alert-box alert-info">
        <strong style="color:{UDES_GOLD}">Reverse DCF:</strong>
        Current price <strong>{fmt_price(price)}</strong> implies
        <span style="color:{g_color};font-weight:700">{impl_g:.1f}% annual FCF growth</span>
        for {proj_y} years.<br>
        <em style="color:{TEXT_MUTED}">{rev.get('assessment', '')}</em>
    </div>
    """, unsafe_allow_html=True)

    render_section("Bull / Base / Bear Scenarios")
    scenarios = scenario_dcf(fcf, wacc, tg, proj_y, nd, shares)
    cols = st.columns(3)
    style_map = {"Bear": (NEGATIVE, "🐻"), "Base": (UDES_GOLD, "📊"), "Bull": (POSITIVE, "🐂")}
    for col, name in zip(cols, ["Bear", "Base", "Bull"]):
        s = scenarios[name]
        color, icon = style_map[name]
        sc_price = s["price_per_share"]
        upside_s = (sc_price / price - 1) if price else 0
        col.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
                    border-top:3px solid {color};border-radius:8px;
                    padding:18px 22px;text-align:center">
            <div style="color:{color};font-size:22px;font-weight:700">{icon} {name} Case</div>
            <div style="color:{TEXT_PRIMARY};font-size:36px;font-weight:800;margin:12px 0">
                {fmt_price(sc_price)}
            </div>
            <div style="color:{color_for_value(upside_s)};font-size:16px;font-weight:600">
                {fmt_pct(upside_s, signed=True)}
            </div>
            <div style="color:{TEXT_MUTED};font-size:11px;margin-top:8px;line-height:1.6">
                Growth: {s['growth']*100:.0f}%<br>
                {s.get('description', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    render_section("Sensitivity Analysis")
    wacc_range = [round(wacc - 0.02, 4), round(wacc - 0.01, 4), round(wacc, 4),
                  round(wacc + 0.01, 4), round(wacc + 0.02, 4)]
    growth_range = [0.0, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20]
    sens_df = sensitivity_table(fcf, wacc_range, growth_range, tg, proj_y, nd, shares)
    st.plotly_chart(sensitivity_heatmap(sens_df, current_price=price,
                                          title="Intrinsic Value Sensitivity (WACC × FCF Growth)"),
                     use_container_width=True)
