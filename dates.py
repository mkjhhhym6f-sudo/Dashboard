"""
src/utils/dates.py
Date utility helpers for financial periods.
"""

from datetime import datetime, date, timedelta
import pandas as pd


def get_ytd_start() -> str:
    """Return first trading day of the current year as string YYYY-MM-DD."""
    return f"{datetime.today().year}-01-01"


def get_period_start(period: str) -> str:
    """Convert period string (1mo, 3mo, 6mo, 1y, 3y, 5y) to start date."""
    today = datetime.today()
    mapping = {
        '1d': today - timedelta(days=1),
        '1mo': today - timedelta(days=30),
        '3mo': today - timedelta(days=91),
        '6mo': today - timedelta(days=182),
        '1y': today - timedelta(days=365),
        '3y': today - timedelta(days=3 * 365),
        '5y': today - timedelta(days=5 * 365),
        'ytd': datetime(today.year, 1, 1),
        'max': datetime(2000, 1, 1),
    }
    dt = mapping.get(period, today - timedelta(days=365))
    return dt.strftime('%Y-%m-%d')


def trading_days_ago(n: int) -> str:
    """Approximate n trading days ago (no calendar; uses 252 days/year ratio)."""
    calendar_days = int(n * 365 / 252) + 1
    return (datetime.today() - timedelta(days=calendar_days)).strftime('%Y-%m-%d')


def format_date(dt) -> str:
    """Safely format a date or string to YYYY-MM-DD."""
    if dt is None:
        return 'N/A'
    try:
        if isinstance(dt, (datetime, date)):
            return dt.strftime('%Y-%m-%d')
        return str(dt)[:10]
    except Exception:
        return 'N/A'


def fiscal_quarter(dt=None) -> str:
    """Return current fiscal quarter string e.g. '2024Q3'."""
    if dt is None:
        dt = datetime.today()
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{q}"
