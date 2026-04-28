# SIF Analytics — Vert & Or
### Université de Sherbrooke · Student Investment Fund Dashboard

A professional, institutional-grade analytics platform for a student-run investment fund covering 38 securities (34 Canadian/US equities + 4 ETF benchmarks).

---

## ⚡ Deploy to Streamlit Community Cloud

### 1. Push to GitHub

All files in this folder go to the **root** of a new GitHub repository — flat structure, no subfolders for Python files.

```
your-repo/
├── app.py                      ← entry point
├── requirements.txt
├── theme.py
├── formatting.py
├── market_data.py
├── macro_data.py
├── scoring.py
├── valuation.py
├── charts.py
├── fund_overview.py
├── sector_overview.py
├── macro_dashboard.py
├── company_deep_dive.py
├── peer_comparison.py
├── valuation_center.py
├── risk_monitor.py
├── analyst_center.py
├── data_quality.py
├── .streamlit/config.toml
└── config/
    ├── universe.csv
    ├── analyst_coverage.csv
    └── sector_config.yaml
```

### 2. Streamlit Cloud settings

| Field | Value |
|-------|-------|
| **Repository** | `your-username/sif-analytics` |
| **Branch** | `main` |
| **Main file path** | `app.py` |

### 3. (Optional) Add FRED API key

In Streamlit Cloud → **Settings → Secrets**, paste:

```toml
FRED_API_KEY = "your_fred_api_key_here"
```

Get a free FRED key here: https://fred.stlouisfed.org/docs/api/api_key.html

The dashboard works fully without the FRED key — only US macro data will show "N/A". Bank of Canada data works without any key.

---

## 📁 Project Structure (FLAT)

Every Python file is at the **root** of the repository — no nested folders, no `pages/` or `src/` subfolders. This is intentional: Streamlit Community Cloud has the simplest module resolution when everything is flat.

| File | Purpose |
|------|---------|
| `app.py` | Streamlit entry point with sidebar navigation |
| `theme.py` | UdeS Vert & Or color palette and CSS |
| `formatting.py` | Number/currency/percent formatters |
| `market_data.py` | yfinance wrapper with caching |
| `macro_data.py` | FRED + Bank of Canada providers |
| `scoring.py` | 6-component composite score (0–100) |
| `valuation.py` | DCF, Reverse DCF, sensitivity |
| `charts.py` | Plotly chart factory with UdeS theme |
| `fund_overview.py` | Page 1: Portfolio overview |
| `sector_overview.py` | Page 2: Sector deep dive |
| `macro_dashboard.py` | Page 3: Macro indicators |
| `company_deep_dive.py` | Page 4: Single-company analysis |
| `peer_comparison.py` | Page 5: Multi-company comparison |
| `valuation_center.py` | Page 6: Standalone DCF tooling |
| `risk_monitor.py` | Page 7: Portfolio-wide alerts |
| `analyst_center.py` | Page 8: Manage coverage and theses |
| `data_quality.py` | Page 9: API health and inventory |

---

## ➕ Adding a New Company

The dashboard is designed to make adding companies trivially easy:

1. Open `config/universe.csv` directly in GitHub (click the pencil ✏️ icon)
2. Add a new row at the end:

```csv
ticker,ticker_yf,name,sector,subsector,market,currency,is_etf,analyst,weight_pct
TSX:NEW,NEW.TO,New Company Inc.,Technology,Software,TSX,CAD,False,TBD,0
```

3. Commit changes — Streamlit Cloud auto-redeploys in ~30 seconds
4. The new company appears everywhere automatically: portfolio overview, sector overview, peer comparison, and is available in dropdowns

### Special TSX ticker formats

| Fund format | yfinance format | Example |
|-------------|-----------------|---------|
| `TSX:SHOP` | `SHOP.TO` | Standard |
| `TSX:QBR.B` | `QBR-B.TO` | Class B (replace `.` with `-`) |
| `TSX:CSH.UN` | `CSH-UN.TO` | Income trust |
| `NASDAQ:LULU` | `LULU` | US ticker |

---

## 🔄 Auto-Refresh Behavior

| Data type | Cache duration | Refreshes when |
|-----------|----------------|----------------|
| Universe CSV | 5 min | File edited or cache cleared |
| Stock prices | 4 hours | Cache TTL or "Refresh" button |
| Fundamentals | 24 hours | Cache TTL or "Refresh" button |
| Macro indicators | 12 hours | Cache TTL or "Refresh" button |

Click the **🔄 Clear Cache & Reload** button in the sidebar to force a full refresh.

---

## 🎨 Brand Identity

Colors use the official Université de Sherbrooke palette:
- **Vert fierté** `#00563F` — primary
- **Vert standard** `#007A33` — accent
- **Or** `#FFB81C` — highlights
- Typography: Merriweather (headings) + Inter (body)

---

## 🛡️ Robustness

The dashboard is designed to **never crash** on missing data:
- yfinance returns nothing → fields show `N/A`
- FRED key absent → US macro shows `N/A`, BoC continues working
- BoC offline → both regions show `N/A`, app continues
- Per-ticker errors caught silently — never propagate to user
- Special TSX tickers (`.B`, `.UN`, `.A`) handled via centralized mapping

---

## 🐍 Python Version

Python 3.9–3.12 supported. Streamlit Cloud uses 3.11 by default.

---

*Educational tool — not investment advice. © 2025 Étudiantes et étudiants en finance, Université de Sherbrooke*
