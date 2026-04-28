"""
src/utils/validation.py
Data validation and quality helpers.
"""

import pandas as pd
import numpy as np
from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, return default if not possible."""
    if value is None:
        return default
    try:
        v = float(value)
        return default if np.isnan(v) or np.isinf(v) else v
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def is_valid_number(value: Any) -> bool:
    """Return True if value is a finite real number."""
    try:
        v = float(value)
        return not (np.isnan(v) or np.isinf(v))
    except (TypeError, ValueError):
        return False


def check_data_completeness(data: dict, required_fields: list) -> dict:
    """
    Check which required fields are present and valid.
    Returns {'field': True/False} dict.
    """
    return {
        field: is_valid_number(data.get(field)) or (
            data.get(field) is not None and str(data.get(field)).strip() not in ('', 'None', 'nan')
        )
        for field in required_fields
    }


def label_data_source(value: Any, source: str = 'yfinance') -> dict:
    """Return dict with value, source, and quality flag."""
    is_valid = is_valid_number(value) if value is not None else False
    return {
        'value': value,
        'source': source if is_valid else 'N/A',
        'quality': 'actual' if is_valid else 'missing',
        'display': str(value) if is_valid else 'N/A'
    }


def clip_extreme(value: float, lower: float, upper: float) -> float:
    """Clip a value within [lower, upper] bounds for scoring safety."""
    return max(lower, min(upper, value))
