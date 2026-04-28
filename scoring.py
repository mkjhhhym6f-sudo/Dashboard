"""
Scoring Model — Institutional-grade composite score (0-100)

Score Breakdown:
  Quality Score:       25%  (ROIC, margins, FCF conversion)
  Valuation Score:     25%  (multiples vs history and peers)
  Growth Score:        20%  (revenue, earnings, FCF growth)
  Balance Sheet Score: 15%  (leverage, coverage, liquidity)
  Momentum Score:      10%  (price momentum, relative strength)
  Macro/Sector Fit:     5%  (regime alignment)
"""

import pandas as pd
import numpy as np
from typing import Optional


# ─── Scoring weights ──────────────────────────────────────────────────────────
WEIGHTS = {
    "quality":      0.25,
    "valuation":    0.25,
    "growth":       0.20,
    "balance_sheet":0.15,
    "momentum":     0.10,
    "macro_fit":    0.05,
}

# ─── Industry-adjusted benchmarks ─────────────────────────────────────────────
SECTOR_BENCHMARKS = {
    "Technology": {
        "gross_margin_target": 60, "ebitda_margin_target": 25, "roic_target": 15,
        "ev_ebitda_fair": 25, "net_debt_ebitda_max": 2.5
    },
    "Financials": {
        "roe_target": 14, "roa_target": 1.0, "pe_fair": 12,
        "pb_fair": 1.5, "efficiency_ratio_target": 55
    },
    "Consumer_Staples": {
        "gross_margin_target": 30, "ebitda_margin_target": 15, "roic_target": 12,
        "ev_ebitda_fair": 16, "net_debt_ebitda_max": 3.0
    },
    "Consumer_Discretionary": {
        "gross_margin_target": 35, "ebitda_margin_target": 15, "roic_target": 12,
        "ev_ebitda_fair": 14, "net_debt_ebitda_max": 3.5
    },
    "Industrials": {
        "gross_margin_target": 30, "ebitda_margin_target": 18, "roic_target": 10,
        "ev_ebitda_fair": 15, "net_debt_ebitda_max": 3.0
    },
    "Real_Estate": {
        "gross_margin_target": 50, "ebitda_margin_target": 40, "roic_target": 6,
        "ev_ebitda_fair": 20, "net_debt_ebitda_max": 8.0  # REITs use more leverage
    },
    "Utilities": {
        "gross_margin_target": 40, "ebitda_margin_target": 35, "roic_target": 7,
        "ev_ebitda_fair": 14, "net_debt_ebitda_max": 5.0
    },
    "Materials": {
        "gross_margin_target": 30, "ebitda_margin_target": 20, "roic_target": 10,
        "ev_ebitda_fair": 12, "net_debt_ebitda_max": 2.5
    },
    "Communication_Services": {
        "gross_margin_target": 55, "ebitda_margin_target": 35, "roic_target": 8,
        "ev_ebitda_fair": 8, "net_debt_ebitda_max": 4.0
    },
    "Healthcare": {
        "gross_margin_target": 45, "ebitda_margin_target": 18, "roic_target": 10,
        "ev_ebitda_fair": 15, "net_debt_ebitda_max": 3.0
    },
    "Default": {
        "gross_margin_target": 35, "ebitda_margin_target": 20, "roic_target": 10,
        "ev_ebitda_fair": 14, "net_debt_ebitda_max": 3.5
    },
}


def _safe(val, default=None):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    return val


def score_quality(data: dict, sector: str = "Default") -> dict:
    """
    Quality Score (0-100): ROIC, margins, FCF conversion
    """
    bench = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])
    points = 0
    max_pts = 0
    drivers = []
    penalties = []

    # ROIC or ROE/ROA fallback
    roic = _safe(data.get("roic")) or _safe(data.get("roe"))
    if roic is not None:
        roic_pct = roic * 100 if abs(roic) < 1 else roic
        target = bench.get("roic_target", 10)
        if roic_pct >= target * 1.5:
            points += 25; drivers.append(f"Excellent ROIC/ROE ({roic_pct:.1f}% vs {target}% target)")
        elif roic_pct >= target:
            points += 18; drivers.append(f"Good ROIC/ROE ({roic_pct:.1f}%)")
        elif roic_pct >= target * 0.5:
            points += 10; drivers.append(f"Moderate ROIC/ROE ({roic_pct:.1f}%)")
        else:
            points += 0; penalties.append(f"Weak ROIC/ROE ({roic_pct:.1f}%)")
        max_pts += 25

    # EBITDA margin
    ebitda_m = _safe(data.get("ebitda_margin"))
    if ebitda_m is not None:
        em_pct = ebitda_m * 100 if abs(ebitda_m) < 1 else ebitda_m
        target = bench.get("ebitda_margin_target", 20)
        if em_pct >= target * 1.5:
            points += 20; drivers.append(f"Strong EBITDA margin ({em_pct:.1f}%)")
        elif em_pct >= target:
            points += 14; drivers.append(f"Good EBITDA margin ({em_pct:.1f}%)")
        elif em_pct >= target * 0.5:
            points += 7
        else:
            penalties.append(f"Weak EBITDA margin ({em_pct:.1f}%)")
        max_pts += 20

    # Gross margin
    gross_m = _safe(data.get("gross_margin"))
    if gross_m is not None:
        gm_pct = gross_m * 100 if abs(gross_m) < 1 else gross_m
        target = bench.get("gross_margin_target", 35)
        if gm_pct >= target:
            points += 15; drivers.append(f"Healthy gross margin ({gm_pct:.1f}%)")
        elif gm_pct >= target * 0.7:
            points += 8
        else:
            penalties.append(f"Low gross margin ({gm_pct:.1f}%)")
        max_pts += 15

    # FCF conversion (FCF / Net Income)
    fcf = _safe(data.get("fcf"))
    net_inc = _safe(data.get("net_income_ttm"))
    if fcf is not None and net_inc and net_inc > 0:
        conversion = fcf / net_inc
        if conversion >= 1.0:
            points += 20; drivers.append(f"Excellent FCF conversion ({conversion:.1f}x)")
        elif conversion >= 0.7:
            points += 12; drivers.append(f"Good FCF conversion ({conversion:.1f}x)")
        elif conversion >= 0.4:
            points += 5
        else:
            penalties.append(f"Poor FCF conversion ({conversion:.1f}x)")
        max_pts += 20

    # Operating margin
    op_m = _safe(data.get("operating_margin"))
    if op_m is not None:
        op_pct = op_m * 100 if abs(op_m) < 1 else op_m
        if op_pct > 20:
            points += 20; drivers.append(f"High operating margin ({op_pct:.1f}%)")
        elif op_pct > 10:
            points += 12
        elif op_pct > 0:
            points += 5
        else:
            penalties.append(f"Negative operating margin ({op_pct:.1f}%)")
        max_pts += 20

    score = (points / max_pts * 100) if max_pts > 0 else 50
    return {"score": round(score), "drivers": drivers, "penalties": penalties, "points": points, "max_pts": max_pts}


def score_valuation(data: dict, sector: str = "Default") -> dict:
    """
    Valuation Score (0-100): Lower multiple vs history/peers = higher score
    """
    bench = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])
    points = 0
    max_pts = 0
    drivers = []
    penalties = []

    # EV/EBITDA
    ev_ebitda = _safe(data.get("ev_ebitda"))
    if ev_ebitda is not None and ev_ebitda > 0:
        fair = bench.get("ev_ebitda_fair", 14)
        if ev_ebitda <= fair * 0.7:
            points += 30; drivers.append(f"Cheap EV/EBITDA ({ev_ebitda:.1f}x vs {fair}x fair)")
        elif ev_ebitda <= fair:
            points += 20; drivers.append(f"Fair EV/EBITDA ({ev_ebitda:.1f}x)")
        elif ev_ebitda <= fair * 1.3:
            points += 10; penalties.append(f"Slightly elevated EV/EBITDA ({ev_ebitda:.1f}x)")
        elif ev_ebitda <= fair * 1.8:
            points += 5; penalties.append(f"Rich EV/EBITDA ({ev_ebitda:.1f}x)")
        else:
            penalties.append(f"Very expensive EV/EBITDA ({ev_ebitda:.1f}x — {ev_ebitda/fair:.1f}x fair)")
        max_pts += 30

    # P/E
    pe = _safe(data.get("pe_trailing")) or _safe(data.get("pe_forward"))
    if pe is not None and pe > 0:
        pe_fair = bench.get("pe_fair", 18)
        if pe <= pe_fair * 0.7:
            points += 25; drivers.append(f"Cheap P/E ({pe:.1f}x)")
        elif pe <= pe_fair:
            points += 18; drivers.append(f"Fair P/E ({pe:.1f}x)")
        elif pe <= pe_fair * 1.5:
            points += 8; penalties.append(f"Premium P/E ({pe:.1f}x)")
        else:
            penalties.append(f"Expensive P/E ({pe:.1f}x)")
        max_pts += 25

    # FCF yield
    fcf = _safe(data.get("fcf"))
    mkt_cap = _safe(data.get("market_cap"))
    if fcf is not None and mkt_cap and mkt_cap > 0:
        fcf_yield = (fcf / mkt_cap) * 100
        if fcf_yield >= 6:
            points += 25; drivers.append(f"High FCF yield ({fcf_yield:.1f}%)")
        elif fcf_yield >= 4:
            points += 18; drivers.append(f"Good FCF yield ({fcf_yield:.1f}%)")
        elif fcf_yield >= 2:
            points += 10
        elif fcf_yield >= 0:
            points += 3
        else:
            penalties.append(f"Negative FCF yield ({fcf_yield:.1f}%)")
        max_pts += 25

    # EV/Revenue
    ev_rev = _safe(data.get("ev_revenue"))
    if ev_rev is not None:
        if ev_rev <= 2:
            points += 20; drivers.append(f"Low EV/Revenue ({ev_rev:.1f}x)")
        elif ev_rev <= 5:
            points += 12
        elif ev_rev <= 10:
            points += 5
        else:
            penalties.append(f"High EV/Revenue ({ev_rev:.1f}x)")
        max_pts += 20

    score = (points / max_pts * 100) if max_pts > 0 else 50
    return {"score": round(score), "drivers": drivers, "penalties": penalties}


def score_growth(data: dict) -> dict:
    """
    Growth Score (0-100): Revenue, earnings, FCF growth
    """
    points = 0
    max_pts = 0
    drivers = []
    penalties = []

    # Revenue growth
    rev_growth = _safe(data.get("revenue_growth_yoy"))
    if rev_growth is not None:
        rg = rev_growth * 100 if abs(rev_growth) < 1 else rev_growth
        if rg >= 20:
            points += 35; drivers.append(f"Strong revenue growth ({rg:.1f}%)")
        elif rg >= 10:
            points += 25; drivers.append(f"Solid revenue growth ({rg:.1f}%)")
        elif rg >= 5:
            points += 15
        elif rg >= 0:
            points += 5
        else:
            penalties.append(f"Revenue declining ({rg:.1f}%)")
        max_pts += 35

    # EPS growth
    eps_growth = _safe(data.get("earnings_growth"))
    if eps_growth is not None:
        eg = eps_growth * 100 if abs(eps_growth) < 1 else eps_growth
        if eg >= 20:
            points += 35; drivers.append(f"Strong EPS growth ({eg:.1f}%)")
        elif eg >= 10:
            points += 25
        elif eg >= 0:
            points += 10
        else:
            penalties.append(f"EPS declining ({eg:.1f}%)")
        max_pts += 35

    # FCF growth (proxy via FCF margin)
    fcf = _safe(data.get("fcf"))
    rev = _safe(data.get("revenue_ttm"))
    if fcf is not None and rev and rev > 0:
        fcf_margin = (fcf / rev) * 100
        if fcf_margin >= 15:
            points += 30; drivers.append(f"High FCF margin ({fcf_margin:.1f}%)")
        elif fcf_margin >= 8:
            points += 20
        elif fcf_margin >= 3:
            points += 10
        else:
            penalties.append(f"Low FCF margin ({fcf_margin:.1f}%)")
        max_pts += 30

    score = (points / max_pts * 100) if max_pts > 0 else 50
    return {"score": round(score), "drivers": drivers, "penalties": penalties}


def score_balance_sheet(data: dict, sector: str = "Default") -> dict:
    """
    Balance Sheet Score (0-100): Leverage, coverage, liquidity
    """
    bench = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])
    points = 0
    max_pts = 0
    drivers = []
    penalties = []

    # Net Debt / EBITDA
    net_debt = _safe(data.get("net_debt"))
    ebitda = _safe(data.get("ebitda"))
    max_lev = bench.get("net_debt_ebitda_max", 3.5)

    if net_debt is not None and ebitda and ebitda > 0:
        lev = net_debt / ebitda
        if lev <= 0:
            points += 40; drivers.append(f"Net cash position (leverage {lev:.1f}x)")
        elif lev <= max_lev * 0.5:
            points += 35; drivers.append(f"Low leverage ({lev:.1f}x ND/EBITDA)")
        elif lev <= max_lev:
            points += 20; drivers.append(f"Moderate leverage ({lev:.1f}x)")
        elif lev <= max_lev * 1.5:
            points += 8; penalties.append(f"High leverage ({lev:.1f}x vs {max_lev}x max)")
        else:
            penalties.append(f"Very high leverage ({lev:.1f}x — above threshold)")
        max_pts += 40

    # Current Ratio
    cr = _safe(data.get("current_ratio"))
    if cr is not None:
        if cr >= 2.0:
            points += 30; drivers.append(f"Strong liquidity (Current ratio {cr:.1f}x)")
        elif cr >= 1.2:
            points += 20
        elif cr >= 1.0:
            points += 8
        else:
            penalties.append(f"Tight liquidity (Current ratio {cr:.1f}x)")
        max_pts += 30

    # Payout ratio (for dividend payers)
    payout = _safe(data.get("payout_ratio"))
    if payout is not None and payout > 0:
        pr = payout * 100 if payout < 1 else payout
        if pr <= 40:
            points += 15; drivers.append(f"Conservative payout ratio ({pr:.0f}%)")
        elif pr <= 65:
            points += 10
        elif pr <= 80:
            points += 5
        else:
            penalties.append(f"High payout ratio ({pr:.0f}%) — dividend sustainability risk")
        max_pts += 15

    # Debt to equity
    de = _safe(data.get("debt_to_equity"))
    if de is not None:
        de_val = de / 100 if de > 10 else de  # yfinance sometimes returns as %, sometimes as ratio
        if de_val <= 0.3:
            points += 15; drivers.append(f"Conservative D/E ({de:.1f}%)")
        elif de_val <= 1.0:
            points += 10
        elif de_val <= 2.0:
            points += 5
        else:
            penalties.append(f"High D/E ({de:.1f}%)")
        max_pts += 15

    score = (points / max_pts * 100) if max_pts > 0 else 50
    return {"score": round(score), "drivers": drivers, "penalties": penalties}


def score_momentum(returns: dict) -> dict:
    """
    Momentum Score (0-100): Based on price returns across periods
    """
    points = 0
    max_pts = 0
    drivers = []
    penalties = []

    momentum_weights = [
        ("1m", 20, "1-month"),
        ("3m", 30, "3-month"),
        ("6m", 25, "6-month"),
        ("1y", 25, "1-year"),
    ]

    for key, weight, label in momentum_weights:
        ret = returns.get(key)
        if ret is not None:
            pct = ret * 100
            if pct >= 15:
                pts = weight; drivers.append(f"Strong {label} momentum (+{pct:.1f}%)")
            elif pct >= 5:
                pts = weight * 0.7
            elif pct >= -5:
                pts = weight * 0.4
            elif pct >= -15:
                pts = weight * 0.1; penalties.append(f"Weak {label} momentum ({pct:.1f}%)")
            else:
                pts = 0; penalties.append(f"Very weak {label} momentum ({pct:.1f}%)")
            points += pts
            max_pts += weight

    score = (points / max_pts * 100) if max_pts > 0 else 50
    return {"score": round(score), "drivers": drivers, "penalties": penalties}


def score_macro_fit(sector: str, macro_regime: str) -> dict:
    """
    Macro/Sector Fit Score (0-100): How well sector fits current macro regime
    """
    # Simplified regime fit matrix
    FIT = {
        ("Technology", "Favorable"):     80,
        ("Technology", "Neutral"):       60,
        ("Technology", "Unfavorable"):   35,
        ("Technology", "Stress"):        20,
        ("Financials", "Favorable"):     70,
        ("Financials", "Neutral"):       55,
        ("Financials", "Unfavorable"):   40,
        ("Financials", "Stress"):        25,
        ("Consumer_Staples", "Favorable"):  60,
        ("Consumer_Staples", "Neutral"):    65,
        ("Consumer_Staples", "Unfavorable"):75,
        ("Consumer_Staples", "Stress"):     80,
        ("Consumer_Discretionary", "Favorable"): 80,
        ("Consumer_Discretionary", "Neutral"):   55,
        ("Consumer_Discretionary", "Unfavorable"):25,
        ("Consumer_Discretionary", "Stress"):    15,
        ("Industrials", "Favorable"):   70,
        ("Industrials", "Neutral"):     55,
        ("Industrials", "Unfavorable"): 40,
        ("Industrials", "Stress"):      25,
        ("Real_Estate", "Favorable"):   65,
        ("Real_Estate", "Neutral"):     45,
        ("Real_Estate", "Unfavorable"): 25,
        ("Real_Estate", "Stress"):      15,
        ("Utilities", "Favorable"):     40,
        ("Utilities", "Neutral"):       55,
        ("Utilities", "Unfavorable"):   70,
        ("Utilities", "Stress"):        75,
        ("Materials", "Favorable"):     65,
        ("Materials", "Neutral"):       55,
        ("Materials", "Unfavorable"):   40,
        ("Materials", "Stress"):        30,
        ("Communication_Services", "Favorable"): 60,
        ("Communication_Services", "Neutral"):   60,
        ("Communication_Services", "Unfavorable"):50,
        ("Communication_Services", "Stress"):    45,
        ("Healthcare", "Favorable"):    55,
        ("Healthcare", "Neutral"):      65,
        ("Healthcare", "Unfavorable"):  70,
        ("Healthcare", "Stress"):       75,
    }

    score = FIT.get((sector, macro_regime), 50)
    drivers = [f"{sector} sector is {_fit_label(score)} in {macro_regime} macro regime"]
    return {"score": score, "drivers": drivers, "penalties": []}


def _fit_label(score: int) -> str:
    if score >= 70: return "well-positioned"
    if score >= 50: return "fairly positioned"
    if score >= 35: return "challenged"
    return "poorly positioned"


def compute_composite_score(
    fundamentals: dict,
    returns: dict,
    sector: str,
    macro_regime: str,
    is_etf: bool = False
) -> dict:
    """
    Compute the composite investment score (0-100) with full breakdown.
    """
    if is_etf:
        return {
            "total": None,
            "recommendation": "BENCHMARK",
            "note": "ETFs are used as sector benchmarks and are not scored as individual securities.",
            "sub_scores": {}
        }

    quality     = score_quality(fundamentals, sector)
    valuation   = score_valuation(fundamentals, sector)
    growth      = score_growth(fundamentals)
    balance     = score_balance_sheet(fundamentals, sector)
    momentum    = score_momentum(returns)
    macro_fit   = score_macro_fit(sector, macro_regime)

    sub_scores = {
        "quality":      quality,
        "valuation":    valuation,
        "growth":       growth,
        "balance_sheet":balance,
        "momentum":     momentum,
        "macro_fit":    macro_fit,
    }

    # Weighted total
    total = (
        quality["score"]     * WEIGHTS["quality"]      +
        valuation["score"]   * WEIGHTS["valuation"]    +
        growth["score"]      * WEIGHTS["growth"]       +
        balance["score"]     * WEIGHTS["balance_sheet"]+
        momentum["score"]    * WEIGHTS["momentum"]     +
        macro_fit["score"]   * WEIGHTS["macro_fit"]
    )

    # Recommendation thresholds
    if total >= 70:
        recommendation = "BUY"
        rec_color = "#06d6a0"
    elif total >= 55:
        recommendation = "HOLD"
        rec_color = "#ffd60a"
    elif total >= 40:
        recommendation = "WATCHLIST"
        rec_color = "#f77f00"
    else:
        recommendation = "SELL"
        rec_color = "#ef233c"

    # Generate narrative
    all_drivers  = []
    all_penalties = []
    for name, s in sub_scores.items():
        all_drivers.extend(s.get("drivers", []))
        all_penalties.extend(s.get("penalties", []))

    return {
        "total":          round(total, 1),
        "recommendation": recommendation,
        "rec_color":      rec_color,
        "sub_scores":     sub_scores,
        "top_drivers":    all_drivers[:3],
        "top_risks":      all_penalties[:3],
        "weights":        WEIGHTS,
    }


def get_score_color(score: float) -> str:
    if score is None: return "#8d99ae"
    if score >= 70: return "#06d6a0"
    if score >= 55: return "#ffd60a"
    if score >= 40: return "#f77f00"
    return "#ef233c"


def get_score_badge_class(score: float) -> str:
    if score is None: return "score-medium"
    if score >= 60: return "score-high"
    if score >= 40: return "score-medium"
    return "score-low"
