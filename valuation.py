"""
Valuation Analytics
- DCF (simplified)
- Reverse DCF
- Sensitivity Tables
- Multiples analysis
- WACC estimation
"""

import numpy as np
import pandas as pd
from typing import Optional


def estimate_wacc(
    beta: float = 1.0,
    risk_free_rate: float = 0.045,  # ~10Y CA gov bond
    equity_risk_premium: float = 0.055,
    target_debt_weight: float = 0.30,
    cost_of_debt: float = 0.055,
    tax_rate: float = 0.265,  # Canadian corporate tax
) -> dict:
    """
    Estimate WACC using CAPM.
    Returns WACC and components.
    """
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    equity_weight = 1 - target_debt_weight
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
    wacc = equity_weight * cost_of_equity + target_debt_weight * after_tax_cost_of_debt

    return {
        "wacc":               round(wacc, 4),
        "cost_of_equity":     round(cost_of_equity, 4),
        "after_tax_cod":      round(after_tax_cost_of_debt, 4),
        "equity_weight":      round(equity_weight, 4),
        "debt_weight":        round(target_debt_weight, 4),
        "risk_free_rate":     risk_free_rate,
        "erp":                equity_risk_premium,
        "beta":               beta,
        "tax_rate":           tax_rate,
    }


def dcf_valuation(
    revenue_base: float,
    revenue_growth_rates: list,  # List of growth rates for projection years
    ebitda_margin_target: float,
    capex_pct_revenue: float,
    tax_rate: float,
    nwc_change_pct: float,
    wacc: float,
    terminal_growth_rate: float,
    net_debt: float,
    shares_outstanding: float,
    da_pct_revenue: float = 0.05,  # D&A as % of revenue
) -> dict:
    """
    Simplified 5-10 year DCF model.
    Returns implied share price and key outputs.
    """
    years = len(revenue_growth_rates)
    revenues = []
    fcfs = []
    pv_fcfs = []

    rev = revenue_base
    for i, g in enumerate(revenue_growth_rates):
        rev = rev * (1 + g)
        revenues.append(rev)

        ebitda = rev * ebitda_margin_target
        da = rev * da_pct_revenue
        ebit = ebitda - da
        nopat = ebit * (1 - tax_rate)
        capex = rev * capex_pct_revenue
        nwc_change = rev * nwc_change_pct
        fcf = nopat + da - capex - nwc_change
        fcfs.append(fcf)

        discount_factor = 1 / (1 + wacc) ** (i + 1)
        pv_fcfs.append(fcf * discount_factor)

    # Terminal value (Gordon Growth)
    terminal_fcf = fcfs[-1] * (1 + terminal_growth_rate)
    terminal_value = terminal_fcf / (wacc - terminal_growth_rate)
    pv_terminal = terminal_value / (1 + wacc) ** years

    # Enterprise value and equity value
    pv_fcf_total = sum(pv_fcfs)
    enterprise_value = pv_fcf_total + pv_terminal
    equity_value = enterprise_value - net_debt
    price_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else None

    tv_pct = pv_terminal / enterprise_value * 100 if enterprise_value > 0 else None

    return {
        "years":             years,
        "revenues":          revenues,
        "fcfs":              fcfs,
        "pv_fcfs":           pv_fcfs,
        "pv_fcf_total":      pv_fcf_total,
        "terminal_value":    terminal_value,
        "pv_terminal":       pv_terminal,
        "enterprise_value":  enterprise_value,
        "equity_value":      equity_value,
        "price_per_share":   price_per_share,
        "tv_pct_of_ev":      tv_pct,
        "wacc":              wacc,
        "terminal_growth":   terminal_growth_rate,
    }


def reverse_dcf(
    current_price: float,
    net_debt: float,
    shares_outstanding: float,
    revenue_base: float,
    ebitda_margin_target: float,
    capex_pct_revenue: float,
    tax_rate: float,
    nwc_change_pct: float,
    wacc: float,
    terminal_growth_rate: float = 0.025,
    da_pct_revenue: float = 0.05,
    years: int = 10,
) -> dict:
    """
    Reverse DCF: Find the revenue growth rate implied by the current stock price.
    Uses binary search over growth rate.
    """
    # Current equity value = market cap
    market_cap = current_price * shares_outstanding
    target_ev = market_cap + net_debt

    # Binary search for growth rate
    def compute_ev(g_rate):
        rates = [g_rate] * years
        result = dcf_valuation(
            revenue_base, rates, ebitda_margin_target, capex_pct_revenue,
            tax_rate, nwc_change_pct, wacc, terminal_growth_rate, net_debt,
            shares_outstanding, da_pct_revenue
        )
        return result["enterprise_value"]

    low, high = -0.20, 0.60
    for _ in range(60):  # 60 iterations = high precision
        mid = (low + high) / 2
        ev = compute_ev(mid)
        if ev < target_ev:
            low = mid
        else:
            high = mid
        if abs(high - low) < 0.0001:
            break

    implied_growth = (low + high) / 2

    # Contextual assessment
    if implied_growth >= 0.25:
        assessment = "Very High — market is pricing in exceptional growth that may be hard to achieve"
        risk_level = "HIGH"
    elif implied_growth >= 0.15:
        assessment = "High — requires sustained strong growth to justify valuation"
        risk_level = "MODERATE-HIGH"
    elif implied_growth >= 0.08:
        assessment = "Moderate — achievable for a well-positioned company"
        risk_level = "MODERATE"
    elif implied_growth >= 0.03:
        assessment = "Low — conservatively priced; limited growth required"
        risk_level = "LOW"
    else:
        assessment = "Very Low / Negative — market may be pricing in decline"
        risk_level = "LOW (Cheap or Value Trap)"

    return {
        "implied_annual_growth":    round(implied_growth, 4),
        "implied_annual_growth_pct":round(implied_growth * 100, 2),
        "assessment":               assessment,
        "risk_level":               risk_level,
        "market_cap":               market_cap,
        "target_ev":                target_ev,
        "wacc":                     wacc,
        "terminal_growth":          terminal_growth_rate,
        "years":                    years,
    }


def sensitivity_table(
    revenue_base: float,
    wacc_range: list,
    growth_range: list,
    ebitda_margin_target: float,
    capex_pct_revenue: float,
    tax_rate: float,
    nwc_change_pct: float,
    net_debt: float,
    shares_outstanding: float,
    terminal_growth_rate: float = 0.025,
    years: int = 7,
    da_pct_revenue: float = 0.05,
) -> pd.DataFrame:
    """
    Generate a WACC vs Revenue Growth sensitivity table of implied share prices.
    Rows = WACC, Columns = Revenue Growth
    """
    rows = []
    for wacc in wacc_range:
        row = {"WACC": f"{wacc*100:.1f}%"}
        for g in growth_range:
            result = dcf_valuation(
                revenue_base,
                [g] * years,
                ebitda_margin_target,
                capex_pct_revenue,
                tax_rate,
                nwc_change_pct,
                wacc,
                terminal_growth_rate,
                net_debt,
                shares_outstanding,
                da_pct_revenue,
            )
            row[f"{g*100:.0f}% Rev Growth"] = round(result["price_per_share"] or 0, 2)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("WACC")
    return df


def bull_base_bear_dcf(
    revenue_base: float,
    ebitda_margin_base: float,
    wacc: float,
    net_debt: float,
    shares_outstanding: float,
) -> dict:
    """
    Three-scenario DCF (Bull / Base / Bear).
    Returns implied share price per scenario.
    """
    scenarios = {
        "Bull": {
            "growth_rates":        [0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09],
            "ebitda_margin":       ebitda_margin_base * 1.15,
            "terminal_growth":     0.03,
            "capex_pct":           0.04,
            "label":               "Bull Case",
            "description":         "Strong execution, market share gains, margin expansion",
            "color":               "#06d6a0",
        },
        "Base": {
            "growth_rates":        [0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.05],
            "ebitda_margin":       ebitda_margin_base,
            "terminal_growth":     0.025,
            "capex_pct":           0.05,
            "label":               "Base Case",
            "description":         "Consensus growth, stable margins, no major surprises",
            "color":               "#ffd60a",
        },
        "Bear": {
            "growth_rates":        [0.03, 0.03, 0.02, 0.02, 0.01, 0.01, 0.01],
            "ebitda_margin":       ebitda_margin_base * 0.85,
            "terminal_growth":     0.015,
            "capex_pct":           0.06,
            "label":               "Bear Case",
            "description":         "Margin pressure, slower growth, macro headwinds",
            "color":               "#ef233c",
        },
    }

    results = {}
    for key, s in scenarios.items():
        r = dcf_valuation(
            revenue_base,
            s["growth_rates"],
            s["ebitda_margin"],
            s["capex_pct"],
            0.265,
            0.01,
            wacc,
            s["terminal_growth"],
            net_debt,
            shares_outstanding,
        )
        results[key] = {
            **s,
            "price_per_share": r["price_per_share"],
            "enterprise_value": r["enterprise_value"],
            "tv_pct": r["tv_pct_of_ev"],
        }

    return results


def compute_valuation_percentile(current_multiple: float, historical_multiples: list) -> Optional[float]:
    """
    Where does the current multiple sit in its historical distribution?
    Returns percentile (0-100). Higher = more expensive.
    """
    if not historical_multiples or current_multiple is None:
        return None
    arr = np.array([m for m in historical_multiples if m is not None and not np.isnan(m)])
    if len(arr) == 0:
        return None
    return float(np.percentile(arr <= current_multiple, 100))


# ─────────────────────────────────────────────────────────────────────────────
# ValuationEngine — compatibility class wrapper for valuation_center.py


# ─────────────────────────────────────────────────────────────────────────────
# ValuationEngine — standalone FCF-based DCF for valuation_center.py
# Uses a simpler FCF-growth model independent of the revenue-based functions.
# ─────────────────────────────────────────────────────────────────────────────
class ValuationEngine:
    """
    FCF-based DCF engine used by the Valuation Center page.
    Accepts trailing FCF, growth rates, and WACC directly.
    """

    @staticmethod
    def _safe(v, default=0.0):
        if v is None: return default
        try:
            f = float(v)
            return default if (f != f or abs(f) == float('inf')) else f
        except (TypeError, ValueError):
            return default

    def dcf_model(self, base_fcf: float, growth_phase1: float, growth_phase2: float,
                  fcf_margin: float, terminal_growth: float, wacc: float,
                  projection_years: int, net_debt: float,
                  shares_outstanding: float) -> dict:
        """
        Simple FCF-compounding DCF.
        Splits projection period ~60/40 between phase1 and phase2 growth rates.
        """
        base_fcf = self._safe(base_fcf, 1e6)
        if base_fcf <= 0:
            base_fcf = 1e6  # fallback so model runs
        growth_phase1    = self._safe(growth_phase1, 0.08)
        growth_phase2    = self._safe(growth_phase2, 0.04)
        terminal_growth  = self._safe(terminal_growth, 0.025)
        wacc             = max(self._safe(wacc, 0.09), 0.04)
        projection_years = max(int(projection_years), 3)
        net_debt         = self._safe(net_debt, 0)
        shares           = max(self._safe(shares_outstanding, 1e6), 1)

        phase1_years = max(1, round(projection_years * 0.6))
        phase2_years = projection_years - phase1_years

        pv_fcfs = []
        projections = []
        fcf = base_fcf
        for yr in range(1, projection_years + 1):
            g = growth_phase1 if yr <= phase1_years else growth_phase2
            fcf = fcf * (1 + g)
            disc = fcf / (1 + wacc) ** yr
            pv_fcfs.append(disc)
            projections.append({
                "year": yr,
                "growth_rate": g,
                "fcf_m": round(fcf / 1e6, 2),
                "pv_fcf_m": round(disc / 1e6, 2),
            })

        # Terminal value (Gordon Growth)
        terminal_fcf = fcf * (1 + terminal_growth)
        tv = terminal_fcf / max(wacc - terminal_growth, 0.001)
        pv_tv = tv / (1 + wacc) ** projection_years

        enterprise_value = sum(pv_fcfs) + pv_tv
        equity_value = enterprise_value - net_debt
        intrinsic_per_share = equity_value / shares

        return {
            "intrinsic_value_per_share": max(intrinsic_per_share, 0),
            "equity_value": equity_value,
            "enterprise_value": enterprise_value,
            "pv_fcfs": pv_fcfs,
            "pv_terminal_value": pv_tv,
            "terminal_value": tv,
            "projections": projections,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
        }

    def reverse_dcf(self, current_price: float, base_fcf: float, fcf_margin: float,
                    wacc: float, terminal_growth: float, projection_years: int,
                    net_debt: float, shares_outstanding: float) -> dict:
        """Binary-search for the FCF growth rate that justifies the current price."""
        current_price = self._safe(current_price, 1)
        if current_price <= 0:
            return {"implied_growth_rate": 0.0, "confidence": "Low"}

        lo, hi = -0.10, 0.60
        for _ in range(60):
            mid = (lo + hi) / 2
            result = self.dcf_model(
                base_fcf=base_fcf, growth_phase1=mid,
                growth_phase2=max(mid * 0.6, 0.01),
                fcf_margin=fcf_margin, terminal_growth=terminal_growth,
                wacc=wacc, projection_years=projection_years,
                net_debt=net_debt, shares_outstanding=shares_outstanding
            )
            iv = result.get("intrinsic_value_per_share", 0)
            if abs(iv - current_price) < 0.01:
                break
            if iv < current_price:
                lo = mid
            else:
                hi = mid

        implied = (lo + hi) / 2
        confidence = "High" if abs(implied - 0.35) < 0.25 else "Low"
        return {"implied_growth_rate": implied, "confidence": confidence}
