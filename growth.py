"""analysis/growth.py — top-line/bottom-line growth trends and a 0-100 growth score."""

import numpy as np

from data.fetcher import get_info, get_financials, safe_get_row


def analyze_growth(ticker: str) -> dict:
    info = get_info(ticker)
    fin = get_financials(ticker)

    revenue_growth = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")

    rev_cagr, earnings_stability = _multi_year_trends(fin)
    fcf_growth = _fcf_growth(fin)

    score = _growth_score(revenue_growth, earnings_growth, fcf_growth, earnings_stability)

    return {
        "revenue_growth_yoy": revenue_growth,
        "earnings_growth_yoy": earnings_growth,
        "revenue_cagr_multi_year": rev_cagr,
        "earnings_stability_score": earnings_stability,
        "fcf_growth_yoy": fcf_growth,
        "growth_score": score,
    }


def _multi_year_trends(fin):
    inc = fin.get("income_stmt")
    if inc is None or inc.empty:
        return None, None
    rev = safe_get_row(inc, "Total Revenue")
    net_income = safe_get_row(inc, "Net Income")
    rev_cagr = None
    if rev is not None and len(rev) >= 2:
        try:
            latest, oldest = float(rev.iloc[0]), float(rev.iloc[-1])
            years = len(rev) - 1
            if oldest > 0 and years > 0:
                rev_cagr = (latest / oldest) ** (1 / years) - 1
        except Exception:
            pass
    stability = None
    if net_income is not None and len(net_income) >= 2:
        try:
            vals = [float(v) for v in net_income if v == v]
            positive_years = sum(1 for v in vals if v > 0)
            stability = float(positive_years / len(vals) * 100) if vals else None
        except Exception:
            pass
    return rev_cagr, stability


def _fcf_growth(fin):
    cf = fin.get("cashflow")
    if cf is None or cf.empty:
        return None
    ocf = safe_get_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = safe_get_row(cf, "Capital Expenditure")
    if ocf is None or len(ocf) < 2:
        return None
    try:
        capex_vals = capex if capex is not None else [0] * len(ocf)
        fcf = [o + (c if c == c else 0) for o, c in zip(ocf, capex_vals)]
        if fcf[1] == 0:
            return None
        return float((fcf[0] / fcf[1]) - 1)
    except Exception:
        return None


def _growth_score(revenue_growth, earnings_growth, fcf_growth, earnings_stability) -> float:
    subs = []
    if revenue_growth is not None and revenue_growth == revenue_growth:
        subs.append(float(np.clip(50 + revenue_growth * 250, 0, 100)))
    if earnings_growth is not None and earnings_growth == earnings_growth:
        subs.append(float(np.clip(50 + earnings_growth * 150, 0, 100)))
    if fcf_growth is not None and fcf_growth == fcf_growth:
        subs.append(float(np.clip(50 + fcf_growth * 150, 0, 100)))
    if earnings_stability is not None and earnings_stability == earnings_stability:
        subs.append(earnings_stability)
    if not subs:
        return np.nan
    return float(np.mean(subs))
