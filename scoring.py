"""
scoring.py — Composite investment score (0-100) with 6 components.
Robust to missing data; ETFs return BENCHMARK regardless.
"""

from formatting import is_valid, safe_float


SECTOR_BENCHMARKS = {
    "Technology": {"ev_ebitda_fair": 22, "pe_fair": 28, "ebitda_margin_target": 0.25,
                   "gross_margin_target": 0.55, "roic_target": 0.15, "nd_ebitda_max": 2.5},
    "Financials": {"ev_ebitda_fair": 12, "pe_fair": 13, "ebitda_margin_target": 0.30,
                   "gross_margin_target": 0.40, "roic_target": 0.12, "nd_ebitda_max": 5.0},
    "Consumer Staples": {"ev_ebitda_fair": 14, "pe_fair": 22, "ebitda_margin_target": 0.15,
                          "gross_margin_target": 0.30, "roic_target": 0.12, "nd_ebitda_max": 3.0},
    "Consumer Discretionary": {"ev_ebitda_fair": 12, "pe_fair": 18, "ebitda_margin_target": 0.15,
                                 "gross_margin_target": 0.35, "roic_target": 0.12, "nd_ebitda_max": 3.5},
    "Industrials": {"ev_ebitda_fair": 13, "pe_fair": 18, "ebitda_margin_target": 0.18,
                    "gross_margin_target": 0.30, "roic_target": 0.10, "nd_ebitda_max": 3.0},
    "Real Estate": {"ev_ebitda_fair": 18, "pe_fair": 25, "ebitda_margin_target": 0.40,
                    "gross_margin_target": 0.50, "roic_target": 0.06, "nd_ebitda_max": 8.0},
    "Utilities": {"ev_ebitda_fair": 12, "pe_fair": 17, "ebitda_margin_target": 0.35,
                  "gross_margin_target": 0.40, "roic_target": 0.07, "nd_ebitda_max": 5.5},
    "Materials": {"ev_ebitda_fair": 10, "pe_fair": 15, "ebitda_margin_target": 0.20,
                  "gross_margin_target": 0.30, "roic_target": 0.10, "nd_ebitda_max": 2.5},
    "Communication Services": {"ev_ebitda_fair": 8, "pe_fair": 16, "ebitda_margin_target": 0.32,
                                 "gross_margin_target": 0.50, "roic_target": 0.08, "nd_ebitda_max": 4.0},
    "Healthcare": {"ev_ebitda_fair": 14, "pe_fair": 20, "ebitda_margin_target": 0.18,
                   "gross_margin_target": 0.45, "roic_target": 0.10, "nd_ebitda_max": 3.0},
    "Default": {"ev_ebitda_fair": 14, "pe_fair": 18, "ebitda_margin_target": 0.20,
                "gross_margin_target": 0.35, "roic_target": 0.10, "nd_ebitda_max": 3.5},
}


def _bench(sector: str) -> dict:
    return SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])


def _clip(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def score_quality(fund: dict, sector: str = "Default") -> dict:
    bench = _bench(sector)
    score = 50.0
    drivers = []
    risks = []

    roic = safe_float(fund.get("roic"), 0) or safe_float(fund.get("roe"), 0)
    if is_valid(roic) and roic != 0:
        target = bench.get("roic_target", 0.10)
        ratio = roic / target if target > 0 else 0
        if ratio >= 1.5:
            score += 20; drivers.append(f"Strong ROIC/ROE ({roic*100:.1f}%)")
        elif ratio >= 1.0:
            score += 12; drivers.append(f"Good ROIC/ROE ({roic*100:.1f}%)")
        elif ratio >= 0.6:
            score -= 5
        else:
            score -= 12; risks.append(f"Weak ROIC/ROE ({roic*100:.1f}%)")

    ebm = safe_float(fund.get("ebitda_margin"), None)
    if is_valid(ebm):
        target = bench.get("ebitda_margin_target", 0.20)
        if ebm >= target * 1.3:
            score += 12; drivers.append(f"Excellent EBITDA margin ({ebm*100:.1f}%)")
        elif ebm >= target:
            score += 6
        elif ebm >= target * 0.6:
            score -= 4
        else:
            score -= 10; risks.append(f"Sub-par EBITDA margin ({ebm*100:.1f}%)")

    fcf = safe_float(fund.get("fcf"), 0)
    ni = safe_float(fund.get("net_income_ttm"), 0)
    if fcf and ni and ni > 0:
        conv = fcf / ni
        if conv >= 1.0:
            score += 8; drivers.append(f"Strong FCF conversion ({conv:.2f}x)")
        elif conv >= 0.7:
            score += 3
        elif conv < 0.3:
            score -= 8; risks.append(f"Low FCF conversion ({conv:.2f}x)")

    return {"score": int(_clip(score)), "drivers": drivers, "risks": risks}


def score_valuation(fund: dict, sector: str = "Default") -> dict:
    bench = _bench(sector)
    score = 50.0
    drivers = []
    risks = []

    ev_ebitda = safe_float(fund.get("ev_ebitda"), None)
    if is_valid(ev_ebitda) and ev_ebitda > 0:
        fair = bench.get("ev_ebitda_fair", 14)
        ratio = ev_ebitda / fair
        if ratio < 0.7:
            score += 18; drivers.append(f"Cheap EV/EBITDA ({ev_ebitda:.1f}x vs {fair}x fair)")
        elif ratio < 0.9:
            score += 10; drivers.append(f"Below-fair EV/EBITDA ({ev_ebitda:.1f}x)")
        elif ratio < 1.2:
            score += 0
        elif ratio < 1.5:
            score -= 8
        else:
            score -= 15; risks.append(f"Expensive EV/EBITDA ({ev_ebitda:.1f}x vs {fair}x fair)")

    pe = safe_float(fund.get("pe_trailing"), None) or safe_float(fund.get("pe_forward"), None)
    if is_valid(pe) and pe > 0:
        fair = bench.get("pe_fair", 18)
        ratio = pe / fair
        if ratio < 0.7:
            score += 10
        elif ratio < 1.0:
            score += 5
        elif ratio > 1.5:
            score -= 8

    fcf = safe_float(fund.get("fcf"), None)
    mc = safe_float(fund.get("market_cap"), None)
    if fcf and mc and mc > 0:
        fcf_y = fcf / mc
        if fcf_y > 0.06:
            score += 10; drivers.append(f"High FCF yield ({fcf_y*100:.1f}%)")
        elif fcf_y > 0.03:
            score += 4
        elif fcf_y < 0:
            score -= 8; risks.append("Negative free cash flow")

    return {"score": int(_clip(score)), "drivers": drivers, "risks": risks}


def score_growth(fund: dict) -> dict:
    score = 50.0
    drivers = []
    risks = []

    rev_g = safe_float(fund.get("revenue_growth_yoy"), None)
    if is_valid(rev_g):
        if rev_g >= 0.20:
            score += 25; drivers.append(f"Strong revenue growth ({rev_g*100:.1f}% YoY)")
        elif rev_g >= 0.10:
            score += 15
        elif rev_g >= 0.05:
            score += 5
        elif rev_g < 0:
            score -= 15; risks.append(f"Revenue declining ({rev_g*100:.1f}% YoY)")

    eps_g = safe_float(fund.get("earnings_growth"), None)
    if is_valid(eps_g):
        if eps_g >= 0.15:
            score += 15; drivers.append(f"Strong EPS growth ({eps_g*100:.1f}% YoY)")
        elif eps_g >= 0.05:
            score += 5
        elif eps_g < -0.10:
            score -= 10; risks.append(f"EPS declining ({eps_g*100:.1f}% YoY)")

    return {"score": int(_clip(score)), "drivers": drivers, "risks": risks}


def score_balance_sheet(fund: dict, sector: str = "Default") -> dict:
    bench = _bench(sector)
    score = 60.0
    drivers = []
    risks = []

    nd = safe_float(fund.get("net_debt"), 0)
    ebitda = safe_float(fund.get("ebitda"), 0)
    if ebitda > 0:
        ratio = nd / ebitda
        max_lev = bench.get("nd_ebitda_max", 3.5)
        if ratio < 0:
            score += 15; drivers.append("Net cash position")
        elif ratio < max_lev * 0.5:
            score += 10; drivers.append(f"Conservative leverage ({ratio:.1f}x ND/EBITDA)")
        elif ratio < max_lev:
            score += 0
        elif ratio < max_lev * 1.3:
            score -= 10
        else:
            score -= 20; risks.append(f"High leverage ({ratio:.1f}x ND/EBITDA)")

    cr = safe_float(fund.get("current_ratio"), None)
    if is_valid(cr):
        if cr >= 1.5:
            score += 10; drivers.append(f"Strong liquidity (CR {cr:.1f})")
        elif cr >= 1.0:
            score += 5
        elif cr < 0.8:
            score -= 8; risks.append(f"Liquidity concern (CR {cr:.1f})")

    return {"score": int(_clip(score)), "drivers": drivers, "risks": risks}


def score_momentum(returns: dict) -> dict:
    if not returns:
        return {"score": 50, "drivers": [], "risks": []}

    score = 50.0
    drivers = []
    risks = []

    weights = {"1m": 0.15, "3m": 0.25, "6m": 0.25, "1y": 0.35}
    weighted = 0
    total_w = 0

    for period, w in weights.items():
        r = returns.get(period)
        if is_valid(r):
            weighted += r * w * 100
            total_w += w

    if total_w > 0:
        avg_ret = weighted / total_w
        if avg_ret >= 30:
            score = 90; drivers.append(f"Strong momentum (+{avg_ret:.1f}%)")
        elif avg_ret >= 15:
            score = 75; drivers.append(f"Positive momentum (+{avg_ret:.1f}%)")
        elif avg_ret >= 5:
            score = 60
        elif avg_ret >= -5:
            score = 50
        elif avg_ret >= -15:
            score = 35; risks.append(f"Weak momentum ({avg_ret:.1f}%)")
        else:
            score = 20; risks.append(f"Strong negative momentum ({avg_ret:.1f}%)")

    return {"score": int(_clip(score)), "drivers": drivers, "risks": risks}


def score_macro_fit(sector: str, regime: str = "Neutral") -> dict:
    base = {"Favorable": 75, "Neutral": 60, "Unfavorable": 45, "Stress": 30}.get(regime, 50)
    cyclical = {"Consumer Discretionary", "Industrials", "Materials", "Financials"}
    defensive = {"Consumer Staples", "Utilities", "Healthcare"}
    if regime in ("Unfavorable", "Stress") and sector in defensive:
        base += 10
    elif regime == "Favorable" and sector in cyclical:
        base += 5
    elif regime == "Stress" and sector in cyclical:
        base -= 10
    return {"score": int(_clip(base)), "drivers": [], "risks": []}


WEIGHTS = {"quality": 0.25, "valuation": 0.25, "growth": 0.20,
           "balance_sheet": 0.15, "momentum": 0.10, "macro_fit": 0.05}


def compute_composite_score(fund: dict, returns: dict, sector: str = "Default",
                            regime: str = "Neutral", is_etf: bool = False) -> dict:
    """Composite 0-100 score and recommendation. ETFs return BENCHMARK."""
    if is_etf:
        return {"total": None, "recommendation": "BENCHMARK",
                "sub_scores": {}, "top_drivers": [], "top_risks": []}

    sub = {
        "quality":       score_quality(fund, sector),
        "valuation":     score_valuation(fund, sector),
        "growth":        score_growth(fund),
        "balance_sheet": score_balance_sheet(fund, sector),
        "momentum":      score_momentum(returns or {}),
        "macro_fit":     score_macro_fit(sector, regime),
    }

    total = sum(sub[k]["score"] * WEIGHTS[k] for k in WEIGHTS)
    total = int(_clip(total))

    if total >= 70:
        rec = "BUY"
    elif total >= 55:
        rec = "HOLD"
    elif total >= 40:
        rec = "WATCHLIST"
    else:
        rec = "SELL"

    all_drivers = []
    all_risks = []
    for s in sub.values():
        all_drivers.extend(s.get("drivers", []))
        all_risks.extend(s.get("risks", []))

    return {
        "total": total,
        "recommendation": rec,
        "sub_scores": sub,
        "top_drivers": all_drivers[:3],
        "top_risks": all_risks[:3],
    }
