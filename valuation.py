"""
valuation.py — DCF, Reverse DCF, sensitivity, scenarios.
FCF-based simplified DCF — robust to missing inputs. NEVER raises.
"""
import numpy as np
import pandas as pd
from formatting import safe_float, is_valid


def estimate_wacc(beta: float = 1.0,
                  risk_free_rate: float = 0.045,
                  equity_risk_premium: float = 0.055,
                  debt_weight: float = 0.30,
                  cost_of_debt: float = 0.055,
                  tax_rate: float = 0.265) -> dict:
    """CAPM-based WACC."""
    beta = safe_float(beta, 1.0)
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    after_tax_cod  = cost_of_debt * (1 - tax_rate)
    wacc = (1 - debt_weight) * cost_of_equity + debt_weight * after_tax_cod
    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "after_tax_cod": after_tax_cod,
        "beta": beta,
    }


def dcf_fcf(base_fcf: float,
            growth_phase1: float = 0.10,
            growth_phase2: float = 0.05,
            terminal_growth: float = 0.025,
            wacc: float = 0.09,
            projection_years: int = 10,
            net_debt: float = 0.0,
            shares_outstanding: float = 1.0) -> dict:
    """
    Simple FCF-compounding DCF. Phase 1 covers ~60% of years at growth_phase1,
    phase 2 covers the rest at growth_phase2.
    Returns dict with intrinsic_value_per_share, EV, projections, etc.
    """
    base_fcf = safe_float(base_fcf, 0)
    if base_fcf <= 0:
        return {
            "intrinsic_value_per_share": 0.0,
            "enterprise_value": 0.0,
            "equity_value": 0.0,
            "pv_fcfs": 0.0,
            "pv_terminal_value": 0.0,
            "terminal_value": 0.0,
            "projections": [],
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "error": "Negative or zero base FCF",
        }

    g1     = safe_float(growth_phase1, 0.08)
    g2     = safe_float(growth_phase2, 0.04)
    tg     = safe_float(terminal_growth, 0.025)
    wacc   = max(safe_float(wacc, 0.09), 0.04)
    proj_y = max(int(safe_float(projection_years, 10)), 3)
    nd     = safe_float(net_debt, 0)
    shares = max(safe_float(shares_outstanding, 1.0), 1.0)

    # Ensure tg < wacc (avoid divide-by-zero)
    tg = min(tg, wacc - 0.01)

    phase1_y = max(1, round(proj_y * 0.6))

    pv_fcfs = []
    projections = []
    fcf = base_fcf

    for yr in range(1, proj_y + 1):
        g = g1 if yr <= phase1_y else g2
        fcf = fcf * (1 + g)
        pv  = fcf / (1 + wacc) ** yr
        pv_fcfs.append(pv)
        projections.append({
            "year":     yr,
            "growth":   g,
            "fcf":      fcf,
            "pv_fcf":   pv,
        })

    terminal_fcf = fcf * (1 + tg)
    tv = terminal_fcf / max(wacc - tg, 0.005)
    pv_tv = tv / (1 + wacc) ** proj_y

    pv_fcfs_sum = sum(pv_fcfs)
    ev = pv_fcfs_sum + pv_tv
    equity_val = ev - nd
    iv_per_share = max(equity_val / shares, 0)

    return {
        "intrinsic_value_per_share": iv_per_share,
        "equity_value":      equity_val,
        "enterprise_value":  ev,
        "pv_fcfs":           pv_fcfs_sum,
        "pv_terminal_value": pv_tv,
        "terminal_value":    tv,
        "projections":       projections,
        "wacc":              wacc,
        "terminal_growth":   tg,
    }


def reverse_dcf_fcf(current_price: float,
                    base_fcf: float,
                    wacc: float = 0.09,
                    terminal_growth: float = 0.025,
                    projection_years: int = 10,
                    net_debt: float = 0.0,
                    shares_outstanding: float = 1.0) -> dict:
    """
    Solve (binary search) for the FCF growth rate that makes intrinsic value equal current price.
    """
    current_price = safe_float(current_price, 0)
    if current_price <= 0:
        return {
            "implied_growth_rate": 0.0,
            "implied_annual_growth_pct": 0.0,
            "assessment": "Price unavailable",
            "confidence": "Low",
        }

    lo, hi = -0.10, 0.50
    last_iv = None
    for _ in range(60):
        mid = (lo + hi) / 2
        result = dcf_fcf(
            base_fcf=base_fcf,
            growth_phase1=mid,
            growth_phase2=max(mid * 0.6, 0.02),
            terminal_growth=terminal_growth,
            wacc=wacc,
            projection_years=projection_years,
            net_debt=net_debt,
            shares_outstanding=shares_outstanding,
        )
        iv = result.get("intrinsic_value_per_share", 0)
        last_iv = iv
        if abs(iv - current_price) < 0.05:
            break
        if iv < current_price:
            lo = mid
        else:
            hi = mid

    implied = (lo + hi) / 2

    if implied > 0.25:
        assessment = "Very demanding — only justified by exceptional moat"
    elif implied > 0.15:
        assessment = "Demanding — requires sustained strong growth"
    elif implied > 0.08:
        assessment = "Moderate — achievable for quality compounders"
    elif implied > 0.02:
        assessment = "Conservative — limited growth required"
    else:
        assessment = "Very conservative or pricing in decline"

    return {
        "implied_growth_rate":       implied,
        "implied_annual_growth_pct": implied * 100,
        "assessment":                assessment,
        "confidence":                "Medium" if last_iv and abs(last_iv - current_price) < 1.0 else "Low",
    }


def sensitivity_table(base_fcf: float,
                      wacc_range: list = None,
                      growth_range: list = None,
                      terminal_growth: float = 0.025,
                      projection_years: int = 10,
                      net_debt: float = 0.0,
                      shares_outstanding: float = 1.0) -> pd.DataFrame:
    """
    DCF sensitivity grid: rows = growth, cols = WACC, cells = $/share.
    """
    if wacc_range is None:
        wacc_range = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
    if growth_range is None:
        growth_range = [0.0, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]

    grid = []
    for g in growth_range:
        row = []
        for w in wacc_range:
            result = dcf_fcf(
                base_fcf=base_fcf,
                growth_phase1=g,
                growth_phase2=max(g * 0.6, 0.02),
                terminal_growth=terminal_growth,
                wacc=w,
                projection_years=projection_years,
                net_debt=net_debt,
                shares_outstanding=shares_outstanding,
            )
            row.append(result.get("intrinsic_value_per_share", 0))
        grid.append(row)

    return pd.DataFrame(
        grid,
        index=[f"{g*100:.0f}% growth" for g in growth_range],
        columns=[f"{w*100:.1f}% WACC" for w in wacc_range],
    )


def scenario_dcf(base_fcf: float,
                 wacc: float = 0.09,
                 terminal_growth: float = 0.025,
                 projection_years: int = 10,
                 net_debt: float = 0.0,
                 shares_outstanding: float = 1.0,
                 base_growth: float = 0.08) -> dict:
    """
    Bull / Base / Bear scenarios. Returns dict keyed by case name with:
    {price_per_share, growth, wacc, terminal_growth, label, description, color}
    """
    base_growth = safe_float(base_growth, 0.08)

    cases = {
        "Bear": {
            "growth":           max(base_growth - 0.06, -0.02),
            "wacc":             wacc + 0.015,
            "terminal_growth":  max(terminal_growth - 0.005, 0.01),
            "label":            "Bear Case",
            "description":      "Lower growth, higher WACC, weaker terminal",
            "color":            "#EF4444",
        },
        "Base": {
            "growth":           base_growth,
            "wacc":             wacc,
            "terminal_growth":  terminal_growth,
            "label":            "Base Case",
            "description":      "Current market expectations",
            "color":            "#FFB81C",
        },
        "Bull": {
            "growth":           base_growth + 0.05,
            "wacc":             max(wacc - 0.01, 0.06),
            "terminal_growth":  min(terminal_growth + 0.005, 0.04),
            "label":            "Bull Case",
            "description":      "Faster growth, slightly cheaper capital",
            "color":            "#22C55E",
        },
    }

    out = {}
    for name, params in cases.items():
        result = dcf_fcf(
            base_fcf=base_fcf,
            growth_phase1=params["growth"],
            growth_phase2=max(params["growth"] * 0.6, 0.02),
            terminal_growth=params["terminal_growth"],
            wacc=params["wacc"],
            projection_years=projection_years,
            net_debt=net_debt,
            shares_outstanding=shares_outstanding,
        )
        out[name] = {
            "price_per_share":      result.get("intrinsic_value_per_share", 0),
            "intrinsic_value":      result.get("intrinsic_value_per_share", 0),
            "growth":               params["growth"],
            "wacc":                 params["wacc"],
            "terminal_growth":      params["terminal_growth"],
            "label":                params["label"],
            "description":          params["description"],
            "color":                params["color"],
        }
    return out
