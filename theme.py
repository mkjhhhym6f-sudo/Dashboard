"""
theme.py — Visual identity for SIF Analytics
Université de Sherbrooke colors (Vert fierté + Or) — professional dark layout.
"""

# ─── UdeS Brand ─────────────────────────────────────────────────
UDES_GREEN_DARK = "#00563F"   # Vert fierté (primary)
UDES_GREEN      = "#007A33"   # Vert standard
UDES_GREEN_LIGHT = "#4A9D6A"  # Lighter green
UDES_GOLD       = "#FFB81C"   # Or
UDES_GOLD_LIGHT = "#FFD166"
UDES_GOLD_DARK  = "#C8941A"   # Deeper gold

# ─── Backgrounds ───────────────────────────────────────────────
BG_DARK    = "#0D1B17"
BG_CARD    = "#142821"
BG_LIGHT   = "#1C3A30"
BG_DIVIDER = "#1F4036"
BORDER     = "#1F4036"

# ─── Text ──────────────────────────────────────────────────────
TEXT_PRIMARY   = "#F5F7F4"
TEXT_SECONDARY = "#B8C5BD"
TEXT_MUTED     = "#7A8C82"

# ─── Semantic ──────────────────────────────────────────────────
POSITIVE = "#22C55E"
NEGATIVE = "#EF4444"
NEUTRAL  = "#94A3B8"
WARNING  = "#F59E0B"
INFO     = "#3B82F6"

# ─── Sector Colors ─────────────────────────────────────────────
SECTOR_COLORS = {
    "Technology":             "#00B4D8",
    "Financials":             UDES_GREEN,
    "Industrials":            "#F77F00",
    "Consumer Staples":       "#52B788",
    "Consumer Discretionary": "#E63946",
    "Healthcare":             "#9D4EDD",
    "Energy":                 "#FFB703",
    "Materials":              "#B5651D",
    "Utilities":              "#06A77D",
    "Communications":         "#8338EC",
    "Communication Services": "#8338EC",
    "Real Estate":            "#FB8500",
    "ETF":                    UDES_GOLD,
    "Default":                NEUTRAL,
}


# ─── Global CSS ────────────────────────────────────────────────
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Merriweather:wght@400;700;900&display=swap');

.stApp {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}
#MainMenu, footer {{visibility: hidden;}}
/* NOTE: 'header' intentionally excluded — it contains the sidebar toggle button */

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {UDES_GREEN_DARK} 0%, #003D2D 100%);
}}
section[data-testid="stSidebar"] * {{ color: {TEXT_PRIMARY} !important; }}

/* Hero */
.sif-hero {{
    background: linear-gradient(135deg, {UDES_GREEN_DARK} 0%, {UDES_GREEN} 100%);
    border-radius: 14px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border-left: 6px solid {UDES_GOLD};
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}}
.sif-hero h1 {{
    font-family: 'Merriweather', Georgia, serif;
    color: {TEXT_PRIMARY};
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
}}
.sif-hero p {{
    color: {UDES_GOLD_LIGHT};
    margin: 0.4rem 0 0 0;
    font-size: 0.95rem;
}}

/* Section headers */
.sif-section {{
    font-family: 'Merriweather', Georgia, serif;
    color: {TEXT_PRIMARY};
    font-size: 1.15rem;
    font-weight: 700;
    margin: 1.5rem 0 0.75rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {UDES_GOLD};
}}

/* Cards */
.sif-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.2rem;
}}
.sif-card-label {{
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
}}
.sif-card-value {{
    color: {TEXT_PRIMARY};
    font-family: 'Merriweather', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0.25rem 0;
}}

/* Badges */
.sif-badge {{
    display: inline-block;
    padding: 0.25rem 0.7rem;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}
.sif-badge-buy        {{ background: rgba(34,197,94,0.15);  color: {POSITIVE}; border:1px solid {POSITIVE}; }}
.sif-badge-hold       {{ background: rgba(245,158,11,0.15); color: {WARNING};  border:1px solid {WARNING}; }}
.sif-badge-watchlist  {{ background: rgba(247,127,0,0.15);  color: #F77F00;    border:1px solid #F77F00; }}
.sif-badge-sell       {{ background: rgba(239,68,68,0.15);  color: {NEGATIVE}; border:1px solid {NEGATIVE}; }}
.sif-badge-benchmark  {{ background: rgba(255,184,28,0.15); color: {UDES_GOLD};border:1px solid {UDES_GOLD}; }}

/* Alerts */
.sif-alert {{
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.88rem;
    border-left: 4px solid;
}}
.sif-alert-critical {{ background: rgba(239,68,68,0.08);  border-color: {NEGATIVE}; }}
.sif-alert-warning  {{ background: rgba(245,158,11,0.08); border-color: {WARNING}; }}
.sif-alert-info     {{ background: rgba(59,130,246,0.08); border-color: {INFO}; }}
.sif-alert-ok       {{ background: rgba(34,197,94,0.08);  border-color: {POSITIVE}; }}

/* Streamlit metric override */
[data-testid="stMetric"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.2rem;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-family: 'Merriweather', Georgia, serif !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background: {BG_CARD};
    border-radius: 8px;
    padding: 0.25rem;
    gap: 0.25rem;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-weight: 500;
    padding: 0.5rem 1rem;
}}
.stTabs [aria-selected="true"] {{
    background: {UDES_GREEN} !important;
    color: {TEXT_PRIMARY} !important;
}}

/* Buttons */
.stButton > button {{
    background: {UDES_GREEN};
    color: {TEXT_PRIMARY};
    border: 1px solid {UDES_GREEN};
    border-radius: 8px;
    font-weight: 600;
}}
.stButton > button:hover {{
    background: {UDES_GREEN_DARK};
    border-color: {UDES_GOLD};
    color: {UDES_GOLD};
}}

/* Inputs */
.stSelectbox label, .stMultiSelect label, .stNumberInput label, .stSlider label {{
    color: {TEXT_SECONDARY} !important;
    font-weight: 500;
}}

/* DataFrame */
[data-testid="stDataFrame"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* Source label */
.sif-source {{
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    font-style: italic;
    margin-top: 0.25rem;
    display: block;
}}
</style>
"""


# ─── Helpers ─────────────────────────────────────────────────
def render_hero(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render the page hero banner directly to Streamlit."""
    import streamlit as st
    st.markdown(_render_hero_html(title, subtitle, icon), unsafe_allow_html=True)


def _render_hero_html(title: str, subtitle: str = "", icon: str = "") -> str:
    icon_html = f"{icon} " if icon else ""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    return f'<div class="sif-hero"><h1>{icon_html}{title}</h1>{sub_html}</div>'


def render_section(title: str) -> None:
    """Render a section header directly to Streamlit."""
    import streamlit as st
    st.markdown(_render_section_html(title), unsafe_allow_html=True)


def _render_section_html(title: str) -> str:
    return f'<div class="sif-section">{title}</div>'


def rec_badge(rec: str) -> str:
    rec_clean = (rec or "N/A").upper()
    css_map = {
        "BUY": "sif-badge-buy", "HOLD": "sif-badge-hold",
        "WATCHLIST": "sif-badge-watchlist", "SELL": "sif-badge-sell",
        "BENCHMARK": "sif-badge-benchmark",
    }
    css = css_map.get(rec_clean, "sif-badge-hold")
    return f'<span class="sif-badge {css}">{rec_clean}</span>'


def color_for_value(value, good_positive: bool = True) -> str:
    if value is None:
        return NEUTRAL
    try:
        v = float(value)
    except (TypeError, ValueError):
        return NEUTRAL
    if good_positive:
        return POSITIVE if v >= 0 else NEGATIVE
    return NEGATIVE if v >= 0 else POSITIVE


def color_for_recommendation(rec: str) -> str:
    return {
        "BUY": POSITIVE, "HOLD": WARNING, "WATCHLIST": "#F77F00",
        "SELL": NEGATIVE, "BENCHMARK": UDES_GOLD,
    }.get((rec or "").upper(), NEUTRAL)


def color_for_score(score) -> str:
    if score is None:
        return NEUTRAL
    try:
        s = float(score)
    except (TypeError, ValueError):
        return NEUTRAL
    if s >= 70: return POSITIVE
    if s >= 55: return UDES_GOLD
    if s >= 40: return WARNING
    return NEGATIVE


def get_plotly_layout(title: str = "", height: int = 380) -> dict:
    return dict(
        title=dict(text=title, font=dict(family="Merriweather, serif", size=15, color=TEXT_PRIMARY), x=0.02, xanchor="left"),
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(family="Inter, sans-serif", color=TEXT_SECONDARY, size=11),
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
        legend=dict(bgcolor=BG_CARD, bordercolor=BORDER, font=dict(color=TEXT_SECONDARY)),
        hoverlabel=dict(bgcolor=BG_LIGHT, bordercolor=UDES_GOLD, font=dict(color=TEXT_PRIMARY)),
    )
