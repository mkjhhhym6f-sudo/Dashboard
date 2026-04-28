"""
formatting.py — Robust formatters for SIF Analytics.
All return 'N/A' on invalid/missing data — never raise.
"""

import math


def is_valid(v) -> bool:
    """True if v is a finite real number."""
    if v is None:
        return False
    try:
        f = float(v)
        return not (math.isnan(f) or math.isinf(f))
    except (TypeError, ValueError):
        return False


def safe_float(v, default: float = 0.0) -> float:
    if not is_valid(v):
        return default
    return float(v)


def fmt_currency(value, currency: str = "CAD", decimals: int = 2, na: str = "N/A") -> str:
    if not is_valid(value):
        return na
    v = float(value)
    if abs(v) >= 1e12:
        return f"${v/1e12:.{decimals}f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.{decimals}f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.{decimals}f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:,.{decimals}f}K"
    return f"${v:.{decimals}f}"


def fmt_price(value, na: str = "N/A") -> str:
    if not is_valid(value):
        return na
    return f"${float(value):.2f}"


def fmt_pct(value, decimals: int = 1, signed: bool = False, na: str = "N/A") -> str:
    """Format decimal as percentage. 0.15 → '15.0%'"""
    if not is_valid(value):
        return na
    v = float(value)
    sign = "+" if signed and v > 0 else ""
    return f"{sign}{v * 100:.{decimals}f}%"


def fmt_pct_raw(value, decimals: int = 1, signed: bool = False, na: str = "N/A") -> str:
    """Format value already in %. 15 → '15.0%'"""
    if not is_valid(value):
        return na
    v = float(value)
    sign = "+" if signed and v > 0 else ""
    return f"{sign}{v:.{decimals}f}%"


def fmt_multiple(value, decimals: int = 1, suffix: str = "x", na: str = "N/A") -> str:
    if not is_valid(value):
        return na
    v = float(value)
    if v <= 0:
        return na
    return f"{v:.{decimals}f}{suffix}"


def fmt_number(value, decimals: int = 1, suffix: str = "", na: str = "N/A") -> str:
    if not is_valid(value):
        return na
    return f"{float(value):,.{decimals}f}{suffix}"


def fmt_large(value, decimals: int = 1, na: str = "N/A") -> str:
    """Alias for fmt_currency with smart magnitude (B/M/K)."""
    return fmt_currency(value, decimals=decimals, na=na)


def fmt_delta(value, decimals: int = 2, na: str = "N/A") -> str:
    """Format a return as +X.XX%/-X.XX%. Decimal input (0.05 → +5.00%)."""
    if not is_valid(value):
        return na
    return f"{float(value)*100:+.{decimals}f}%"
