"""
macro_data.py — Macro indicators from FRED (US) and Bank of Canada.
Both APIs handled gracefully; returns sensible defaults on failure.
"""

import streamlit as st
import requests
import pandas as pd
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
BOC_BASE_URL  = "https://www.bankofcanada.ca/valet"
TIMEOUT = 8


def _get_fred_key() -> str:
    """Get FRED API key from Streamlit secrets or env."""
    try:
        return st.secrets.get("FRED_API_KEY", "")
    except Exception:
        return os.environ.get("FRED_API_KEY", "")


FRED_SERIES = {
    "fed_funds_rate":     "FEDFUNDS",
    "us_cpi":             "CPIAUCSL",
    "us_unemployment":    "UNRATE",
    "us_retail_sales":    "RSAFS",
    "us_10y_yield":       "GS10",
    "us_2y_yield":        "GS2",
    "us_consumer_conf":   "UMCSENT",
    "us_housing_starts":  "HOUST",
    "wti_oil":            "DCOILWTICO",
    "us_wages":           "CES0500000003",
    "cad_usd":            "DEXCAUS",
}

BOC_SERIES = {
    "boc_policy_rate":   "V39079",
    "ca_10y_yield":      "BD.CDN.10YR.DQ.YLD",
    "ca_2y_yield":       "BD.CDN.2YR.DQ.YLD",
    "cad_usd_boc":       "FXUSDCAD",
}


@st.cache_data(ttl=12*3600, show_spinner=False)
def _fetch_fred_series(series_id: str, limit: int = 60) -> pd.Series:
    key = _get_fred_key()
    if not key:
        return pd.Series(dtype=float)
    try:
        params = {"series_id": series_id, "api_key": key,
                  "file_type": "json", "limit": limit, "sort_order": "desc"}
        r = requests.get(FRED_BASE_URL, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return pd.Series(dtype=float)
        data = r.json().get("observations", [])
        if not data:
            return pd.Series(dtype=float)
        rows = []
        for obs in data:
            try:
                rows.append((pd.to_datetime(obs["date"]), float(obs["value"])))
            except (ValueError, KeyError):
                continue
        if not rows:
            return pd.Series(dtype=float)
        df = pd.DataFrame(rows, columns=["date", "value"]).sort_values("date")
        return pd.Series(df["value"].values, index=df["date"])
    except Exception as e:
        logger.warning(f"FRED fetch failed for {series_id}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=12*3600, show_spinner=False)
def _fetch_boc_series(series_id: str, recent: int = 60) -> pd.Series:
    try:
        url = f"{BOC_BASE_URL}/observations/{series_id}/json"
        r = requests.get(url, params={"recent": recent}, timeout=TIMEOUT)
        if r.status_code != 200:
            return pd.Series(dtype=float)
        data = r.json().get("observations", [])
        rows = []
        for obs in data:
            try:
                date = pd.to_datetime(obs["d"])
                val = None
                for k, v in obs.items():
                    if k != "d" and isinstance(v, dict) and "v" in v:
                        try:
                            val = float(v["v"])
                            break
                        except (ValueError, TypeError):
                            continue
                if val is not None:
                    rows.append((date, val))
            except Exception:
                continue
        if not rows:
            return pd.Series(dtype=float)
        df = pd.DataFrame(rows, columns=["date", "value"]).sort_values("date")
        return pd.Series(df["value"].values, index=df["date"])
    except Exception as e:
        logger.warning(f"BoC fetch failed for {series_id}: {e}")
        return pd.Series(dtype=float)


@st.cache_data(ttl=12*3600, show_spinner=False)
def get_macro_snapshot() -> dict:
    """Fetch all macro indicators."""
    snapshot = {
        "fred_available": bool(_get_fred_key()),
        "boc_available": True,
        "last_updated": datetime.now().isoformat(),
    }

    fred_data = {}
    for key, series_id in FRED_SERIES.items():
        s = _fetch_fred_series(series_id)
        fred_data[key + "_series"] = s
        fred_data[key] = float(s.iloc[-1]) if not s.empty else None
    snapshot.update(fred_data)

    cpi_s = snapshot.get("us_cpi_series", pd.Series(dtype=float))
    if len(cpi_s) >= 13:
        try:
            yoy = (cpi_s.iloc[-1] / cpi_s.iloc[-13] - 1) * 100
            snapshot["us_cpi_yoy"] = float(yoy)
        except Exception:
            snapshot["us_cpi_yoy"] = None
    else:
        snapshot["us_cpi_yoy"] = None

    boc_data = {}
    boc_failures = 0
    for key, series_id in BOC_SERIES.items():
        s = _fetch_boc_series(series_id)
        boc_data[key + "_series"] = s
        boc_data[key] = float(s.iloc[-1]) if not s.empty else None
        if s.empty:
            boc_failures += 1
    snapshot.update(boc_data)
    if boc_failures == len(BOC_SERIES):
        snapshot["boc_available"] = False

    if snapshot.get("us_10y_yield") is not None and snapshot.get("us_2y_yield") is not None:
        snapshot["us_yield_curve"] = snapshot["us_10y_yield"] - snapshot["us_2y_yield"]
    else:
        snapshot["us_yield_curve"] = None

    if snapshot.get("ca_10y_yield") is not None and snapshot.get("ca_2y_yield") is not None:
        snapshot["ca_yield_curve"] = snapshot["ca_10y_yield"] - snapshot["ca_2y_yield"]
    else:
        snapshot["ca_yield_curve"] = None

    return snapshot


def compute_macro_regime(snapshot: dict) -> dict:
    """0-100 regime score and label."""
    score = 50
    signals = []

    yc = snapshot.get("us_yield_curve")
    if yc is not None:
        if yc < -0.5:
            score -= 15
            signals.append({"name": "US Yield Curve", "value": f"{yc:.2f}%",
                            "impact": "negative", "note": "Deeply inverted — recession signal"})
        elif yc < 0:
            score -= 8
            signals.append({"name": "US Yield Curve", "value": f"{yc:.2f}%",
                            "impact": "slightly_negative", "note": "Inverted"})
        elif yc < 1:
            signals.append({"name": "US Yield Curve", "value": f"{yc:.2f}%",
                            "impact": "neutral", "note": "Flat"})
        else:
            score += 8
            signals.append({"name": "US Yield Curve", "value": f"{yc:.2f}%",
                            "impact": "positive", "note": "Healthy positive slope"})

    cpi = snapshot.get("us_cpi_yoy")
    if cpi is not None:
        if cpi > 5:
            score -= 10
            signals.append({"name": "US Inflation", "value": f"{cpi:.1f}%",
                            "impact": "negative", "note": "High inflation pressures Fed tightening"})
        elif cpi > 3:
            score -= 4
            signals.append({"name": "US Inflation", "value": f"{cpi:.1f}%",
                            "impact": "slightly_negative", "note": "Above Fed 2% target"})
        elif cpi >= 1.5:
            score += 6
            signals.append({"name": "US Inflation", "value": f"{cpi:.1f}%",
                            "impact": "positive", "note": "Near Fed target"})
        else:
            signals.append({"name": "US Inflation", "value": f"{cpi:.1f}%",
                            "impact": "mixed", "note": "Below target — disinflation risk"})

    unr = snapshot.get("us_unemployment")
    if unr is not None:
        if unr > 6:
            score -= 12
            signals.append({"name": "US Unemployment", "value": f"{unr:.1f}%",
                            "impact": "negative", "note": "Elevated unemployment"})
        elif unr > 4.5:
            signals.append({"name": "US Unemployment", "value": f"{unr:.1f}%",
                            "impact": "neutral", "note": "Normalizing"})
        else:
            score += 5
            signals.append({"name": "US Unemployment", "value": f"{unr:.1f}%",
                            "impact": "positive", "note": "Tight labor market"})

    ff = snapshot.get("fed_funds_rate")
    if ff is not None:
        if ff > 5:
            score -= 6
            signals.append({"name": "Fed Funds Rate", "value": f"{ff:.2f}%",
                            "impact": "slightly_negative", "note": "Restrictive policy"})
        elif ff < 1:
            score += 4
            signals.append({"name": "Fed Funds Rate", "value": f"{ff:.2f}%",
                            "impact": "positive", "note": "Accommodative policy"})
        else:
            signals.append({"name": "Fed Funds Rate", "value": f"{ff:.2f}%",
                            "impact": "neutral", "note": "Neutral policy zone"})

    boc = snapshot.get("boc_policy_rate")
    if boc is not None:
        signals.append({"name": "BoC Policy Rate", "value": f"{boc:.2f}%",
                        "impact": "neutral" if 2 < boc < 5 else "slightly_negative",
                        "note": "Bank of Canada overnight target"})

    wti = snapshot.get("wti_oil")
    if wti is not None:
        if wti > 100:
            score -= 5
            signals.append({"name": "WTI Crude", "value": f"${wti:.0f}",
                            "impact": "slightly_negative", "note": "Elevated oil prices"})
        elif wti < 50:
            score -= 3
            signals.append({"name": "WTI Crude", "value": f"${wti:.0f}",
                            "impact": "mixed", "note": "Low oil — Canadian energy headwind"})
        else:
            signals.append({"name": "WTI Crude", "value": f"${wti:.0f}",
                            "impact": "neutral", "note": "Stable range"})

    cc = snapshot.get("us_consumer_conf")
    if cc is not None:
        if cc < 70:
            score -= 5
            signals.append({"name": "Consumer Confidence", "value": f"{cc:.1f}",
                            "impact": "negative", "note": "Weak sentiment"})
        elif cc > 100:
            score += 4
            signals.append({"name": "Consumer Confidence", "value": f"{cc:.1f}",
                            "impact": "positive", "note": "Strong sentiment"})

    score = max(0, min(100, score))
    if score >= 70:
        regime, color = "Favorable", "#2DB87E"
    elif score >= 50:
        regime, color = "Neutral", "#FFB81C"
    elif score >= 25:
        regime, color = "Unfavorable", "#E07B39"
    else:
        regime, color = "Stress", "#E54B4B"

    return {"score": int(score), "regime": regime, "color": color, "signals": signals}


SECTOR_MACRO_IMPACT = {
    "Technology": {"rates_up": "negative", "rates_down": "positive",
                   "inflation_up": "slightly_negative", "growth_up": "positive",
                   "note": "Long-duration assets sensitive to rates"},
    "Financials": {"rates_up": "positive", "rates_down": "negative",
                   "inflation_up": "mixed", "growth_up": "positive",
                   "note": "Banks benefit from steeper yield curves"},
    "Consumer Staples": {"rates_up": "slightly_negative", "rates_down": "slightly_positive",
                          "inflation_up": "mixed", "growth_up": "neutral",
                          "note": "Defensive — pricing power matters"},
    "Consumer Discretionary": {"rates_up": "negative", "rates_down": "positive",
                                "inflation_up": "negative", "growth_up": "positive",
                                "note": "Cyclical — sensitive to consumer spending"},
    "Industrials": {"rates_up": "slightly_negative", "rates_down": "positive",
                    "inflation_up": "neutral", "growth_up": "positive",
                    "note": "Cyclical — capex and global trade exposure"},
    "Real Estate": {"rates_up": "negative", "rates_down": "positive",
                    "inflation_up": "mixed", "growth_up": "positive",
                    "note": "Highly rate-sensitive; inflation can be a hedge"},
    "Utilities": {"rates_up": "negative", "rates_down": "positive",
                  "inflation_up": "slightly_negative", "growth_up": "neutral",
                  "note": "Bond proxies — rate-sensitive defensives"},
    "Materials": {"rates_up": "slightly_negative", "rates_down": "positive",
                  "inflation_up": "positive", "growth_up": "positive",
                  "note": "Commodity-linked; benefits from inflation"},
    "Communication Services": {"rates_up": "slightly_negative", "rates_down": "positive",
                                 "inflation_up": "neutral", "growth_up": "positive",
                                 "note": "Mix of defensive (telecom) and growth (media)"},
    "Healthcare": {"rates_up": "slightly_negative", "rates_down": "slightly_positive",
                   "inflation_up": "mixed", "growth_up": "neutral",
                   "note": "Defensive with secular growth tailwinds"},
}


def get_sector_macro_score(sector: str, regime: str) -> int:
    base = {"Favorable": 75, "Neutral": 60, "Unfavorable": 45, "Stress": 30}.get(regime, 50)
    cyclical = {"Consumer Discretionary", "Industrials", "Materials", "Financials"}
    defensive = {"Consumer Staples", "Utilities", "Healthcare"}
    if regime in ("Unfavorable", "Stress") and sector in defensive:
        base += 10
    elif regime == "Favorable" and sector in cyclical:
        base += 5
    elif regime == "Stress" and sector in cyclical:
        base -= 10
    return max(0, min(100, base))
