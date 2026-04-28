"""
market_data.py — FIEUS Analytics data layer.

Data hierarchy:
  1. config/manual_fundamentals.csv  ← Capital IQ / FIEUS (highest priority)
  2. config/manual_valuation.csv     ← Capital IQ / FIEUS
  3. config/manual_targets.csv       ← FIEUS analyst views
  4. yfinance API                    ← price history, returns, market data
  5. N/A                             ← if absent everywhere

Rules:
  - Never treat blank CSV cells as zero.
  - Never invent values.
  - Always tag the source of each merged value.
  - fetch_fundamentals() returns a single unified dict with _source metadata.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent

# ── CSV file paths ────────────────────────────────────────────────────────────
UNIVERSE_CSV      = ROOT / "config" / "universe.csv"
ANALYST_CSV       = ROOT / "config" / "analyst_coverage.csv"
MANUAL_FUND_CSV   = ROOT / "config" / "manual_fundamentals.csv"
MANUAL_VAL_CSV    = ROOT / "config" / "manual_valuation.csv"
MANUAL_TARGET_CSV = ROOT / "config" / "manual_targets.csv"
DATA_DICT_CSV     = ROOT / "config" / "data_dictionary.csv"

# ── Ticker maps ───────────────────────────────────────────────────────────────
SPECIAL_TICKER_MAP = {
    "TSX:QBR.B":  "QBR-B.TO", "TSX:BBD.B":  "BBD-B.TO",
    "TSX:CSH.UN": "CSH-UN.TO", "TSX:GIB.A":  "GIB-A.TO",
    "TSX:CCL.B":  "CCL-B.TO",  "TSX:CAR.UN": "CAR-UN.TO",
    "TSX:RCI.B":  "RCI-B.TO",  "TSX:CTC.A":  "CTC-A.TO",
    "NASDAQ:LULU": "LULU",      "NYSE:GIL":   "GIL",
}

# ── Source labels ─────────────────────────────────────────────────────────────
SRC_CIQ     = "Capital IQ export"
SRC_FIEUS   = "FIEUS manual"
SRC_YF      = "yfinance"
SRC_PREMIUM = "Premium/manual required"
SRC_CALC    = "Calculated"


# ═════════════════════════════════════════════════════════════════════════════
# UNIVERSE & CONFIG LOADERS
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def load_universe() -> pd.DataFrame:
    """Load universe.csv (new schema with ciq_symbol). Falls back gracefully."""
    if not UNIVERSE_CSV.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(UNIVERSE_CSV, dtype=str)
        # Support both old schema (ticker) and new schema (ciq_symbol)
        if "ciq_symbol" in df.columns and "ticker" not in df.columns:
            df = df.rename(columns={"ciq_symbol": "ticker"})
        if "yahoo_symbol" in df.columns and "ticker_yf" not in df.columns:
            df = df.rename(columns={"yahoo_symbol": "ticker_yf"})
        if "company" in df.columns and "name" not in df.columns:
            df = df.rename(columns={"company": "name"})
        # Normalise is_etf
        if "is_etf" in df.columns:
            df["is_etf"] = df["is_etf"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
        # Filter out example rows
        if "ticker" in df.columns:
            df = df[~df["ticker"].astype(str).str.startswith("EXAMPLE")]
        return df
    except Exception as e:
        logger.error(f"load_universe failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def load_analyst_coverage() -> pd.DataFrame:
    """Load legacy analyst_coverage.csv. Cached 5 min."""
    if not ANALYST_CSV.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(ANALYST_CSV)
    except Exception as e:
        logger.error(f"load_analyst_coverage failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def load_manual_fundamentals() -> pd.DataFrame:
    """
    Load manual_fundamentals.csv (Capital IQ / FIEUS).
    Returns empty DataFrame with correct columns if file missing.
    Blank cells become NaN — never zero.
    """
    cols = [
        "ciq_symbol", "yahoo_symbol", "company", "fiscal_year", "fiscal_period",
        "revenue", "gross_profit", "ebitda", "ebit", "net_income", "free_cash_flow",
        "gross_margin", "ebitda_margin", "ebit_margin", "net_margin",
        "roe", "roic", "total_assets", "total_debt", "cash", "net_debt",
        "shares_outstanding", "last_update", "source",
    ]
    if not MANUAL_FUND_CSV.exists():
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(MANUAL_FUND_CSV, dtype=str, keep_default_na=True)
        # Strip example rows
        df = df[~df["ciq_symbol"].astype(str).str.startswith("EXAMPLE")]
        # Convert numeric columns — blank stays NaN
        num_cols = [
            "revenue", "gross_profit", "ebitda", "ebit", "net_income", "free_cash_flow",
            "gross_margin", "ebitda_margin", "ebit_margin", "net_margin",
            "roe", "roic", "total_assets", "total_debt", "cash", "net_debt",
            "shares_outstanding",
        ]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"load_manual_fundamentals failed: {e}")
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=300, show_spinner=False)
def load_manual_valuation() -> pd.DataFrame:
    """
    Load manual_valuation.csv (Capital IQ / FIEUS).
    Returns empty DataFrame if file missing. Blank cells → NaN.
    """
    cols = [
        "ciq_symbol", "yahoo_symbol", "company", "price", "market_cap",
        "enterprise_value", "pe", "forward_pe", "ev_ebitda", "ev_ebit",
        "ev_sales", "price_sales", "price_book", "fcf_yield", "dividend_yield",
        "net_debt_ebitda", "last_update", "source",
    ]
    if not MANUAL_VAL_CSV.exists():
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(MANUAL_VAL_CSV, dtype=str, keep_default_na=True)
        df = df[~df["ciq_symbol"].astype(str).str.startswith("EXAMPLE")]
        num_cols = [
            "price", "market_cap", "enterprise_value", "pe", "forward_pe",
            "ev_ebitda", "ev_ebit", "ev_sales", "price_sales", "price_book",
            "fcf_yield", "dividend_yield", "net_debt_ebitda",
        ]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"load_manual_valuation failed: {e}")
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=300, show_spinner=False)
def load_manual_targets() -> pd.DataFrame:
    """
    Load manual_targets.csv (FIEUS analyst views).
    Returns empty DataFrame if file missing.
    """
    cols = [
        "ciq_symbol", "company", "analyst", "recommendation", "target_price",
        "upside_downside", "thesis_status", "priority", "next_earnings",
        "last_update", "source", "bull_case", "base_case", "bear_case",
        "key_risks", "key_metrics_to_watch",
    ]
    if not MANUAL_TARGET_CSV.exists():
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(MANUAL_TARGET_CSV, dtype=str, keep_default_na=True)
        df = df[~df["ciq_symbol"].astype(str).str.startswith("EXAMPLE")]
        if "target_price" in df.columns:
            df["target_price"] = pd.to_numeric(df["target_price"], errors="coerce")
        if "upside_downside" in df.columns:
            df["upside_downside"] = pd.to_numeric(df["upside_downside"], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"load_manual_targets failed: {e}")
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data_dictionary() -> pd.DataFrame:
    """Load data_dictionary.csv."""
    if not DATA_DICT_CSV.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(DATA_DICT_CSV)
    except Exception:
        return pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════════════
# TICKER UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def get_yf_ticker(fund_ticker: str, override: str = None) -> str:
    """Convert fund-format ticker to yfinance format."""
    if override and isinstance(override, str) and override.strip():
        return override.strip()
    if fund_ticker in SPECIAL_TICKER_MAP:
        return SPECIAL_TICKER_MAP[fund_ticker]
    if ":" in fund_ticker:
        prefix, base = fund_ticker.split(":", 1)
        if prefix == "TSX":
            return f"{base}.TO"
        return base
    return fund_ticker


def get_company_meta(ticker: str) -> dict:
    """Return universe metadata for a ticker (ciq_symbol key)."""
    df = load_universe()
    if df.empty:
        return {}
    rows = df[df["ticker"] == ticker]
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


def _get_manual_row(df: pd.DataFrame, ciq_symbol: str) -> pd.Series | None:
    """Find a row in a manual CSV by ciq_symbol or by yahoo_symbol fallback."""
    if df.empty:
        return None
    # Primary join: ciq_symbol
    if "ciq_symbol" in df.columns:
        rows = df[df["ciq_symbol"] == ciq_symbol]
        if not rows.empty:
            return rows.iloc[0]
    # Fallback: ticker column (old universe.csv)
    if "ticker" in df.columns:
        rows = df[df["ticker"] == ciq_symbol]
        if not rows.empty:
            return rows.iloc[0]
    return None


def _coalesce(manual_val, yf_val):
    """
    Return manual_val if it is a real, non-null number; else yf_val.
    Never treats blank / NaN as zero.
    """
    if manual_val is not None and not (isinstance(manual_val, float) and np.isnan(manual_val)):
        try:
            v = float(manual_val)
            return v  # valid number from manual CSV
        except (TypeError, ValueError):
            pass
    return yf_val


# ═════════════════════════════════════════════════════════════════════════════
# PRICE HISTORY  (yfinance only — this is always market data)
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=4*3600, show_spinner=False)
def fetch_price_history(fund_ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch OHLCV price history from yfinance. Returns empty DataFrame on error."""
    meta = get_company_meta(fund_ticker)
    yf_ticker = get_yf_ticker(fund_ticker, meta.get("ticker_yf"))
    try:
        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(period=period, interval="1d", auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)
        return hist
    except Exception as e:
        logger.warning(f"Price fetch failed for {fund_ticker}: {e}")
        return pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════════════
# FUNDAMENTALS  — unified dict with CSV-first, yfinance fallback
# ═════════════════════════════════════════════════════════════════════════════

EMPTY_FUNDAMENTALS = {
    # identity
    "ticker_fund": None, "ticker_yf": None, "name": None, "sector": None,
    "industry": None, "currency": None, "exchange": None, "country": None,
    "description": None, "employees": None, "website": None,
    # price / market (always yfinance)
    "price": None, "prev_close": None, "open": None, "day_high": None,
    "day_low": None, "week_52_high": None, "week_52_low": None,
    "volume": None, "avg_volume": None, "beta": None,
    # size (CSV > yfinance)
    "market_cap": None, "enterprise_value": None, "shares_outstanding": None,
    "float_shares": None,
    # valuation multiples (CSV > yfinance)
    "pe_trailing": None, "pe_forward": None, "pb_ratio": None, "ps_ratio": None,
    "ev_ebitda": None, "ev_revenue": None, "peg_ratio": None,
    "ev_ebit": None, "ev_sales": None,
    "fcf_yield": None, "dividend_yield": None, "dividend_rate": None,
    "payout_ratio": None, "net_debt_ebitda": None,
    # income statement (CSV > yfinance)
    "revenue_ttm": None, "gross_profit": None, "ebitda": None, "ebit": None,
    "net_income_ttm": None, "free_cash_flow": None, "operating_cashflow": None,
    "eps_ttm": None, "eps_forward": None,
    # margins (CSV > yfinance)
    "gross_margin": None, "ebitda_margin": None, "ebit_margin": None,
    "profit_margin": None, "operating_margin": None,
    # returns (CSV > yfinance)
    "roe": None, "roa": None, "roic": None,
    # growth (yfinance only — usually unavailable)
    "revenue_growth_yoy": None, "earnings_growth": None,
    # balance sheet (CSV > yfinance)
    "total_assets": None, "total_debt": None, "cash": None, "net_debt": None,
    "current_ratio": None, "quick_ratio": None, "debt_to_equity": None,
    "book_value": None, "fcf": None,
    # analyst / thesis (manual_targets.csv)
    "analyst": None, "recommendation": None, "target_price": None,
    "upside_downside": None, "thesis_status": None, "priority": None,
    "next_earnings": None, "bull_case": None, "base_case": None, "bear_case": None,
    "key_risks": None, "key_metrics_to_watch": None,
    # metadata
    "data_source": SRC_YF, "data_quality": "missing",
    "manual_fund_source": None, "manual_val_source": None,
    "manual_fund_last_update": None, "manual_val_last_update": None,
    "has_manual_fundamentals": False, "has_manual_valuation": False,
    "has_manual_targets": False,
}


@st.cache_data(ttl=24*3600, show_spinner=False)
def fetch_fundamentals(fund_ticker: str) -> dict:
    """
    Return unified fundamentals dict — CSV first, yfinance fallback.

    Priority:
      1. manual_fundamentals.csv / manual_valuation.csv  → Capital IQ / FIEUS
      2. yfinance .info                                   → free market data
      3. None                                             → displayed as N/A

    Never treats blank/NaN cells from CSV as zero.
    """
    meta = get_company_meta(fund_ticker)
    yf_ticker = get_yf_ticker(fund_ticker, meta.get("ticker_yf"))
    result = {
        **EMPTY_FUNDAMENTALS,
        "ticker_fund": fund_ticker,
        "ticker_yf":   yf_ticker,
        # Fill name/sector/industry from universe always
        "name":     meta.get("name"),
        "sector":   meta.get("sector"),
        "industry": meta.get("industry") or meta.get("subsector"),
        "currency": meta.get("currency"),
        "country":  meta.get("country"),
    }

    # ── Step 1: yfinance (lowest priority — only used as fallback) ────────────
    yf_info = {}
    try:
        ticker_obj = yf.Ticker(yf_ticker)
        yf_info = ticker_obj.info or {}
    except Exception as e:
        logger.warning(f"yfinance failed for {fund_ticker}: {e}")
        result["data_quality"] = "error"

    yf_map = {
        "name":            ["longName", "shortName"],
        "sector":          ["sector"], "industry": ["industry"],
        "currency":        ["currency"], "exchange": ["exchange"], "country": ["country"],
        "description":     ["longBusinessSummary"], "employees": ["fullTimeEmployees"],
        "website":         ["website"],
        "price":           ["currentPrice", "regularMarketPrice"],
        "prev_close":      ["previousClose"], "open": ["open"],
        "day_high":        ["dayHigh"], "day_low": ["dayLow"],
        "week_52_high":    ["fiftyTwoWeekHigh"], "week_52_low": ["fiftyTwoWeekLow"],
        "volume":          ["volume"], "avg_volume": ["averageVolume"],
        "market_cap":      ["marketCap"], "enterprise_value": ["enterpriseValue"],
        "shares_outstanding": ["sharesOutstanding"], "float_shares": ["floatShares"],
        "pe_trailing":     ["trailingPE"], "pe_forward": ["forwardPE"],
        "pb_ratio":        ["priceToBook"], "ps_ratio": ["priceToSalesTrailing12Months"],
        "ev_ebitda":       ["enterpriseToEbitda"], "ev_revenue": ["enterpriseToRevenue"],
        "peg_ratio":       ["pegRatio"],
        "dividend_yield":  ["dividendYield"], "dividend_rate": ["dividendRate"],
        "payout_ratio":    ["payoutRatio"],
        "profit_margin":   ["profitMargins"], "operating_margin": ["operatingMargins"],
        "gross_margin":    ["grossMargins"], "ebitda_margin": ["ebitdaMargins"],
        "roe":             ["returnOnEquity"], "roa": ["returnOnAssets"],
        "revenue_ttm":     ["totalRevenue"], "revenue_growth_yoy": ["revenueGrowth"],
        "ebitda":          ["ebitda"], "net_income_ttm": ["netIncomeToCommon"],
        "eps_ttm":         ["trailingEps"], "eps_forward": ["forwardEps"],
        "earnings_growth": ["earningsGrowth"],
        "cash":            ["totalCash"], "total_debt": ["totalDebt"],
        "current_ratio":   ["currentRatio"], "quick_ratio": ["quickRatio"],
        "debt_to_equity":  ["debtToEquity"], "book_value": ["bookValue"],
        "fcf":             ["freeCashflow"], "operating_cashflow": ["operatingCashflow"],
        "beta":            ["beta"],
    }

    for key, sources in yf_map.items():
        for src in sources:
            val = yf_info.get(src)
            if val is not None and val != "":
                result[key] = val
                break

    # Derived from yfinance if available
    if result["total_debt"] is not None or result["cash"] is not None:
        result["net_debt"] = (result["total_debt"] or 0) - (result["cash"] or 0)

    # Fix dividend_yield sometimes returned as > 1 by yfinance
    dy = result["dividend_yield"]
    if dy is not None:
        try:
            dy_v = float(dy)
            if dy_v > 1:
                result["dividend_yield"] = dy_v / 100
        except (TypeError, ValueError):
            pass

    # Mark yfinance quality
    if yf_info:
        result["data_quality"] = "yfinance"
        result["data_source"]  = SRC_YF

    # ── Step 2: manual_fundamentals.csv — OVERRIDES yfinance ─────────────────
    mf_df  = load_manual_fundamentals()
    mf_row = _get_manual_row(mf_df, fund_ticker)

    if mf_row is not None:
        mf_src = str(mf_row.get("source") or SRC_CIQ)
        mf_upd = str(mf_row.get("last_update") or "")
        result["manual_fund_source"]      = mf_src
        result["manual_fund_last_update"] = mf_upd
        result["has_manual_fundamentals"] = True

        # Map CSV columns → internal fund keys (CSV > yfinance)
        csv_to_fund = {
            "revenue":          "revenue_ttm",
            "gross_profit":     "gross_profit",
            "ebitda":           "ebitda",
            "ebit":             "ebit",
            "net_income":       "net_income_ttm",
            "free_cash_flow":   ("fcf", "free_cash_flow"),
            "gross_margin":     "gross_margin",
            "ebitda_margin":    "ebitda_margin",
            "ebit_margin":      "ebit_margin",
            "net_margin":       "profit_margin",
            "roe":              "roe",
            "roic":             "roic",
            "total_assets":     "total_assets",
            "total_debt":       "total_debt",
            "cash":             "cash",
            "net_debt":         "net_debt",
            "shares_outstanding": "shares_outstanding",
        }

        for csv_col, fund_key in csv_to_fund.items():
            csv_val = mf_row.get(csv_col)
            if isinstance(fund_key, tuple):
                for k in fund_key:
                    result[k] = _coalesce(csv_val, result.get(k))
            else:
                result[fund_key] = _coalesce(csv_val, result.get(fund_key))

        # Re-derive net_debt from manual if both available
        if result.get("total_debt") is not None and result.get("cash") is not None:
            nd = _coalesce(mf_row.get("net_debt"),
                           (result["total_debt"] or 0) - (result["cash"] or 0))
            result["net_debt"] = nd

        result["data_quality"] = "manual"
        result["data_source"]  = mf_src

    # ── Step 3: manual_valuation.csv — OVERRIDES yfinance multiples ──────────
    mv_df  = load_manual_valuation()
    mv_row = _get_manual_row(mv_df, fund_ticker)

    if mv_row is not None:
        mv_src = str(mv_row.get("source") or SRC_CIQ)
        mv_upd = str(mv_row.get("last_update") or "")
        result["manual_val_source"]      = mv_src
        result["manual_val_last_update"] = mv_upd
        result["has_manual_valuation"]   = True

        csv_to_val = {
            "price":            "price",
            "market_cap":       "market_cap",
            "enterprise_value": "enterprise_value",
            "pe":               "pe_trailing",
            "forward_pe":       "pe_forward",
            "ev_ebitda":        "ev_ebitda",
            "ev_ebit":          "ev_ebit",
            "ev_sales":         ("ev_revenue", "ev_sales"),
            "price_sales":      "ps_ratio",
            "price_book":       "pb_ratio",
            "fcf_yield":        "fcf_yield",
            "dividend_yield":   "dividend_yield",
            "net_debt_ebitda":  "net_debt_ebitda",
        }

        for csv_col, fund_key in csv_to_val.items():
            csv_val = mv_row.get(csv_col)
            if isinstance(fund_key, tuple):
                for k in fund_key:
                    result[k] = _coalesce(csv_val, result.get(k))
            else:
                result[fund_key] = _coalesce(csv_val, result.get(fund_key))

        # Only upgrade quality if we don't already have manual fundamentals
        if not result["has_manual_fundamentals"]:
            result["data_quality"] = "manual"
            result["data_source"]  = mv_src

    # ── Step 4: manual_targets.csv — analyst views, thesis ───────────────────
    mt_df  = load_manual_targets()
    mt_row = _get_manual_row(mt_df, fund_ticker)

    if mt_row is not None:
        result["has_manual_targets"] = True
        for col in ["analyst", "recommendation", "thesis_status", "priority",
                    "next_earnings", "bull_case", "base_case", "bear_case",
                    "key_risks", "key_metrics_to_watch"]:
            val = mt_row.get(col)
            if isinstance(val, str) and val.strip() and val.lower() not in ("nan", "none", ""):
                result[col] = val.strip()
        tp = mt_row.get("target_price")
        if tp is not None and not (isinstance(tp, float) and np.isnan(tp)):
            try:
                result["target_price"] = float(tp)
            except (TypeError, ValueError):
                pass
        ud = mt_row.get("upside_downside")
        if ud is not None and not (isinstance(ud, float) and np.isnan(ud)):
            try:
                result["upside_downside"] = float(ud)
            except (TypeError, ValueError):
                pass

    # Also check legacy analyst_coverage.csv as a further fallback for thesis
    if not result["has_manual_targets"]:
        cov = load_analyst_coverage()
        if not cov.empty and "ticker" in cov.columns:
            cov_rows = cov[cov["ticker"] == fund_ticker]
            if not cov_rows.empty:
                r = cov_rows.iloc[0]
                for col in ["analyst_name", "recommendation", "thesis_summary",
                            "key_risks", "next_earnings", "status"]:
                    val = r.get(col)
                    if isinstance(val, str) and val.strip():
                        # Map old names to new names
                        key_map = {"analyst_name": "analyst",
                                   "thesis_summary": "base_case",
                                   "status": "thesis_status"}
                        result[key_map.get(col, col)] = val.strip()
                tp_old = r.get("target_price_cad")
                if is_valid_val(tp_old):
                    result["target_price"] = float(tp_old)

    # ── Final metadata ────────────────────────────────────────────────────────
    result["last_updated"] = datetime.now().isoformat()
    return result


def is_valid_val(v) -> bool:
    """True if v is a real numeric value (not None / NaN / blank)."""
    if v is None:
        return False
    if isinstance(v, float) and np.isnan(v):
        return False
    try:
        f = float(v)
        return not np.isnan(f)
    except (TypeError, ValueError):
        return False


def get_data_source_label(fund: dict, metric: str) -> str:
    """
    Return the human-readable source label for a given metric in a fund dict.
    Used for displaying source attribution in pages.
    """
    manual_fund_metrics = {
        "revenue_ttm", "gross_profit", "ebitda", "ebit", "net_income_ttm",
        "fcf", "free_cash_flow", "gross_margin", "ebitda_margin", "ebit_margin",
        "profit_margin", "roe", "roic", "total_assets", "total_debt", "cash",
        "net_debt", "shares_outstanding",
    }
    manual_val_metrics = {
        "market_cap", "enterprise_value", "pe_trailing", "pe_forward",
        "ev_ebitda", "ev_ebit", "ev_revenue", "ev_sales", "ps_ratio",
        "pb_ratio", "fcf_yield", "dividend_yield", "net_debt_ebitda",
    }
    manual_target_metrics = {
        "recommendation", "target_price", "upside_downside", "thesis_status",
        "analyst", "priority", "next_earnings", "bull_case", "base_case",
        "bear_case", "key_risks", "key_metrics_to_watch",
    }
    price_metrics = {
        "price", "prev_close", "beta", "week_52_high", "week_52_low",
        "volume", "avg_volume",
    }

    val = fund.get(metric)
    if not is_valid_val(val) and val is None:
        return SRC_PREMIUM

    if metric in manual_target_metrics and fund.get("has_manual_targets"):
        return SRC_FIEUS
    if metric in manual_fund_metrics and fund.get("has_manual_fundamentals"):
        return fund.get("manual_fund_source") or SRC_CIQ
    if metric in manual_val_metrics and fund.get("has_manual_valuation"):
        return fund.get("manual_val_source") or SRC_CIQ
    if metric in price_metrics:
        return SRC_YF
    if val is not None:
        return SRC_YF
    return SRC_PREMIUM


# ═════════════════════════════════════════════════════════════════════════════
# RETURNS & RISK  (always computed from yfinance price history)
# ═════════════════════════════════════════════════════════════════════════════

def calculate_returns(prices: pd.Series) -> dict:
    """Calculate multi-period returns from price series."""
    empty = {"1d": None, "1w": None, "1m": None, "3m": None, "6m": None,
             "ytd": None, "1y": None, "3y": None, "5y": None}
    if prices is None or prices.empty or len(prices) < 2:
        return empty

    now = prices.iloc[-1]
    res = {}
    periods = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126,
               "1y": 252, "3y": 756, "5y": 1260}

    for label, days in periods.items():
        if len(prices) >= days:
            try:
                past = prices.iloc[-days]
                res[label] = (now / past - 1) if past and past > 0 else None
            except Exception:
                res[label] = None
        else:
            res[label] = None

    try:
        current_year = prices.index[-1].year
        ytd_prices = prices[prices.index.year == current_year]
        if len(ytd_prices) >= 2:
            start_y = ytd_prices.iloc[0]
            res["ytd"] = (now / start_y - 1) if start_y and start_y > 0 else None
        else:
            res["ytd"] = None
    except Exception:
        res["ytd"] = None

    return res


def calculate_risk_metrics(prices: pd.Series) -> dict:
    """Calculate annualised volatility, max drawdown, current drawdown from 52W high."""
    if prices is None or prices.empty or len(prices) < 30:
        return {"volatility_ann": None, "max_drawdown": None,
                "current_drawdown_from_52w": None}
    try:
        daily_ret = prices.pct_change().dropna()
        vol = float(daily_ret.std() * np.sqrt(252))
    except Exception:
        vol = None

    try:
        rolling_max = prices.cummax()
        dd = (prices - rolling_max) / rolling_max
        max_dd = float(dd.min())
    except Exception:
        max_dd = None

    try:
        high_52w = prices.tail(252).max() if len(prices) >= 252 else prices.max()
        cur_dd = float(prices.iloc[-1] / high_52w - 1) if high_52w and high_52w > 0 else None
    except Exception:
        cur_dd = None

    return {
        "volatility_ann":             vol if vol and not np.isnan(vol) else None,
        "max_drawdown":               max_dd if max_dd and not np.isnan(max_dd) else None,
        "current_drawdown_from_52w":  cur_dd if cur_dd and not np.isnan(cur_dd) else None,
    }


def fetch_portfolio_snapshot(tickers: list, period: str = "1y") -> pd.DataFrame:
    """Fetch price-based snapshot for many tickers (returns, risk, basic data)."""
    rows = []
    for ticker in tickers:
        meta = get_company_meta(ticker)
        fd = fetch_fundamentals(ticker)
        prices_df = fetch_price_history(ticker, period=period)
        prices = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
        rets = calculate_returns(prices)
        risk = calculate_risk_metrics(prices)

        rows.append({
            "ticker":     ticker,
            "name":       fd.get("name") or meta.get("name", ticker),
            "sector":     meta.get("sector", "N/A"),
            "is_etf":     bool(meta.get("is_etf", False)),
            "currency":   meta.get("currency", "CAD"),
            "price":      fd.get("price"),
            "market_cap": fd.get("market_cap"),
            "ev_ebitda":  fd.get("ev_ebitda"),
            "pe":         fd.get("pe_trailing") or fd.get("pe_forward"),
            "ret_1d":     rets.get("1d"),  "ret_1m": rets.get("1m"),
            "ret_3m":     rets.get("3m"),  "ret_6m": rets.get("6m"),
            "ret_ytd":    rets.get("ytd"), "ret_1y": rets.get("1y"),
            "volatility": risk.get("volatility_ann"),
            "drawdown":   risk.get("current_drawdown_from_52w"),
            "fundamentals": fd,
        })
    return pd.DataFrame(rows)


def get_last_refresh() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
