"""
market_data.py — Market data provider via yfinance.

Features:
  - Centralized ticker mapping (fund format → yfinance format)
  - Streamlit caching (auto-refresh every 4h for prices, 24h for fundamentals)
  - Universe loaded from config/universe.csv with auto-merge of new tickers
  - Robust error handling: never raises, always returns sensible defaults

To add a new company: edit config/universe.csv and add a line.
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
UNIVERSE_CSV = ROOT / "config" / "universe.csv"
ANALYST_CSV  = ROOT / "config" / "analyst_coverage.csv"


SPECIAL_TICKER_MAP = {
    "TSX:QBR.B":  "QBR-B.TO", "TSX:BBD.B":  "BBD-B.TO",
    "TSX:CSH.UN": "CSH-UN.TO", "TSX:GIB.A":  "GIB-A.TO",
    "TSX:CCL.B":  "CCL-B.TO", "TSX:CAR.UN": "CAR-UN.TO",
    "TSX:RCI.B":  "RCI-B.TO", "TSX:CTC.A":  "CTC-A.TO",
    "NASDAQ:LULU": "LULU", "NYSE:GIL": "GIL",
}


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


@st.cache_data(ttl=300, show_spinner=False)
def load_universe() -> pd.DataFrame:
    """Load universe.csv. Cached 5 min."""
    if not UNIVERSE_CSV.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(UNIVERSE_CSV)
        if "is_etf" in df.columns:
            df["is_etf"] = df["is_etf"].astype(str).str.lower().isin(["true", "1", "yes"])
        return df
    except Exception as e:
        logger.error(f"Failed to load universe: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def load_analyst_coverage() -> pd.DataFrame:
    """Load analyst_coverage.csv. Cached 5 min."""
    if not ANALYST_CSV.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(ANALYST_CSV)
    except Exception as e:
        logger.error(f"Failed to load coverage: {e}")
        return pd.DataFrame()


def get_company_meta(ticker: str) -> dict:
    """Return universe metadata for a ticker."""
    df = load_universe()
    if df.empty:
        return {}
    rows = df[df["ticker"] == ticker]
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


@st.cache_data(ttl=4*3600, show_spinner=False)
def fetch_price_history(fund_ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch OHLCV history. Returns empty DataFrame on error."""
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


EMPTY_FUNDAMENTALS = {
    "ticker_fund": None, "ticker_yf": None, "name": None, "sector": None,
    "industry": None, "currency": None, "exchange": None, "country": None,
    "description": None, "employees": None, "website": None,
    "price": None, "prev_close": None, "open": None, "day_high": None,
    "day_low": None, "week_52_high": None, "week_52_low": None,
    "volume": None, "avg_volume": None, "market_cap": None,
    "enterprise_value": None, "shares_outstanding": None, "float_shares": None,
    "pe_trailing": None, "pe_forward": None, "pb_ratio": None, "ps_ratio": None,
    "ev_ebitda": None, "ev_revenue": None, "peg_ratio": None,
    "dividend_yield": None, "dividend_rate": None, "payout_ratio": None,
    "profit_margin": None, "operating_margin": None, "gross_margin": None,
    "ebitda_margin": None, "roe": None, "roa": None, "roic": None,
    "revenue_ttm": None, "revenue_growth_yoy": None, "ebitda": None,
    "net_income_ttm": None, "eps_ttm": None, "eps_forward": None,
    "earnings_growth": None,
    "cash": None, "total_debt": None, "net_debt": None,
    "current_ratio": None, "quick_ratio": None, "debt_to_equity": None,
    "book_value": None,
    "fcf": None, "operating_cashflow": None,
    "beta": None,
    "data_source": "yfinance", "data_quality": "missing",
}


@st.cache_data(ttl=24*3600, show_spinner=False)
def fetch_fundamentals(fund_ticker: str) -> dict:
    """Fetch fundamentals. Always returns dict — None for missing fields."""
    meta = get_company_meta(fund_ticker)
    yf_ticker = get_yf_ticker(fund_ticker, meta.get("ticker_yf"))
    result = {**EMPTY_FUNDAMENTALS, "ticker_fund": fund_ticker, "ticker_yf": yf_ticker}

    try:
        ticker = yf.Ticker(yf_ticker)
        info = ticker.info or {}
    except Exception as e:
        logger.warning(f"Fundamentals fetch failed for {fund_ticker}: {e}")
        result["data_quality"] = "error"
        return result

    if not info or not isinstance(info, dict):
        return result

    mapping = {
        "name": ["longName", "shortName"],
        "sector": ["sector"], "industry": ["industry"],
        "currency": ["currency"], "exchange": ["exchange"], "country": ["country"],
        "description": ["longBusinessSummary"], "employees": ["fullTimeEmployees"],
        "website": ["website"],
        "price": ["currentPrice", "regularMarketPrice"],
        "prev_close": ["previousClose"], "open": ["open"],
        "day_high": ["dayHigh"], "day_low": ["dayLow"],
        "week_52_high": ["fiftyTwoWeekHigh"], "week_52_low": ["fiftyTwoWeekLow"],
        "volume": ["volume"], "avg_volume": ["averageVolume"],
        "market_cap": ["marketCap"], "enterprise_value": ["enterpriseValue"],
        "shares_outstanding": ["sharesOutstanding"], "float_shares": ["floatShares"],
        "pe_trailing": ["trailingPE"], "pe_forward": ["forwardPE"],
        "pb_ratio": ["priceToBook"], "ps_ratio": ["priceToSalesTrailing12Months"],
        "ev_ebitda": ["enterpriseToEbitda"], "ev_revenue": ["enterpriseToRevenue"],
        "peg_ratio": ["pegRatio"],
        "dividend_yield": ["dividendYield"], "dividend_rate": ["dividendRate"],
        "payout_ratio": ["payoutRatio"],
        "profit_margin": ["profitMargins"], "operating_margin": ["operatingMargins"],
        "gross_margin": ["grossMargins"], "ebitda_margin": ["ebitdaMargins"],
        "roe": ["returnOnEquity"], "roa": ["returnOnAssets"],
        "revenue_ttm": ["totalRevenue"], "revenue_growth_yoy": ["revenueGrowth"],
        "ebitda": ["ebitda"], "net_income_ttm": ["netIncomeToCommon"],
        "eps_ttm": ["trailingEps"], "eps_forward": ["forwardEps"],
        "earnings_growth": ["earningsGrowth"],
        "cash": ["totalCash"], "total_debt": ["totalDebt"],
        "current_ratio": ["currentRatio"], "quick_ratio": ["quickRatio"],
        "debt_to_equity": ["debtToEquity"], "book_value": ["bookValue"],
        "fcf": ["freeCashflow"], "operating_cashflow": ["operatingCashflow"],
        "beta": ["beta"],
    }

    for key, sources in mapping.items():
        for src in sources:
            val = info.get(src)
            if val is not None and val != "":
                result[key] = val
                break

    if result["total_debt"] is not None or result["cash"] is not None:
        result["net_debt"] = (result["total_debt"] or 0) - (result["cash"] or 0)

    dy = result["dividend_yield"]
    if dy is not None:
        try:
            dy_v = float(dy)
            if dy_v > 1:
                result["dividend_yield"] = dy_v / 100
        except (TypeError, ValueError):
            pass

    result["data_quality"] = "live"
    result["last_updated"] = datetime.now().isoformat()
    return result


def calculate_returns(prices: pd.Series) -> dict:
    """Calculate multi-period returns. Returns dict with None for missing."""
    if prices is None or prices.empty or len(prices) < 2:
        return {"1d": None, "1w": None, "1m": None, "3m": None, "6m": None,
                "ytd": None, "1y": None, "3y": None, "5y": None}

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
    """Calculate volatility, max drawdown, current drawdown."""
    if prices is None or prices.empty or len(prices) < 30:
        return {"volatility_ann": None, "max_drawdown": None,
                "current_drawdown_from_52w": None}

    try:
        daily_ret = prices.pct_change().dropna()
        vol = daily_ret.std() * np.sqrt(252)
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
        "volatility_ann": float(vol) if vol is not None and not np.isnan(vol) else None,
        "max_drawdown": max_dd if max_dd is not None and not np.isnan(max_dd) else None,
        "current_drawdown_from_52w": cur_dd if cur_dd is not None and not np.isnan(cur_dd) else None,
    }


def fetch_portfolio_snapshot(tickers: list, period: str = "1y") -> pd.DataFrame:
    """Fetch fundamentals + returns + risk for many tickers."""
    rows = []
    for ticker in tickers:
        meta = get_company_meta(ticker)
        fd = fetch_fundamentals(ticker)
        prices_df = fetch_price_history(ticker, period=period)
        prices = prices_df["Close"] if not prices_df.empty else pd.Series(dtype=float)
        rets = calculate_returns(prices)
        risk = calculate_risk_metrics(prices)

        rows.append({
            "ticker": ticker,
            "name": fd.get("name") or meta.get("name", ticker),
            "sector": meta.get("sector", "N/A"),
            "is_etf": bool(meta.get("is_etf", False)),
            "currency": meta.get("currency", "CAD"),
            "price": fd.get("price"),
            "market_cap": fd.get("market_cap"),
            "ev_ebitda": fd.get("ev_ebitda"),
            "pe": fd.get("pe_trailing") or fd.get("pe_forward"),
            "ret_1d": rets.get("1d"), "ret_1m": rets.get("1m"),
            "ret_3m": rets.get("3m"), "ret_6m": rets.get("6m"),
            "ret_ytd": rets.get("ytd"), "ret_1y": rets.get("1y"),
            "volatility": risk.get("volatility_ann"),
            "drawdown": risk.get("current_drawdown_from_52w"),
            "fundamentals": fd,
        })
    return pd.DataFrame(rows)


def get_last_refresh() -> str:
    """Return current timestamp string. Used by pages for 'last updated' display."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
