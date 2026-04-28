"""analyst_center.py — Page 8: Manage analyst coverage, theses, and notes.
Reads/writes config/analyst_coverage.csv directly.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from theme import (render_hero, render_section, rec_badge,
                    UDES_GOLD, POSITIVE, NEGATIVE, NEUTRAL,
                    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER)
from market_data import load_universe, load_analyst_coverage
from formatting import is_valid

ROOT = Path(__file__).parent
COVERAGE_CSV = ROOT / "config" / "analyst_coverage.csv"


def _save_coverage(df: pd.DataFrame) -> bool:
    try:
        df.to_csv(COVERAGE_CSV, index=False)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


def render():
    render_hero("Analyst Center",
                 "Manage coverage · Update theses · Track recommendations",
                 "👤")

    universe = load_universe()
    coverage = load_analyst_coverage()
    if universe.empty:
        st.error("Could not load universe.csv")
        return

    companies = universe[~universe["is_etf"]].copy()
    tabs = st.tabs(["📊 Coverage Dashboard", "📝 Edit Coverage", "🆕 Add Coverage"])

    # ── Tab 1: Dashboard ────────────────────────────────────────────────────
    with tabs[0]:
        if coverage.empty:
            st.info("No coverage yet. Use 'Add Coverage' tab to start.")
        else:
            n_total = len(coverage)
            recs_col = coverage.get("recommendation", pd.Series(dtype=str)).str.upper()
            n_buy = int((recs_col == "BUY").sum())
            n_hold = int((recs_col == "HOLD").sum())
            n_sell = int((recs_col == "SELL").sum())
            n_orphan = max(len(companies) - n_total, 0)

            c1, c2, c3, c4, c5 = st.columns(5)
            for col, (label, val, color) in zip(
                [c1, c2, c3, c4, c5],
                [("Coverage", n_total, TEXT_PRIMARY), ("BUY", n_buy, POSITIVE),
                 ("HOLD", n_hold, UDES_GOLD), ("SELL", n_sell, NEGATIVE),
                 ("Uncovered", n_orphan, NEUTRAL)]
            ):
                col.markdown(f"""
                <div style="background:{BG_CARD};border:1px solid {BORDER};
                            border-radius:10px;padding:12px 16px">
                    <div style="color:{TEXT_MUTED};font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase">{label}</div>
                    <div style="color:{color};font-size:24px;font-weight:700;margin-top:4px">{val}</div>
                </div>
                """, unsafe_allow_html=True)

            render_section("Coverage Table")
            display_cols = ["ticker", "analyst_name", "recommendation",
                             "target_price_cad", "status", "last_update", "next_earnings"]
            avail = [c for c in display_cols if c in coverage.columns]
            st.dataframe(coverage[avail], use_container_width=True, hide_index=True)

            if n_orphan > 0:
                render_section("Uncovered Companies")
                covered_set = set(coverage["ticker"].tolist())
                uncovered = [t for t in companies["ticker"].tolist() if t not in covered_set]
                for t in uncovered:
                    name = companies[companies["ticker"] == t]["name"].iloc[0]
                    st.markdown(f"""
                    <div style="background:{BG_CARD};border-left:3px solid {NEUTRAL};
                                border-radius:6px;padding:8px 14px;margin:4px 0">
                        <span style="color:{UDES_GOLD};font-weight:600">{t}</span>
                        <span style="color:{TEXT_MUTED};margin-left:10px">{name}</span>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Tab 2: Edit ────────────────────────────────────────────────────────
    with tabs[1]:
        if coverage.empty:
            st.info("No coverage to edit yet.")
        else:
            ticker_to_edit = st.selectbox("Select company to edit",
                                            options=coverage["ticker"].tolist(),
                                            key="edit_select")
            cov_row = coverage[coverage["ticker"] == ticker_to_edit].iloc[0]

            with st.form(f"edit_form_{ticker_to_edit}"):
                c1, c2 = st.columns(2)
                with c1:
                    analyst_name = st.text_input("Analyst",
                                                   value=str(cov_row.get("analyst_name", "") or ""))
                    role = st.text_input("Role", value=str(cov_row.get("role", "") or ""))
                    rec_options = ["BUY", "HOLD", "SELL", "WATCHLIST"]
                    cur_rec = str(cov_row.get("recommendation", "HOLD") or "HOLD").upper()
                    rec = st.selectbox("Recommendation", options=rec_options,
                                        index=rec_options.index(cur_rec) if cur_rec in rec_options else 1)
                    tp_v = cov_row.get("target_price_cad")
                    tp = st.number_input("Target Price (CAD)",
                                          value=float(tp_v) if is_valid(tp_v) else 0.0, step=1.0)
                with c2:
                    status_options = ["À jour", "À revoir", "Nouveau", "Suspendu"]
                    cur_status = str(cov_row.get("status", "À jour") or "À jour")
                    status = st.selectbox("Status", options=status_options,
                                           index=status_options.index(cur_status) if cur_status in status_options else 0)
                    next_e = st.text_input("Next Earnings (YYYY-MM-DD)",
                                             value=str(cov_row.get("next_earnings", "") or ""))

                thesis = st.text_area("Thesis Summary",
                                        value=str(cov_row.get("thesis_summary", "") or ""), height=120)
                risks = st.text_area("Key Risks",
                                       value=str(cov_row.get("key_risks", "") or ""), height=80)
                notes = st.text_area("Notes",
                                       value=str(cov_row.get("notes", "") or ""), height=60)

                if st.form_submit_button("💾 Save Changes", type="primary"):
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "analyst_name"] = analyst_name
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "role"] = role
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "recommendation"] = rec
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "target_price_cad"] = tp
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "status"] = status
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "next_earnings"] = next_e
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "thesis_summary"] = thesis
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "key_risks"] = risks
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "notes"] = notes
                    coverage.loc[coverage["ticker"] == ticker_to_edit, "last_update"] = \
                        datetime.now().strftime("%Y-%m-%d")
                    if _save_coverage(coverage):
                        st.success(f"✅ {ticker_to_edit} updated.")
                        st.rerun()

    # ── Tab 3: Add ─────────────────────────────────────────────────────────
    with tabs[2]:
        covered_set = set(coverage["ticker"].tolist()) if not coverage.empty else set()
        uncovered = [t for t in companies["ticker"].tolist() if t not in covered_set]

        if not uncovered:
            st.success("All companies have analyst coverage. 🎉")
        else:
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                with c1:
                    new_ticker = st.selectbox("Company to cover", options=uncovered)
                    new_analyst = st.text_input("Analyst Name")
                    new_role = st.text_input("Analyst Role", value="Junior Analyst")
                    new_rec = st.selectbox("Initial Recommendation",
                                             options=["BUY", "HOLD", "SELL", "WATCHLIST"], index=1)
                with c2:
                    new_tp = st.number_input("Target Price (CAD)", value=0.0, step=1.0)
                    new_status = st.selectbox("Status",
                                                 options=["Nouveau", "À jour", "À revoir"], index=0)
                    new_next_e = st.text_input("Next Earnings (YYYY-MM-DD)")

                new_thesis = st.text_area("Initial Thesis (1-3 paragraphs)", height=120)
                new_risks = st.text_area("Key Risks", height=80)
                new_notes = st.text_area("Notes", height=60)

                if st.form_submit_button("➕ Add Coverage", type="primary"):
                    if not new_analyst.strip():
                        st.error("Please enter analyst name.")
                    else:
                        new_row = pd.DataFrame([{
                            "ticker": new_ticker, "analyst_name": new_analyst,
                            "role": new_role, "recommendation": new_rec,
                            "target_price_cad": new_tp,
                            "last_update": datetime.now().strftime("%Y-%m-%d"),
                            "thesis_summary": new_thesis, "key_risks": new_risks,
                            "next_earnings": new_next_e, "status": new_status,
                            "notes": new_notes,
                        }])
                        updated = pd.concat([coverage, new_row], ignore_index=True)
                        if _save_coverage(updated):
                            st.success(f"✅ Coverage added for {new_ticker}.")
                            st.rerun()
