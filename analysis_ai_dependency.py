"""
analysis/ai_dependency.py

Heuristic 'AI dependency risk' overlay. There is no free, reliable data source
that reports segment-level 'AI revenue' directly, so this is built from proxies:

  1. Narrative exposure: keyword density of AI-related terms in the company's
     business description (yfinance longBusinessSummary).
  2. Valuation expansion: how far current P/E sits above the stock's own
     3-year median P/E-equivalent, approximated via price appreciation
     relative to earnings growth (a proxy for multiple expansion).
  3. Sector volatility: annualized volatility, since AI-narrative-driven names
     cluster in high-volatility sectors (semis, software, momentum tech).

This is explicitly a PROXY, not a fundamentals-verified exposure metric — it is
disclosed as such in the UI. Treat the AI Dependency Risk Score as a caution
flag, not a precise measurement.
"""

import re
import numpy as np

from fetcher import get_info, get_price_history

AI_KEYWORDS = [
    "artificial intelligence", "machine learning", "generative ai", "large language model",
    "llm", "neural network", "deep learning", "ai-powered", "ai chip", "gpu", "data center",
    "ai infrastructure", "foundation model", "genai",
]


def analyze_ai_dependency(ticker: str) -> dict:
    info = get_info(ticker)
    hist = get_price_history(ticker, period="3y")

    summary = (info.get("longBusinessSummary") or "").lower()
    keyword_hits = sum(len(re.findall(re.escape(k), summary)) for k in AI_KEYWORDS)
    narrative_exposure = float(np.clip(keyword_hits * 12, 0, 100))  # 8+ mentions -> saturated

    valuation_expansion = np.nan
    price_return_3y = np.nan
    if not hist.empty and len(hist) > 30:
        close = hist["Close"].dropna()
        price_return_3y = float((close.iloc[-1] / close.iloc[0]) - 1.0)
        earnings_growth = info.get("earningsGrowth")
        if earnings_growth is not None and earnings_growth == earnings_growth:
            # if price has run up far faster than earnings, that's multiple expansion
            gap = price_return_3y - (earnings_growth * 3)
            valuation_expansion = float(np.clip(gap * 100, 0, 100))
        else:
            valuation_expansion = float(np.clip(price_return_3y * 100, 0, 100)) if price_return_3y > 0 else 0.0

    sector_vol = np.nan
    if not hist.empty:
        daily_ret = hist["Close"].pct_change().dropna()
        if len(daily_ret) > 30:
            sector_vol = float(np.clip(daily_ret.std() * np.sqrt(252) * 150, 0, 100))

    components = [v for v in [narrative_exposure, valuation_expansion, sector_vol] if v == v]
    ai_dependency_risk = float(np.mean(components)) if components else np.nan

    # Penalty subtracted from overall factor score: scaled so a max-risk name loses ~15 pts
    penalty = (ai_dependency_risk / 100.0) * 15.0 if ai_dependency_risk == ai_dependency_risk else 0.0

    return {
        "ai_keyword_mentions": keyword_hits,
        "narrative_exposure_0to100": narrative_exposure,
        "valuation_expansion_proxy_0to100": valuation_expansion,
        "price_return_3y": price_return_3y,
        "sector_volatility_proxy_0to100": sector_vol,
        "ai_dependency_risk_0to100": ai_dependency_risk,
        "overall_score_penalty": penalty,
        "methodology_note": (
            "Proxy metric based on business-description keyword density, "
            "price-vs-earnings multiple expansion, and realized volatility. "
            "Not a verified segment-revenue disclosure."
        ),
    }
