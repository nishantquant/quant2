"""analysis/price_market.py — price/market structure metrics."""

import numpy as np
import pandas as pd

from fetcher import get_price_history, get_info, get_benchmark_history


def analyze_price_market(ticker: str) -> dict:
    hist = get_price_history(ticker, period="2y")
    info = get_info(ticker)
    bench = get_benchmark_history(period="2y")

    if hist.empty:
        return {"error": f"No price history available for {ticker}."}

    close = hist["Close"].dropna()
    current_price = float(close.iloc[-1])

    hi_52w = float(close[-252:].max()) if len(close) >= 5 else float(close.max())
    lo_52w = float(close[-252:].min()) if len(close) >= 5 else float(close.min())
    dist_from_high = (current_price / hi_52w - 1.0) * 100.0 if hi_52w else np.nan

    daily_ret = close.pct_change().dropna()
    hist_vol_annualized = float(daily_ret.std() * np.sqrt(252)) if len(daily_ret) > 5 else np.nan

    avg_volume = float(hist["Volume"].tail(30).mean()) if "Volume" in hist.columns else np.nan
    liquidity_score = _liquidity_score(avg_volume, current_price)

    beta = info.get("beta", None)
    correlation = np.nan
    if not bench.empty:
        bclose = bench["Close"].pct_change().dropna()
        merged = pd.concat([daily_ret.rename("stock"), bclose.rename("bench")], axis=1).dropna()
        if len(merged) > 10:
            correlation = float(merged["stock"].corr(merged["bench"]))
            if beta is None or beta != beta:
                cov = merged["stock"].cov(merged["bench"])
                var = merged["bench"].var()
                beta = float(cov / var) if var else np.nan

    market_cap = info.get("marketCap", None)

    return {
        "current_price": current_price,
        "market_cap": market_cap,
        "avg_volume_30d": avg_volume,
        "liquidity_score": liquidity_score,
        "52w_high": hi_52w,
        "52w_low": lo_52w,
        "distance_from_52w_high_pct": dist_from_high,
        "historical_volatility_annualized": hist_vol_annualized,
        "beta": beta,
        "correlation_to_spx": correlation,
    }


def _liquidity_score(avg_volume, price) -> float:
    """0-100 score from average daily dollar volume traded. Rough free-float-agnostic proxy."""
    if avg_volume is None or avg_volume != avg_volume or price is None:
        return np.nan
    dollar_vol = avg_volume * price
    # log-scale mapping: $1M/day -> ~20, $10M -> ~50, $100M -> ~80, $1B+ -> ~100
    if dollar_vol <= 0:
        return 0.0
    score = 20 * np.log10(max(dollar_vol, 1) / 1e5)
    return float(np.clip(score, 0, 100))
