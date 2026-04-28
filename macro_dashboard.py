"""
Page 3 — Macro Dashboard
FRED + Bank of Canada indicators, regime scoring, sector impact matrix.

Fixes:
  - render_hero() / render_section() return None — called directly, never wrapped in st.markdown()
  - All sig[] literal subscripts replaced with sig.get() — no KeyError possible
  - Robust to missing FRED key and any missing signal field
"""
import streamlit as st
import pandas as pd

from theme import (UDES_GOLD, UDES_GREEN_DARK, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                   POSITIVE, NEGATIVE, INFO, BG_CARD, BORDER,
                   render_hero, render_section)
from formatting import fmt_pct_raw, fmt_number, is_valid
from macro_data import get_macro_snapshot, compute_macro_regime, SECTOR_MACRO_IMPACT
from charts import macro_indicator_chart


def _value(v, fmt="{:.2f}", suffix=""):
    if not is_valid(v):
        return "N/A"
    try:
        return "{}{}".format(fmt.format(v), suffix)
    except Exception:
        return "N/A"


def render():
    # render_hero() calls st.markdown internally and returns None.
    # NEVER wrap it in st.markdown() — that passes None as the HTML string.
    render_hero(
        "Macro Dashboard",
        "Federal Reserve · Bank of Canada · regime scoring · sector impact",
        "🌍",
    )

    with st.spinner("Fetching macro data (FRED + Bank of Canada)..."):
        try:
            snap = get_macro_snapshot()
            regime = compute_macro_regime(snap)
        except Exception as e:
            st.error(f"Error loading macro data: {e}")
            snap = {}
            regime = {"regime": "Unknown", "score": 50, "color": TEXT_MUTED, "signals": []}

    if not snap.get("fred_available") and not snap.get("boc_available"):
        st.error("⚠️ No macro data available. FRED key missing and Bank of Canada API unreachable.")
        st.info("Add FRED_API_KEY to Streamlit Cloud secrets to enable US data.")
    elif not snap.get("fred_available"):
        st.info("ℹ️ FRED API key not set — US macro data unavailable. Bank of Canada data still active.")

    # ── Regime banner ─────────────────────────────────────────────────────────
    rc = regime.get("color", TEXT_MUTED)
    regime_name = regime.get("regime", "Unknown")
    regime_score = regime.get("score", 50)
    regime_emoji = {
        "Favorable": "🟢", "Neutral": "🟡",
        "Unfavorable": "🟠", "Stress": "🔴",
    }.get(regime_name, "⚪")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {rc}22, {BG_CARD});
                border:1px solid {rc}66; border-radius:12px;
                padding:1.5rem; margin-bottom:1.5rem;">
        <div style="display:flex; align-items:center; gap:2rem; flex-wrap:wrap;">
            <div>
                <p style="color:{TEXT_MUTED}; font-size:0.75rem; margin:0;
                           text-transform:uppercase; letter-spacing:1px;">Macro Regime</p>
                <p style="color:{rc}; font-size:2.2rem; font-weight:900; margin:0;
                           font-family:Merriweather,serif;">
                    {regime_emoji} {regime_name.upper()}
                </p>
            </div>
            <div style="flex:1; min-width:200px;">
                <div style="background:#1F4036; border-radius:6px; height:12px;">
                    <div style="background:{rc}; width:{regime_score}%; height:12px;
                                 border-radius:6px;"></div>
                </div>
                <p style="color:{TEXT_MUTED}; font-size:0.85rem; margin:0.5rem 0 0 0;">
                    Score: <strong style="color:{rc};">{regime_score}/100</strong>
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Signals ───────────────────────────────────────────────────────────────
    # render_section() also returns None — call directly, not via st.markdown()
    render_section("Macro Signals")

    impact_color = {
        "positive":          POSITIVE,
        "slightly_positive": "#86EFAC",
        "neutral":           TEXT_MUTED,
        "mixed":             TEXT_MUTED,
        "slightly_negative": "#FCA5A5",
        "negative":          NEGATIVE,
        "highly_positive":   POSITIVE,
        "highly_negative":   NEGATIVE,
    }

    signals = regime.get("signals") or []
    if not signals:
        st.info("No macro signals available — try adding a FRED API key.")
    else:
        for sig in signals:
            # All access via .get() — no KeyError possible regardless of dict shape
            sig_impact = sig.get("impact") or "neutral"
            sig_name   = sig.get("indicator") or sig.get("name") or "N/A"
            sig_note   = sig.get("note") or ""
            sig_value  = sig.get("value") or "N/A"

            color = impact_color.get(sig_impact, TEXT_MUTED)
            impact_lower = sig_impact.lower()
            if "positive" in impact_lower:
                icon = "✅"
            elif "negative" in impact_lower:
                icon = "🔴"
            else:
                icon = "⚪"

            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:1rem;
                        background:{BG_CARD}; border-left:3px solid {color};
                        padding:0.7rem 1rem; border-radius:0 8px 8px 0; margin:0.3rem 0;">
                <span style="font-size:1.1rem;">{icon}</span>
                <div style="flex:1;">
                    <span style="color:{TEXT_PRIMARY}; font-weight:600; font-size:0.9rem;">
                        {sig_name}
                    </span>
                    <span style="color:{TEXT_SECONDARY}; font-size:0.85rem;">
                         — {sig_note}
                    </span>
                </div>
                <span style="color:{color}; font-weight:700; font-size:0.95rem;
                             min-width:80px; text-align:right;">
                    {sig_value}
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ── Key Indicators Tabs ───────────────────────────────────────────────────
    render_section("Key Indicators")

    tabs = st.tabs(["🇨🇦 Canada", "🇺🇸 United States", "📈 Rates & FX", "🛢️ Commodities"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("BoC Policy Rate", _value(snap.get("boc_policy_rate"), "{:.2f}", "%"))
        c2.metric("CA 10Y Yield",    _value(snap.get("ca_10y_yield"),    "{:.2f}", "%"))
        c3.metric("CA 2Y Yield",     _value(snap.get("ca_2y_yield"),     "{:.2f}", "%"))

        ca_curve = snap.get("ca_yield_curve")
        if is_valid(ca_curve):
            color = POSITIVE if ca_curve > 0 else NEGATIVE
            st.markdown(
                f'<p style="color:{color}; font-weight:600;">'
                f'Canada Yield Curve (10Y-2Y): {_value(ca_curve, "{:.2f}", "%")}'
                f'</p>',
                unsafe_allow_html=True,
            )

        boc_series = snap.get("boc_policy_rate_series")
        if boc_series is not None and not boc_series.empty:
            try:
                st.plotly_chart(
                    macro_indicator_chart(boc_series.tail(120),
                                          "Bank of Canada Policy Rate (%)",
                                          color=UDES_GOLD),
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Chart unavailable: {e}")
        st.caption("Source: Bank of Canada Valet API")

    with tabs[1]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fed Funds Rate", _value(snap.get("fed_funds_rate"),   "{:.2f}", "%"))
        c2.metric("US CPI YoY",     _value(snap.get("us_cpi_yoy"),       "{:.1f}", "%"))
        c3.metric("Unemployment",    _value(snap.get("us_unemployment"),  "{:.1f}", "%"))
        c4.metric("Consumer Conf",   _value(snap.get("us_consumer_conf"), "{:.1f}"))

        if not snap.get("fred_available"):
            st.warning("US data unavailable — add FRED_API_KEY to Streamlit secrets.")
        else:
            fed_series = snap.get("fed_funds_rate_series")
            if fed_series is not None and not fed_series.empty:
                try:
                    st.plotly_chart(
                        macro_indicator_chart(fed_series.tail(120),
                                              "US Federal Funds Rate (%)",
                                              color=POSITIVE),
                        use_container_width=True,
                    )
                except Exception as e:
                    st.caption(f"Chart unavailable: {e}")
        st.caption("Source: Federal Reserve Economic Data (FRED) — requires API key")

    with tabs[2]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("US 10Y Yield",   _value(snap.get("us_10y_yield"), "{:.2f}", "%"))
        c2.metric("US 2Y Yield",    _value(snap.get("us_2y_yield"),  "{:.2f}", "%"))
        yc = snap.get("us_yield_curve")
        c3.metric("US Yield Curve", _value(yc, "{:.2f}", "%"))
        cad = snap.get("cad_usd")
        c4.metric("USD/CAD",        _value(cad, "{:.4f}"))

        cad_series = snap.get("cad_usd_series")
        if cad_series is not None and not cad_series.empty:
            try:
                st.plotly_chart(
                    macro_indicator_chart(cad_series.tail(120),
                                          "USD/CAD Exchange Rate",
                                          color=INFO),
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Chart unavailable: {e}")
        st.caption("Source: FRED (US yields) · Bank of Canada (CAD/USD)")

    with tabs[3]:
        c1, c2 = st.columns(2)
        c1.metric("WTI Crude Oil", _value(snap.get("wti_oil"), "${:.2f}"))
        rs = snap.get("us_retail_sales")
        c2.metric("US Retail Sales", "${:,.0f}M".format(rs) if is_valid(rs) else "N/A")

        wti_series = snap.get("wti_oil_series")
        if wti_series is not None and not wti_series.empty:
            try:
                st.plotly_chart(
                    macro_indicator_chart(wti_series.tail(120),
                                          "WTI Crude Oil (USD/barrel)",
                                          color="#F97316"),
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Chart unavailable: {e}")
        st.caption("Source: FRED (WTI, retail sales)")

    # ── Sector Impact Matrix ──────────────────────────────────────────────────
    render_section("Sector Impact Matrix")
    st.caption("How current macro conditions may affect each sector — illustrative framework.")

    impact_pill = {
        "positive": ("🟢", POSITIVE),
        "negative": ("🔴", NEGATIVE),
        "neutral":  ("⚪", TEXT_MUTED),
    }

    for sector, impacts in SECTOR_MACRO_IMPACT.items():
        note = impacts.get("note", "")
        factors = {k: v for k, v in impacts.items() if k != "note"}
        chips = []
        for factor, impact in factors.items():
            icon, color = impact_pill.get(impact, ("⚪", TEXT_MUTED))
            label = factor.replace("_", " ").title()
            chips.append(
                f'<span class="pill" style="color:{color}; border-color:{color}66;'
                f'background:{color}11;">{icon} {label}</span>'
            )
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER};
                    border-radius:10px; padding:0.8rem 1rem; margin:0.4rem 0;">
            <div style="display:flex; gap:1rem; align-items:center; flex-wrap:wrap;">
                <div style="min-width:200px;">
                    <strong style="color:{UDES_GOLD};">{sector}</strong><br>
                    <span style="color:{TEXT_MUTED}; font-size:0.78rem;">{note}</span>
                </div>
                <div style="display:flex; gap:0.4rem; flex-wrap:wrap; flex:1;">
                    {''.join(chips)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.caption(f"Last updated: {snap.get('last_updated', 'N/A')} · Source: FRED + Bank of Canada Valet")
