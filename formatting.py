"""
src/utils/formatting.py
Formatting helpers for financial values, percentages, multiples.
"""

def fmt_currency(value, currency='CAD', decimals=2):
    """Format a number as currency string."""
    if value is None or value != value:  # NaN check
        return 'N/A'
    try:
        v = float(value)
        symbol = '$' if currency in ('CAD', 'USD') else '€' if currency == 'EUR' else '$'
        if abs(v) >= 1e9:
            return f"{symbol}{v/1e9:.{decimals}f}B"
        elif abs(v) >= 1e6:
            return f"{symbol}{v/1e6:.{decimals}f}M"
        elif abs(v) >= 1e3:
            return f"{symbol}{v/1e3:.{decimals}f}K"
        return f"{symbol}{v:.{decimals}f}"
    except (TypeError, ValueError):
        return 'N/A'


def fmt_pct(value, decimals=1, signed=False):
    """Format a decimal as percentage string."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
        if v != v:
            return 'N/A'
        prefix = '+' if signed and v > 0 else ''
        return f"{prefix}{v * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return 'N/A'


def fmt_multiple(value, decimals=1, suffix='x'):
    """Format a number as a financial multiple."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
        if v != v or v <= 0:
            return 'N/A'
        return f"{v:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return 'N/A'


def fmt_number(value, decimals=1, suffix=''):
    """Format a generic number."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
        if v != v:
            return 'N/A'
        return f"{v:,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return 'N/A'


def fmt_large(value, currency='CAD'):
    """Format large financial values with B/M suffix."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
        if v != v:
            return 'N/A'
        symbol = '$'
        if abs(v) >= 1e12:
            return f"{symbol}{v/1e12:.2f}T"
        elif abs(v) >= 1e9:
            return f"{symbol}{v/1e9:.2f}B"
        elif abs(v) >= 1e6:
            return f"{symbol}{v/1e6:.1f}M"
        elif abs(v) >= 1e3:
            return f"{symbol}{v/1e3:.0f}K"
        return f"{symbol}{v:.2f}"
    except (TypeError, ValueError):
        return 'N/A'


def color_return(value: float) -> str:
    """Return CSS color string for a return value."""
    if value is None or value != value:
        return '#888888'
    return '#00d4aa' if value > 0 else '#ff4b4b' if value < 0 else '#888888'


def format_delta_pct(value: float) -> str:
    """Format return as +/- percentage."""
    if value is None or value != value:
        return 'N/A'
    return f"{value:+.2%}"
