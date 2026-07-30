"""
models/sector_scanner.py

Sector-adjusted scanning: ranks stocks only against sector peers (never
technology vs. utilities directly), and surfaces best-overall / most
undervalued / lowest-risk / highest-momentum picks per sector.

The DEFAULT_UNIVERSE below is a small, free-to-fetch starter set. Users can
supply their own ticker->sector mapping for a larger universe; nothing here
depends on a paid reference-data provider — sector labels come straight from
yfinance's `sector` field, with the DEFAULT_UNIVERSE as a fallback grouping.
"""

import pandas as pd
import numpy as np

from fetcher import get_info
from factor_model import run_full_analysis

DEFAULT_UNIVERSE = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "PFE", "MRK"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "V"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Industrials": ["CAT", "HON", "UNP", "RTX", "BA"],
    "Utilities": ["NEE", "DUK", "SO", "AEP"],
}


def scan_sector(sector: str, tickers: list = None) -> dict:
    tickers = tickers or DEFAULT_UNIVERSE.get(sector, [])
    if not tickers:
        return {"error": f"No tickers configured for sector '{sector}'. Supply a ticker list."}

    rows = []
    for t in tickers:
        try:
            result = run_full_analysis(t, sector_peers=tickers)
            rows.append({
                "ticker": t,
                "overall_score": result["overall_score"],
                "momentum_score": result["subscores"]["momentum"],
                "value_score": result["subscores"]["value"],
                "quality_score": result["subscores"]["quality"],
                "growth_score": result["subscores"]["growth"],
                "risk_score": result["subscores"]["risk"],
                "return_3m": result["momentum"].get("return_3m"),
                "pe_ratio": result["value"].get("pe_ratio"),
                "annualized_volatility": result["risk"].get("annualized_volatility"),
            })
        except Exception as e:
            rows.append({"ticker": t, "error": str(e)})

    df = pd.DataFrame(rows)
    valid = df[df.get("overall_score").notna()] if "overall_score" in df.columns else df

    summary = {
        "sector": sector,
        "n_names": len(df),
        "avg_return_3m": float(valid["return_3m"].mean()) if "return_3m" in valid else np.nan,
        "avg_volatility": float(valid["annualized_volatility"].mean()) if "annualized_volatility" in valid else np.nan,
        "avg_pe": float(valid["pe_ratio"].mean()) if "pe_ratio" in valid else np.nan,
        "avg_quality_score": float(valid["quality_score"].mean()) if "quality_score" in valid else np.nan,
        "avg_growth_score": float(valid["growth_score"].mean()) if "growth_score" in valid else np.nan,
        "avg_overall_score": float(valid["overall_score"].mean()) if "overall_score" in valid else np.nan,
    }

    best = {}
    if not valid.empty:
        best["best_overall"] = valid.loc[valid["overall_score"].idxmax(), "ticker"]
        best["most_undervalued"] = valid.loc[valid["value_score"].idxmax(), "ticker"] if valid["value_score"].notna().any() else None
        best["lowest_risk"] = valid.loc[valid["risk_score"].idxmax(), "ticker"] if valid["risk_score"].notna().any() else None
        best["highest_momentum"] = valid.loc[valid["momentum_score"].idxmax(), "ticker"] if valid["momentum_score"].notna().any() else None

    return {"summary": summary, "table": df, "best_in_category": best}


def scan_all_sectors(universe: dict = None) -> pd.DataFrame:
    universe = universe or DEFAULT_UNIVERSE
    rows = []
    for sector in universe:
        res = scan_sector(sector, universe[sector])
        s = res["summary"]
        s["opportunity_score"] = _opportunity_score(s)
        rows.append(s)
    df = pd.DataFrame(rows).sort_values("opportunity_score", ascending=False)
    return df


def _opportunity_score(summary: dict) -> float:
    """Ranks sectors by a blend of average quality/growth score and average valuation attractiveness,
    penalized modestly by average volatility. This is a simple, transparent heuristic — inspect the
    underlying averages rather than trusting the single number."""
    q = summary.get("avg_quality_score") or 0
    g = summary.get("avg_growth_score") or 0
    o = summary.get("avg_overall_score") or 0
    vol = summary.get("avg_volatility") or 0.3
    return float(0.4 * o + 0.3 * q + 0.3 * g - vol * 20)
