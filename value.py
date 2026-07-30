"""analysis/value.py — valuation multiples and a 0-100 value score (higher = cheaper)."""

import numpy as np

from data.fetcher import get_info, get_financials, safe_get_row


def analyze_value(ticker: str) -> dict:
    info = get_info(ticker)
    fin = get_financials(ticker)

    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    ps = info.get("priceToSalesTrailing12Months")
    pb = info.get("priceToBook")
    ev = info.get("enterpriseValue")
    ebitda = info.get("ebitda")
    ev_ebitda = (ev / ebitda) if (ev and ebitda and ebitda != 0) else info.get("enterpriseToEbitda")

    market_cap = info.get("marketCap")
    fcf = _estimate_fcf(fin)
    fcf_yield = (fcf / market_cap) if (fcf is not None and market_cap) else None

    score = _value_score(pe, peg, ev_ebitda, fcf_yield)

    return {
        "pe_ratio": pe,
        "forward_pe": fwd_pe,
        "peg_ratio": peg,
        "price_to_sales": ps,
        "price_to_book": pb,
        "ev_ebitda": ev_ebitda,
        "fcf_yield": fcf_yield,
        "value_score": score,
    }


def _estimate_fcf(fin: dict):
    cf = fin.get("cashflow")
    if cf is None or cf.empty:
        return None
    ocf = safe_get_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = safe_get_row(cf, "Capital Expenditure")
    if ocf is None:
        return None
    ocf_latest = ocf.iloc[0] if len(ocf) else None
    capex_latest = capex.iloc[0] if capex is not None and len(capex) else 0
    if ocf_latest is None or ocf_latest != ocf_latest:
        return None
    capex_latest = capex_latest if (capex_latest == capex_latest) else 0
    return float(ocf_latest + capex_latest)  # capex is stored negative by yfinance


def _value_score(pe, peg, ev_ebitda, fcf_yield) -> float:
    """
    Each metric contributes a 0-100 sub-score (cheaper -> higher), then averaged.
    A metric with no data is simply excluded rather than penalized, since data
    availability varies a lot across tickers (financials, small caps especially).
    """
    subs = []

    if pe is not None and pe == pe and pe > 0:
        subs.append(float(np.clip(100 - (pe - 10) * 3, 0, 100)))  # PE 10 -> 100, PE 40 -> ~10

    if peg is not None and peg == peg and peg > 0:
        subs.append(float(np.clip(100 - (peg - 0.5) * 50, 0, 100)))  # PEG 0.5 -> 100, PEG 2.5 -> 0

    if ev_ebitda is not None and ev_ebitda == ev_ebitda and ev_ebitda > 0:
        subs.append(float(np.clip(100 - (ev_ebitda - 5) * 4, 0, 100)))  # EV/EBITDA 5 -> 100, 30 -> 0

    if fcf_yield is not None and fcf_yield == fcf_yield:
        subs.append(float(np.clip(fcf_yield * 1000, 0, 100)))  # 10% yield -> 100

    if not subs:
        return np.nan
    return float(np.mean(subs))
