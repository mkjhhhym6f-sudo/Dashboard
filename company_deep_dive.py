"""
Page 4 — Company Deep Dive
FIEUS Analytics — Fonds d'investissement étudiant de l'Université de Sherbrooke

Data hierarchy: manual_fundamentals.csv / manual_valuation.csv > yfinance
Analyst thesis: manual_targets.csv
Prices / returns / risk: yfinance
"""
import streamlit as st
import pandas as pd
import numpy as np

from theme import (UDES_GOLD, UDES_GREEN_DARK, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                   POSITIVE, NEGATIVE, NEUTRAL, INFO, BG_CARD, BORDER,
                   render_hero, render_section, rec_badge,
                   color_for_value, color_for_score, color_for_recommendation)
from formatting import (fmt_pct, fmt_multiple, fmt_large, fmt_price,
                        fmt_number, is_valid, safe_float)
from market_data import (load_universe, fetch_fundamentals, fetch_price_history,
                         calculate_returns, calculate_risk_metrics,
                         get_data_source_label, SRC_YF, SRC_CIQ, SRC_FIEUS, SRC_PREMIUM)
from scoring import compute_composite_score, SECTOR_BENCHMARKS
from valuation import estimate_wacc, dcf_fcf, reverse_dcf_fcf, scenario_dcf, sensitivity_table
from charts import price_chart, returns_bar, gauge_chart, sensitivity_heatmap


def _src_badge(label: str) -> str:
    """Tiny inline source badge."""
    colors = {
        SRC_CIQ:     ("#00B4D8", "#00B4D811"),
        SRC_FIEUS:   (UDES_GOLD, UDES_GOLD + "11"),
        SRC_YF:      (NEUTRAL, "#94A3B811"),
        SRC_PREMIUM: (NEGATIVE, "#EF444411"),
    }
    c, bg = colors.get(label, (NEUTRAL, "#94A3B811"))
    return (f'<span style="font-size:9px;font-weight:600;color:{c};'
            f'background:{bg};border:1px solid {c}44;border-radius:3px;'
            f'padding:1px 5px;margin-left:4px;">{label}</span>')


def render():
    # render_hero() calls st.markdown internally and returns None — do NOT wrap in st.markdown
    render_hero(
        "Company Deep Dive",
        "Snapshot · business · financials · score · valuation · thesis",
        "🔍",
    )

    universe = load_universe()
    if universe.empty:
        st.error("Universe not available.")
        return

    equities = universe[universe["is_etf"] == False]
    name_map = {r["ticker"]: f"{r['ticker']} — {r['name']}"
                for _, r in equities.iterrows()}

    c1, c2 = st.columns([3, 1])
    with c1:
        selected = st.selectbox(
            "Select Company",
            options=equities["ticker"].tolist(),
            format_func=lambda x: name_map.get(x, x),
        )
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not selected:
        return

    meta = universe[universe["ticker"] == selected].iloc[0].to_dict()
    sector = meta.get("sector", "Default")

    with st.spinner(f"Loading {selected}..."):
        fund = fetch_fundamentals(selected)
        prices_df = fetch_price_history(selected, period="5y")
        prices = (prices_df["Close"]
                  if not prices_df.empty and "Close" in prices_df.columns
                  else pd.Series(dtype=float))
        rets = calculate_returns(prices) if not prices.empty else {}
        risk = calculate_risk_metrics(prices) if not prices.empty else {}

    score = compute_composite_score(fund, rets, sector, "Neutral", False)

    # ── Source summary banner ────────────────────────────────────────────────
    has_mf  = fund.get("has_manual_fundamentals", False)
    has_mv  = fund.get("has_manual_valuation", False)
    has_mt  = fund.get("has_manual_targets", False)
    mf_src  = fund.get("manual_fund_source") or SRC_CIQ
    mf_date = fund.get("manual_fund_last_update") or ""
    mv_date = fund.get("manual_val_last_update") or ""

    if not has_mf and not has_mv:
        st.info(
            "ℹ️ **Fundamental data not yet available from manual CSV.**  "
            "Fill `config/manual_fundamentals.csv` and `config/manual_valuation.csv` "
            "from Capital IQ or FIEUS to see complete financials. "
            "Currently showing yfinance market data only (may be N/A for TSX stocks)."
        )
    else:
        badges = []
        if has_mf:
            badges.append(f"✅ Fundamentals: {mf_src}" + (f" · {mf_date}" if mf_date else ""))
        if has_mv:
            badges.append(f"✅ Valuation: {mv_date or mf_src}")
        if has_mt:
            badges.append("✅ Analyst thesis: FIEUS manual")
        st.success("  |  ".join(badges))

    # ════════════════════════════════════════════════════════════════════════
    # A · SNAPSHOT
    # ════════════════════════════════════════════════════════════════════════
    render_section("A · Snapshot")

    name = fund.get("name") or meta.get("name", selected)
    price = fund.get("price")
    prev  = fund.get("prev_close")
    day_chg_pct = ((price / prev) - 1) if is_valid(price) and is_valid(prev) and prev > 0 else None

    rec       = score["recommendation"]
    rec_color = color_for_recommendation(rec)

    # Header card
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{UDES_GREEN_DARK},{BG_CARD});
                border:1px solid {UDES_GOLD}44;border-radius:12px;
                padding:1.2rem 1.5rem;margin-bottom:1rem;">
        <div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
                <p style="color:{TEXT_MUTED};font-size:0.8rem;margin:0;text-transform:uppercase;">
                    {selected} · {meta.get('market','TSX')}
                </p>
                <p style="color:{UDES_GOLD};font-size:1.5rem;font-weight:900;
                           margin:0.2rem 0;font-family:Merriweather,serif;">
                    {name}
                </p>
                <p style="color:{TEXT_SECONDARY};font-size:0.85rem;margin:0;">
                    {sector} · {meta.get('subsector','') or meta.get('industry','')}
                </p>
            </div>
            <div style="text-align:right;">
                <p style="color:{TEXT_PRIMARY};font-size:2rem;font-weight:900;margin:0;
                           font-family:Merriweather,serif;">
                    {fmt_price(price)}
                </p>
                <p style="color:{color_for_value(day_chg_pct)};font-size:0.95rem;
                           font-weight:600;margin:0;">
                    {fmt_pct(day_chg_pct,signed=True)} today
                </p>
                <p style="color:{TEXT_MUTED};font-size:9px;margin:2px 0 0 0;">Source: {SRC_YF}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI grid — show source per metric
    def _metric_with_src(col_obj, label, value, metric_key):
        src = get_data_source_label(fund, metric_key)
        src_note = f"Source: {src}" if value and value != "N/A" else SRC_PREMIUM
        col_obj.metric(label, value, help=src_note)

    cols = st.columns(6)
    _metric_with_src(cols[0], "Market Cap",  fmt_large(fund.get("market_cap")),   "market_cap")
    _metric_with_src(cols[1], "EV",          fmt_large(fund.get("enterprise_value")), "enterprise_value")
    cols[2].metric("Beta",       fmt_number(fund.get("beta")),   help=f"Source: {SRC_YF}")
    cols[3].metric("Volatility", fmt_pct(risk.get("volatility_ann")), help=f"Calculated from {SRC_YF} prices")
    cols[4].metric("DD from 52W", fmt_pct(risk.get("current_drawdown_from_52w"), signed=True),
                   help=f"Calculated from {SRC_YF} prices")
    _metric_with_src(cols[5], "Div Yield", fmt_pct(fund.get("dividend_yield")), "dividend_yield")

    # FIEUS Screening Score banner
    score_color = color_for_score(score["total"])
    score_disp  = f"{score['total']:.0f}/100" if is_valid(score["total"]) else "N/A"
    partial_note = "" if (has_mf and has_mv) else " (partial — limited input data)"
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {score_color}66;
                border-left:4px solid {score_color};
                border-radius:10px;padding:1rem 1.3rem;margin:0.8rem 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;
                    flex-wrap:wrap;gap:1rem;">
            <div>
                <p style="color:{TEXT_MUTED};font-size:0.75rem;margin:0;text-transform:uppercase;">
                    FIEUS Screening Score{partial_note}
                </p>
                <p style="color:{score_color};font-size:2.2rem;font-weight:900;margin:0.2rem 0;
                           font-family:Merriweather,serif;">
                    {score_disp}
                </p>
                <p style="color:{TEXT_MUTED};font-size:0.72rem;margin:0;">
                    Preliminary screening signal — not a final investment recommendation.
                    Verify with Capital IQ and FIEUS research.
                </p>
            </div>
            <div>{rec_badge(rec)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not prices.empty:
        st.plotly_chart(price_chart(prices, selected), use_container_width=True)
        st.caption(f"Source: {SRC_YF} adjusted close · 5-year history")
    if rets:
        st.plotly_chart(returns_bar(rets, selected), use_container_width=True)
        st.caption(f"Source: Calculated from {SRC_YF} adjusted close prices")

    # ════════════════════════════════════════════════════════════════════════
    # B · BUSINESS OVERVIEW
    # ════════════════════════════════════════════════════════════════════════
    render_section("B · Business Overview")

    desc = fund.get("description") or "Business description not available from yfinance."
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};
                border-radius:10px;padding:1rem 1.3rem;">
        <p style="color:{TEXT_PRIMARY};line-height:1.7;font-size:0.92rem;">
            {str(desc)[:1000]}{'...' if len(str(desc)) > 1000 else ''}
        </p>
    </div>
    """, unsafe_allow_html=True)

    chips = [
        ("Industry",  fund.get("industry") or meta.get("industry") or "N/A"),
        ("Employees", f"{fund.get('employees'):,}" if is_valid(fund.get("employees")) else "N/A"),
        ("Country",   fund.get("country") or meta.get("country") or "N/A"),
        ("Currency",  fund.get("currency") or meta.get("currency", "CAD")),
    ]
    chip_html = " ".join([f"""
    <span class="pill" style="color:{UDES_GOLD};border-color:{UDES_GOLD}66;
                              background:{UDES_GOLD}11;margin-right:0.4rem;">
        <strong style="color:{TEXT_MUTED};">{lbl}:</strong> {val}
    </span>""" for lbl, val in chips])
    st.markdown(f'<div style="margin-top:0.8rem;">{chip_html}</div>',
                unsafe_allow_html=True)
    st.caption(f"Source: {SRC_YF}")

    # ════════════════════════════════════════════════════════════════════════
    # C · FINANCIALS
    # ════════════════════════════════════════════════════════════════════════
    render_section("C · Financials")

    fund_src_note = (f"Source: {mf_src}" + (f" · {mf_date}" if mf_date else "")
                     if has_mf else f"Source: {SRC_YF} (limited for TSX stocks)")

    if not has_mf and not has_mv:
        st.warning(
            "Fundamental data unavailable from current CSV/manual source. "
            "Fill `config/manual_fundamentals.csv` from Capital IQ or company filings."
        )

    tabs = st.tabs(["📊 Profitability", "💵 Cash Flow", "🏦 Balance Sheet", "📈 Multiples"])

    with tabs[0]:
        cols = st.columns(3)
        cols[0].metric("Gross Margin",     fmt_pct(fund.get("gross_margin")))
        cols[1].metric("EBITDA Margin",    fmt_pct(fund.get("ebitda_margin")))
        cols[2].metric("Operating Margin", fmt_pct(fund.get("operating_margin")))
        cols = st.columns(3)
        cols[0].metric("Net Margin", fmt_pct(fund.get("profit_margin")))
        cols[1].metric("ROE",        fmt_pct(fund.get("roe")))
        cols[2].metric("ROIC",       fmt_pct(fund.get("roic")))
        st.caption(fund_src_note)

    with tabs[1]:
        rev = fund.get("revenue_ttm")
        ocf = fund.get("operating_cashflow")
        fcf = fund.get("fcf") or fund.get("free_cash_flow")
        cols = st.columns(4)
        cols[0].metric("Revenue (TTM)",  fmt_large(rev))
        cols[1].metric("Op Cash Flow",   fmt_large(ocf))
        cols[2].metric("Free Cash Flow", fmt_large(fcf))
        fcf_margin = fcf / rev if is_valid(fcf) and is_valid(rev) and rev > 0 else None
        cols[3].metric("FCF Margin",     fmt_pct(fcf_margin))
        st.caption(fund_src_note + " · FCF Margin = FCF / Revenue (calculated)")

    with tabs[2]:
        cols = st.columns(4)
        cols[0].metric("Cash",       fmt_large(fund.get("cash")))
        cols[1].metric("Total Debt", fmt_large(fund.get("total_debt")))
        cols[2].metric("Net Debt",   fmt_large(fund.get("net_debt")))
        nd = fund.get("net_debt")
        eb = fund.get("ebitda")
        nde = nd / eb if is_valid(nd) and is_valid(eb) and eb > 0 else fund.get("net_debt_ebitda")
        cols[3].metric("ND/EBITDA",  fmt_multiple(nde))
        cols = st.columns(2)
        cols[0].metric("Current Ratio", fmt_number(fund.get("current_ratio")))
        cols[1].metric("Quick Ratio",   fmt_number(fund.get("quick_ratio")))
        st.caption(fund_src_note)

    with tabs[3]:
        val_src_note = (f"Source: {mv_date or mf_src}" if (has_mv or has_mf)
                        else f"Source: {SRC_YF} (limited for TSX stocks)")
        cols = st.columns(4)
        cols[0].metric("P/E (TTM)",  fmt_multiple(fund.get("pe_trailing")))
        cols[1].metric("P/E (Fwd)",  fmt_multiple(fund.get("pe_forward")))
        cols[2].metric("EV/EBITDA",  fmt_multiple(fund.get("ev_ebitda")))
        cols[3].metric("EV/Revenue", fmt_multiple(fund.get("ev_revenue") or fund.get("ev_sales")))
        cols = st.columns(4)
        cols[0].metric("P/B",      fmt_multiple(fund.get("pb_ratio")))
        cols[1].metric("P/Sales",  fmt_multiple(fund.get("ps_ratio") or fund.get("price_sales")))
        cols[2].metric("FCF Yield",fmt_pct(fund.get("fcf_yield")))
        cols[3].metric("Div Yield",fmt_pct(fund.get("dividend_yield")))
        st.caption(val_src_note)

    # ════════════════════════════════════════════════════════════════════════
    # D · SCORE BREAKDOWN
    # ════════════════════════════════════════════════════════════════════════
    render_section("D · Score Breakdown")

    st.caption(
        "FIEUS composite scoring model: Quality 25% · Valuation 25% · Growth 20% · "
        "Balance Sheet 15% · Momentum 10% · Macro Fit 5%  —  "
        "**Preliminary screening signal only. Not a final investment decision.**"
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if is_valid(score["total"]):
            st.plotly_chart(gauge_chart(score["total"], "FIEUS Screening Score"),
                            use_container_width=True)
        else:
            st.info("Score unavailable — insufficient input data.")
    with c2:
        sub = score["sub_scores"]
        weights = {"quality": 25, "valuation": 25, "growth": 20,
                   "balance_sheet": 15, "momentum": 10, "macro_fit": 5}
        for key, w in weights.items():
            v = sub.get(key, {}).get("score", 0)
            color = color_for_score(v)
            label = key.replace("_", " ").title()
            st.markdown(f"""
            <div style="margin-bottom:0.7rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                    <span style="color:{TEXT_PRIMARY};font-size:0.85rem;">
                        {label}
                        <span style="color:{TEXT_MUTED};font-size:0.75rem;">({w}%)</span>
                    </span>
                    <span style="color:{color};font-weight:700;font-size:0.85rem;">{v}/100</span>
                </div>
                <div style="background:{BORDER};border-radius:4px;height:6px;">
                    <div style="background:{color};width:{v}%;height:6px;border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if score["top_drivers"] or score["top_risks"]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<p style="color:{POSITIVE};font-weight:700;">✅ Drivers</p>',
                        unsafe_allow_html=True)
            for d in score["top_drivers"]:
                st.markdown(f'<div class="alert alert-success">{d}</div>',
                            unsafe_allow_html=True)
        with c2:
            st.markdown(f'<p style="color:{NEGATIVE};font-weight:700;">⚠️ Risks</p>',
                        unsafe_allow_html=True)
            for r in score["top_risks"]:
                st.markdown(f'<div class="alert alert-warning">{r}</div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # E · VALUATION (DCF)
    # ════════════════════════════════════════════════════════════════════════
    render_section("E · Valuation (DCF & Reverse DCF)")

    fcf    = fund.get("fcf") or fund.get("free_cash_flow")
    shares = fund.get("shares_outstanding")
    nd_val = fund.get("net_debt") or 0
    fcf_src = get_data_source_label(fund, "fcf")
    shr_src = get_data_source_label(fund, "shares_outstanding")

    if not (is_valid(fcf) and fcf > 0 and is_valid(shares) and shares > 0 and is_valid(price)):
        st.warning(
            f"⚠️ Insufficient data for DCF. Need positive FCF and share count.  \n"
            f"FCF: {fmt_large(fcf)} (source: {fcf_src}) · "
            f"Shares: {fmt_large(shares)} (source: {shr_src})  \n"
            f"Go to **Valuation Center** to enter manual assumptions."
        )
    else:
        st.caption(f"FCF source: {fcf_src} · Shares source: {shr_src}")

        with st.expander("⚙️ DCF Assumptions", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                beta_in = st.number_input("Beta", value=float(fund.get("beta") or 1.0),
                                           step=0.1, key=f"dd_beta_{selected}")
                rf_in   = st.number_input("Risk-Free Rate (%)", value=4.0,
                                           step=0.1, key=f"dd_rf_{selected}") / 100
            with c2:
                erp_in  = st.number_input("Equity Risk Premium (%)", value=5.5,
                                           step=0.1, key=f"dd_erp_{selected}") / 100
                tg_in   = st.number_input("Terminal Growth (%)", value=2.5,
                                           step=0.1, key=f"dd_tg_{selected}") / 100
            with c3:
                dw_in   = st.slider("Debt Weight", 0.0, 0.6, 0.30,
                                     step=0.05, key=f"dd_dw_{selected}")
                yrs_in  = st.selectbox("Projection Years", [5, 7, 10], index=2,
                                        key=f"dd_yrs_{selected}")

        wacc_r = estimate_wacc(beta_in, rf_in, erp_in, dw_in, 0.055, 0.265)
        wacc   = wacc_r["wacc"]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};
                        border-radius:10px;padding:1rem;">
                <p style="color:{TEXT_MUTED};font-size:0.75rem;margin:0;text-transform:uppercase;">
                    Estimated WACC
                </p>
                <p style="color:{UDES_GOLD};font-size:2rem;font-weight:900;
                           margin:0.2rem 0;font-family:Merriweather,serif;">
                    {wacc*100:.2f}%
                </p>
                <p style="color:{TEXT_SECONDARY};font-size:0.78rem;margin:0;">
                    Cost of equity: {wacc_r['cost_of_equity']*100:.2f}%
                    · After-tax CoD: {wacc_r['after_tax_cod']*100:.2f}%
                </p>
                <p style="color:{TEXT_MUTED};font-size:9px;margin-top:4px;">
                    Source: FIEUS manual assumptions (CAPM)
                </p>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            rev_dcf = reverse_dcf_fcf(price, fcf, wacc, tg_in, yrs_in, nd_val, shares)
            if is_valid(rev_dcf["implied_growth_rate"]):
                g_pct   = rev_dcf["implied_annual_growth_pct"]
                g_color = NEGATIVE if g_pct > 20 else "#F59E0B" if g_pct > 10 else POSITIVE
                st.markdown(f"""
                <div class="alert alert-info">
                    <strong>Reverse DCF</strong><br>
                    Current price implies
                    <span style="color:{g_color};font-weight:700;">{g_pct:.1f}% annual FCF growth</span>
                    for {yrs_in} years.<br>
                    <em>{rev_dcf['assessment']}</em><br>
                    <span style="font-size:9px;color:{TEXT_MUTED};">
                        Based on {fcf_src} FCF inputs — verify before use.
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # Scenario Analysis
        st.markdown('<p style="font-weight:600;margin-top:1rem;">Scenario Analysis</p>',
                    unsafe_allow_html=True)
        scenarios = scenario_dcf(fcf, wacc, tg_in, yrs_in, nd_val, shares)
        cols = st.columns(3)
        for col, (sc_name, sc) in zip(cols, scenarios.items()):
            implied_ret = (
                ((sc["price_per_share"] / price) - 1) * 100
                if is_valid(sc["price_per_share"]) and is_valid(price) and price > 0
                else None
            )
            ret_str = f"{implied_ret:+.1f}% upside" if is_valid(implied_ret) else ""
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

        # Sensitivity table
        st.markdown('<p style="font-weight:600;margin-top:1rem;">Sensitivity: WACC vs Growth</p>',
                    unsafe_allow_html=True)
        wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
        g_range    = [0.03, 0.05, 0.08, 0.12, 0.18]
        try:
            sens_df = sensitivity_table(fcf, wacc_range, g_range, tg_in, yrs_in, nd_val, shares)
            fig_sens = sensitivity_heatmap(sens_df, current_price=price,
                                            title="DCF Sensitivity (Implied Price per Share)")
            st.plotly_chart(fig_sens, use_container_width=True)
        except Exception:
            pass
        st.caption(
            f"DCF uses {fcf_src} FCF = {fmt_large(fcf)}, "
            f"{shr_src} shares = {fmt_large(shares)}, "
            f"net debt = {fmt_large(nd_val)}. "
            "All DCF assumptions are manual inputs — verify independently."
        )

    # ════════════════════════════════════════════════════════════════════════
    # F · INVESTMENT THESIS  (from manual_targets.csv, not analyst_coverage.csv)
    # ════════════════════════════════════════════════════════════════════════
    render_section("F · Investment Thesis")

    # fund dict now contains thesis fields from manual_targets.csv via market_data.py
    analyst_name  = fund.get("analyst") or "TBD"
    recommendation = fund.get("recommendation") or "N/A"
    tp            = fund.get("target_price")
    thesis_status = fund.get("thesis_status") or "N/A"
    priority      = fund.get("priority") or "N/A"
    next_earn     = fund.get("next_earnings") or "N/A"
    bull          = fund.get("bull_case") or "Not documented."
    base          = fund.get("base_case") or "Not documented."
    bear          = fund.get("bear_case") or "Not documented."
    risks         = fund.get("key_risks") or "Not documented."
    metrics_watch = fund.get("key_metrics_to_watch") or "Not documented."

    if not has_mt:
        st.info(
            "No analyst thesis yet. "
            "Fill `config/manual_targets.csv` or use the **Analyst Center** to add coverage."
        )
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            tp_str = f"${tp:.2f}" if is_valid(tp) else "N/A"
            # Implied upside
            upside_str = ""
            if is_valid(tp) and is_valid(price) and price > 0:
                upside = (tp / price - 1) * 100
                upside_color = POSITIVE if upside >= 0 else NEGATIVE
                upside_str = (f'<span style="color:{upside_color};font-weight:700;">'
                              f'{upside:+.1f}%</span>')

            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};
                        border-radius:10px;padding:1.2rem;">
                <div style="display:flex;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.8rem;">
                    <span class="pill" style="color:{INFO};border-color:{INFO}66;background:{INFO}11;">
                        Analyst: {analyst_name}
                    </span>
                    {rec_badge(recommendation)}
                    <span class="pill" style="color:{UDES_GOLD};border-color:{UDES_GOLD}66;background:{UDES_GOLD}11;">
                        Target: {tp_str} {upside_str}
                    </span>
                    <span class="pill" style="color:{TEXT_SECONDARY};border-color:{BORDER};background:{BG_CARD};">
                        Status: {thesis_status}
                    </span>
                    <span class="pill" style="color:{TEXT_SECONDARY};border-color:{BORDER};background:{BG_CARD};">
                        Priority: {priority}
                    </span>
                </div>
                <p style="color:{TEXT_MUTED};font-size:9px;margin-bottom:8px;">
                    Source: FIEUS manual · Not a final investment recommendation ·
                    Subject to FIEUS investment committee review
                </p>
                <p style="color:{TEXT_PRIMARY};line-height:1.7;margin:0.5rem 0;">
                    <strong style="color:{POSITIVE};">Bull:</strong> {bull}
                </p>
                <p style="color:{TEXT_PRIMARY};line-height:1.7;margin:0.5rem 0;">
                    <strong style="color:{UDES_GOLD};">Base:</strong> {base}
                </p>
                <p style="color:{TEXT_PRIMARY};line-height:1.7;margin:0.5rem 0;">
                    <strong style="color:{NEGATIVE};">Bear:</strong> {bear}
                </p>
                <p style="color:{TEXT_SECONDARY};line-height:1.6;margin:0.5rem 0;">
                    <strong style="color:{NEGATIVE};">Key Risks:</strong> {risks}
                </p>
                <p style="color:{TEXT_SECONDARY};line-height:1.6;margin:0.5rem 0;">
                    <strong style="color:{UDES_GOLD};">Watch:</strong> {metrics_watch}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            last_upd = fund.get("manual_fund_last_update") or "N/A"
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};
                        border-radius:10px;padding:1rem;">
                <p style="color:{TEXT_MUTED};font-size:0.75rem;margin:0;text-transform:uppercase;">
                    Next Earnings
                </p>
                <p style="color:{TEXT_PRIMARY};font-size:1.05rem;font-weight:600;margin:0.2rem 0;">
                    {next_earn}
                </p>
                <hr style="border-color:{BORDER};margin:0.7rem 0;">
                <p style="color:{TEXT_MUTED};font-size:0.75rem;margin:0;text-transform:uppercase;">
                    Last CSV Update
                </p>
                <p style="color:{TEXT_PRIMARY};font-size:0.95rem;margin:0.2rem 0;">
                    {last_upd}
                </p>
                <hr style="border-color:{BORDER};margin:0.7rem 0;">
                <p style="color:{TEXT_MUTED};font-size:9px;line-height:1.5;margin:0;">
                    Source: FIEUS manual_targets.csv<br>
                    Analyst view — not investment advice.<br>
                    Requires FIEUS investment committee approval.
                </p>
            </div>
            """, unsafe_allow_html=True)
