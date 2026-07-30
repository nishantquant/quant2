"""analysis/quality.py — profitability, balance-sheet strength, and a 0-100 quality score."""

import numpy as np

from data.fetcher import get_info, get_financials, safe_get_row


def analyze_quality(ticker: str) -> dict:
    info = get_info(ticker)
    fin = get_financials(ticker)

    roe = info.get("returnOnEquity")
    gross_margin = info.get("grossMargins")
    operating_margin = info.get("operatingMargins")
    debt_to_equity = info.get("debtToEquity")
    if debt_to_equity is not None:
        debt_to_equity = debt_to_equity / 100.0 if debt_to_equity > 5 else debt_to_equity

    roic = _estimate_roic(fin, info)
    interest_coverage = _estimate_interest_coverage(fin)
    fcf_consistency = _fcf_consistency(fin)

    score = _quality_score(roic, roe, gross_margin, debt_to_equity, interest_coverage, fcf_consistency)

    return {
        "roic": roic,
        "roe": roe,
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "debt_to_equity": debt_to_equity,
        "interest_coverage": interest_coverage,
        "fcf_consistency_pct_positive_years": fcf_consistency,
        "quality_score": score,
    }


def _estimate_roic(fin, info):
    inc = fin.get("income_stmt")
    bs = fin.get("balance_sheet")
    if inc is None or inc.empty or bs is None or bs.empty:
        return None
    ebit = safe_get_row(inc, "Ebit", "Operating Income")
    tax_rate_row = safe_get_row(inc, "Tax Rate For Calcs")
    total_debt = safe_get_row(bs, "Total Debt")
    cash = safe_get_row(bs, "Cash And Cash Equivalents", "Cash")
    equity = safe_get_row(bs, "Stockholders Equity", "Total Stockholder Equity")

    if ebit is None or equity is None:
        return None
    try:
        ebit_latest = float(ebit.iloc[0])
        equity_latest = float(equity.iloc[0])
        debt_latest = float(total_debt.iloc[0]) if total_debt is not None and len(total_debt) else 0.0
        cash_latest = float(cash.iloc[0]) if cash is not None and len(cash) else 0.0
        tax_rate = float(tax_rate_row.iloc[0]) if tax_rate_row is not None and len(tax_rate_row) else 0.21
        nopat = ebit_latest * (1 - tax_rate)
        invested_capital = debt_latest + equity_latest - cash_latest
        if invested_capital <= 0:
            return None
        return float(nopat / invested_capital)
    except Exception:
        return None


def _estimate_interest_coverage(fin):
    inc = fin.get("income_stmt")
    if inc is None or inc.empty:
        return None
    ebit = safe_get_row(inc, "Ebit", "Operating Income")
    interest_exp = safe_get_row(inc, "Interest Expense")
    if ebit is None or interest_exp is None:
        return None
    try:
        e = float(ebit.iloc[0])
        i = abs(float(interest_exp.iloc[0]))
        if i == 0:
            return None
        return float(e / i)
    except Exception:
        return None


def _fcf_consistency(fin):
    cf = fin.get("cashflow")
    if cf is None or cf.empty:
        return None
    ocf = safe_get_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = safe_get_row(cf, "Capital Expenditure")
    if ocf is None:
        return None
    try:
        capex_vals = capex if capex is not None else [0] * len(ocf)
        fcf_series = [o + (c if c == c else 0) for o, c in zip(ocf, capex_vals)]
        if not fcf_series:
            return None
        positive = sum(1 for v in fcf_series if v > 0)
        return float(positive / len(fcf_series) * 100)
    except Exception:
        return None


def _quality_score(roic, roe, gross_margin, debt_to_equity, interest_coverage, fcf_consistency) -> float:
    subs = []
    if roic is not None and roic == roic:
        subs.append(float(np.clip(roic * 500, 0, 100)))  # 20% ROIC -> 100
    if roe is not None and roe == roe:
        subs.append(float(np.clip(roe * 300, 0, 100)))  # 33% ROE -> 100
    if gross_margin is not None and gross_margin == gross_margin:
        subs.append(float(np.clip(gross_margin * 150, 0, 100)))
    if debt_to_equity is not None and debt_to_equity == debt_to_equity:
        subs.append(float(np.clip(100 - debt_to_equity * 40, 0, 100)))
    if interest_coverage is not None and interest_coverage == interest_coverage:
        subs.append(float(np.clip(interest_coverage * 10, 0, 100)))
    if fcf_consistency is not None and fcf_consistency == fcf_consistency:
        subs.append(fcf_consistency)
    if not subs:
        return np.nan
    return float(np.mean(subs))
