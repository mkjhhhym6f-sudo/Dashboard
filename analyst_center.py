"""
PAGE 8 — ANALYST CENTER
Analyst workspace: coverage tracking, thesis management, notes, recommendations.
Reads from and writes to config/analyst_coverage.csv.
"""

import streamlit as st
import pandas as pd
import os, sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_providers.market_data import MarketDataProvider

DARK = "#0e1117"
CARD = "#1a1d27"
ACCENT = "#00d4aa"
TEXT = "#e0e0e0"
MUTED = "#888"
RED = "#ff4b4b"
GREEN = "#00d4aa"
YELLOW = "#ffa500"

COVERAGE_PATH = Path(__file__).parent.parent.parent / "config" / "analyst_coverage.csv"
NOTES_PATH    = Path(__file__).parent.parent.parent / "data" / "manual" / "analyst_notes.csv"

# CSV columns: ticker,analyst_name,role,recommendation,target_price_cad,
#              last_update,thesis_summary,key_risks,next_earnings,status,notes
COL = {
    "ticker":      "ticker",
    "analyst":     "analyst_name",
    "rec":         "recommendation",
    "target":      "target_price_cad",
    "last_update": "last_update",
    "thesis":      "thesis_summary",
    "risks":       "key_risks",
    "next_earn":   "next_earnings",
    "status":      "status",
    "notes":       "notes",
}


def _load_coverage() -> pd.DataFrame:
    if COVERAGE_PATH.exists():
        df = pd.read_csv(COVERAGE_PATH)
        universe_path = Path(__file__).parent.parent.parent / "config" / "universe.csv"
        if universe_path.exists() and "name" not in df.columns:
            uni = pd.read_csv(universe_path)[["ticker", "name"]]
            df = df.merge(uni, on="ticker", how="left")
        return df
    return pd.DataFrame()


def _save_coverage(df: pd.DataFrame):
    save_df = df.drop(columns=["name"], errors="ignore")
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_df.to_csv(COVERAGE_PATH, index=False)


def _load_notes() -> pd.DataFrame:
    if NOTES_PATH.exists():
        return pd.read_csv(NOTES_PATH)
    return pd.DataFrame(columns=["ticker", "date", "analyst", "note", "category"])


def _save_notes(df: pd.DataFrame):
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(NOTES_PATH, index=False)


def _status_badge(status: str) -> str:
    colors = {"À jour": GREEN, "À revoir": YELLOW, "Urgent": RED}
    color = colors.get(status, MUTED)
    return f'<span style="background:{color}20;color:{color};padding:2px 8px;border-radius:4px;font-size:12px">{status}</span>'


def _rec_badge(rec: str) -> str:
    rec_up = str(rec).upper() if rec else "N/A"
    colors = {"BUY": GREEN, "HOLD": YELLOW, "SELL": RED, "WATCHLIST": "#888aff", "N/A": MUTED}
    color = colors.get(rec_up, MUTED)
    return f'<span style="background:{color}20;color:{color};padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600">{rec}</span>'


def render():
    st.markdown("## 🗂️ Analyst Center")
    st.markdown("*Manage analyst coverage, investment theses, recommendations and notes*")

    df_coverage = _load_coverage()
    df_notes    = _load_notes()

    tab_dashboard, tab_detail, tab_edit, tab_notes = st.tabs([
        "📋 Coverage Dashboard", "🔍 Company Detail",
        "✏️ Edit Coverage",      "📝 Notes Log"
    ])

    with tab_dashboard: _render_dashboard(df_coverage)
    with tab_detail:    _render_detail(df_coverage)
    with tab_edit:      _render_edit(df_coverage)
    with tab_notes:     _render_notes(df_notes, df_coverage)


def _render_dashboard(df: pd.DataFrame):
    st.markdown("### 📋 Coverage Dashboard")
    if df.empty:
        st.warning("No coverage data found. Check that `config/analyst_coverage.csv` exists.")
        return

    rc, sc, ac = COL["rec"], COL["status"], COL["analyst"]
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total Coverage", len(df))
    k2.metric("🟢 Buy",  (df[rc].str.upper()=="BUY").sum()  if rc in df else 0)
    k3.metric("🟡 Hold", (df[rc].str.upper()=="HOLD").sum() if rc in df else 0)
    k4.metric("🔴 Sell", (df[rc].str.upper()=="SELL").sum() if rc in df else 0)
    k5.metric("🚨 Urgent", (df[sc].str.lower().str.contains("urgent",na=False)).sum() if sc in df else 0)

    cf1,cf2,cf3 = st.columns(3)
    analysts = ["All"] + sorted(df[ac].dropna().unique().tolist()) if ac in df.columns else ["All"]
    with cf1: sa = st.selectbox("Analyst", analysts)
    with cf2: sr = st.selectbox("Recommendation", ["All","BUY","HOLD","SELL","WATCHLIST"])
    with cf3: ss = st.selectbox("Status", ["All"] + sorted(df[sc].dropna().unique().tolist()) if sc in df.columns else ["All"])

    filt = df.copy()
    if sa != "All": filt = filt[filt[ac] == sa]
    if sr != "All": filt = filt[filt[rc].str.upper() == sr]
    if ss != "All": filt = filt[filt[sc] == ss]

    st.markdown("---")
    for _, row in filt.iterrows():
        c1,c2,c3,c4,c5,c6 = st.columns([1.5,2,1.5,2,2,1.5])
        c1.markdown(f"**{row.get('ticker','—')}**")
        c2.markdown(str(row.get("name", row.get("ticker","—"))))
        c3.markdown(_rec_badge(str(row.get(rc,"N/A"))), unsafe_allow_html=True)
        tgt = row.get(COL["target"], None)
        tgt_s = f"${float(tgt):.2f}" if pd.notna(tgt) and str(tgt).strip() not in ("","nan") else "N/A"
        c4.markdown(f"🎯 Target: **{tgt_s}**")
        c5.markdown(str(row.get(ac,"—")))
        c6.markdown(_status_badge(str(row.get(sc,"N/A"))), unsafe_allow_html=True)

    if rc in df.columns:
        import plotly.graph_objects as go
        counts = df[rc].str.upper().value_counts().reset_index()
        counts.columns = ["Rec","Count"]
        pc = {"BUY":GREEN,"HOLD":YELLOW,"SELL":RED,"WATCHLIST":"#888aff","N/A":MUTED}
        fig = go.Figure(go.Pie(
            labels=counts["Rec"], values=counts["Count"],
            marker=dict(colors=[pc.get(r,MUTED) for r in counts["Rec"]]),
            hole=0.5, textinfo="label+percent"
        ))
        fig.update_layout(template="plotly_dark",paper_bgcolor=DARK,
                          height=280,title="Recommendation Distribution",showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def _render_detail(df: pd.DataFrame):
    st.markdown("### 🔍 Company Detail")
    if df.empty:
        st.warning("No coverage data available.")
        return

    tc = COL["ticker"]
    tickers = df[tc].tolist()
    selected = st.selectbox(
        "Select Company", tickers,
        format_func=lambda t: f"{t} — {df[df[tc]==t]['name'].values[0] if 'name' in df.columns and len(df[df[tc]==t])>0 else t}"
    )

    rows = df[df[tc] == selected]
    if rows.empty: return
    row = rows.iloc[0]

    mdp = MarketDataProvider()
    try:
        fund = mdp.get_fundamentals(selected)
        price = float(fund.get("price") or fund.get("currentPrice") or 0)
    except Exception:
        price = 0.0

    h1,h2,h3,h4 = st.columns(4)
    h1.metric("Current Price", f"${price:.2f}" if price else "N/A")
    h2.markdown(_rec_badge(str(row.get(COL["rec"],"N/A"))), unsafe_allow_html=True)
    tgt = row.get(COL["target"], None)
    if pd.notna(tgt) and str(tgt).strip() not in ("","nan") and price:
        h3.metric("Target Price", f"${float(tgt):.2f}", delta=f"{float(tgt)/price-1:+.1%}")
    else:
        h3.metric("Target Price","N/A")
    h4.markdown(_status_badge(str(row.get(COL["status"],"N/A"))), unsafe_allow_html=True)

    st.markdown("---")
    cl, cr = st.columns(2)
    with cl:
        st.markdown("#### 📈 Investment Thesis")
        thesis = str(row.get(COL["thesis"],"No thesis entered.") or "No thesis entered.")
        st.markdown(f'<div style="background:{CARD};padding:16px;border-radius:10px;border-left:3px solid {ACCENT}"><p style="color:{TEXT};line-height:1.7;margin:0">{thesis}</p></div>', unsafe_allow_html=True)

        st.markdown("#### 📅 Key Info")
        for lbl, key in [("Analyst",COL["analyst"]),("Last Update",COL["last_update"]),
                          ("Next Earnings",COL["next_earn"]),("Status",COL["status"])]:
            val = str(row.get(key,"N/A") or "N/A")
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #333"><span style="color:{MUTED}">{lbl}</span><span style="color:{TEXT};font-weight:500">{val}</span></div>', unsafe_allow_html=True)

    with cr:
        st.markdown("#### ⚠️ Key Risks")
        risks = str(row.get(COL["risks"],"No risks entered.") or "No risks entered.")
        st.markdown(f'<div style="background:{CARD};padding:16px;border-radius:10px;border-left:3px solid {RED}"><p style="color:{TEXT};line-height:1.7;margin:0">{risks}</p></div>', unsafe_allow_html=True)
        if row.get(COL["notes"]):
            st.markdown("#### 📝 Notes")
            st.info(str(row.get(COL["notes"],"")))


def _render_edit(df: pd.DataFrame):
    st.markdown("### ✏️ Edit Coverage")
    if df.empty:
        st.warning("No coverage data found.")
        return

    tc = COL["ticker"]
    tickers = df[tc].tolist()
    selected = st.selectbox(
        "Select Company to Edit", tickers, key="edit_ticker",
        format_func=lambda t: f"{t} — {df[df[tc]==t]['name'].values[0] if 'name' in df.columns and len(df[df[tc]==t])>0 else t}"
    )

    mask = df[tc] == selected
    if not mask.any(): return
    idx = df[mask].index[0]
    row = df.loc[idx]

    valid_recs = ["BUY","HOLD","SELL","WATCHLIST","N/A"]
    curr_rec   = str(row.get(COL["rec"],"N/A")).upper()
    if curr_rec not in valid_recs: curr_rec = "N/A"
    valid_st   = ["À jour","À revoir","Urgent"]
    curr_st    = str(row.get(COL["status"],"À revoir"))
    if curr_st not in valid_st: curr_st = "À revoir"

    with st.form(key=f"edit_{selected}"):
        c1,c2 = st.columns(2)
        with c1:
            analyst   = st.text_input("Analyst Name", value=str(row.get(COL["analyst"],"") or ""))
            rec       = st.selectbox("Recommendation", valid_recs, index=valid_recs.index(curr_rec))
            tgt_val   = row.get(COL["target"], 0)
            try: tgt_val = float(tgt_val)
            except: tgt_val = 0.0
            target    = st.number_input("Target Price (CAD $)", value=tgt_val, step=1.0, min_value=0.0)
            status    = st.selectbox("Status", valid_st, index=valid_st.index(curr_st))
        with c2:
            next_earn = st.text_input("Next Earnings", value=str(row.get(COL["next_earn"],"") or ""))

        thesis = st.text_area("Investment Thesis", value=str(row.get(COL["thesis"],"") or ""), height=120)
        risks  = st.text_area("Key Risks",        value=str(row.get(COL["risks"],"")  or ""), height=100)
        notes  = st.text_area("Notes",            value=str(row.get(COL["notes"],"")  or ""), height=80)

        if st.form_submit_button("💾 Save Changes", type="primary"):
            df.at[idx, COL["analyst"]]    = analyst
            df.at[idx, COL["rec"]]        = rec
            df.at[idx, COL["target"]]     = target if target > 0 else ""
            df.at[idx, COL["status"]]     = status
            df.at[idx, COL["next_earn"]]  = next_earn
            df.at[idx, COL["thesis"]]     = thesis
            df.at[idx, COL["risks"]]      = risks
            df.at[idx, COL["notes"]]      = notes
            df.at[idx, COL["last_update"]] = datetime.today().strftime("%Y-%m-%d")
            _save_coverage(df)
            st.success(f"✅ Saved **{selected}**!")
            st.rerun()


def _render_notes(df_notes: pd.DataFrame, df_coverage: pd.DataFrame):
    st.markdown("### 📝 Notes Log")

    with st.expander("➕ Add New Note", expanded=False):
        tc = COL["ticker"]
        tickers = df_coverage[tc].tolist() if not df_coverage.empty else []
        with st.form("new_note"):
            c1,c2 = st.columns(2)
            with c1:
                nt = st.selectbox("Company", tickers)
                na = st.text_input("Analyst Name")
                nc = st.selectbox("Category", ["General","Earnings","Thesis Update",
                                               "Risk Flag","Management Meeting","Model Update","News"])
            with c2:
                nd = st.date_input("Date", value=date.today())
                nn = st.text_area("Note", height=120)
            if st.form_submit_button("💾 Add Note") and nn.strip():
                new_row = pd.DataFrame([{"ticker":nt,"date":str(nd),"analyst":na,"note":nn.strip(),"category":nc}])
                df_notes = pd.concat([df_notes, new_row], ignore_index=True)
                _save_notes(df_notes)
                st.success("✅ Note saved!")
                st.rerun()

    if df_notes.empty:
        st.info("No notes yet.")
        return

    c1,c2 = st.columns(2)
    with c1: ft = st.selectbox("Filter by Company",  ["All"]+sorted(df_notes["ticker"].dropna().unique().tolist()))
    with c2: fc = st.selectbox("Filter by Category", ["All"]+sorted(df_notes.get("category",pd.Series()).dropna().unique().tolist()))

    filt = df_notes.copy()
    if ft != "All": filt = filt[filt["ticker"]==ft]
    if fc != "All" and "category" in filt.columns: filt = filt[filt["category"]==fc]
    if "date" in filt.columns: filt = filt.sort_values("date",ascending=False)

    cat_colors = {"Risk Flag":RED,"Earnings":ACCENT,"Thesis Update":"#888aff",
                  "Management Meeting":YELLOW,"Model Update":"#ff88ff","News":"#88aaff","General":MUTED}
    for _,r in filt.iterrows():
        cat   = str(r.get("category","General"))
        color = cat_colors.get(cat,MUTED)
        st.markdown(f"""
        <div style="background:{CARD};padding:14px 18px;border-radius:10px;
                    margin-bottom:10px;border-left:4px solid {color}">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <div>
                    <strong style="color:{ACCENT}">{r.get('ticker','')}</strong>
                    <span style="color:{MUTED};margin-left:8px;font-size:12px">{r.get('date','')}</span>
                    <span style="background:{color}20;color:{color};padding:1px 8px;border-radius:4px;font-size:11px;margin-left:8px">{cat}</span>
                </div>
                <div style="color:{MUTED};font-size:12px">by {r.get('analyst','Unknown')}</div>
            </div>
            <div style="color:{TEXT};line-height:1.6">{r.get('note','')}</div>
        </div>
        """, unsafe_allow_html=True)

    if not filt.empty:
        st.download_button("⬇️ Export CSV", data=filt.to_csv(index=False),
                           file_name="analyst_notes_export.csv", mime="text/csv")
