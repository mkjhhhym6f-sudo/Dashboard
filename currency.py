"""
src/utils/currency.py
Currency conversion helpers (CAD/USD).
Uses live rate from yfinance if available, falls back to cached rate.
"""

import yfinance as yf
import os, json
from datetime import datetime, timedelta

_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cache', 'fx_rate.json')
_DEFAULT_CADUSD = 0.73  # fallback


def get_cadusd_rate() -> float:
    """Return the current CAD/USD exchange rate."""
    # Try cache first (1h TTL)
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                data = json.load(f)
            cached_at = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_at < timedelta(hours=1):
                return float(data.get('cadusd', _DEFAULT_CADUSD))
        except Exception:
            pass

    # Fetch from yfinance
    try:
        ticker = yf.Ticker("CADUSD=X")
        rate = ticker.info.get('regularMarketPrice') or ticker.fast_info.get('lastPrice')
        if rate and 0.5 < rate < 1.5:
            os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
            with open(_CACHE_PATH, 'w') as f:
                json.dump({'cadusd': rate, 'timestamp': datetime.now().isoformat()}, f)
            return float(rate)
    except Exception:
        pass

    return _DEFAULT_CADUSD


def get_usdcad_rate() -> float:
    """Return the current USD/CAD exchange rate."""
    cadusd = get_cadusd_rate()
    return 1.0 / cadusd if cadusd > 0 else 1.36


def to_cad(value_usd: float) -> float:
    """Convert USD amount to CAD."""
    return value_usd * get_usdcad_rate()


def to_usd(value_cad: float) -> float:
    """Convert CAD amount to USD."""
    return value_cad * get_cadusd_rate()


def normalize_to_cad(value: float, currency: str) -> float:
    """Convert any supported currency to CAD."""
    if currency.upper() == 'CAD':
        return value
    elif currency.upper() == 'USD':
        return to_cad(value)
    else:
        return value  # unsupported — return as-is
