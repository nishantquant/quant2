"""analysis/momentum.py — trailing returns, relative strength, and a 0-100 momentum score."""

import numpy as np

from fetcher import get_price_history, get_benchmark_history, pct_change_over


def analyze_momentum(ticker: str, sector_peers: list = None) -> dict:
    hist = get_price_history(ticker, period="2y")
    bench = get_benchmark_history(period="2y")

    if hist.empty:
        return {"error": f"No price history available for {ticker}."}

    r1m = pct_change_over(hist, 30)
    r3m = pct_change_over(hist, 91)
    r6m = pct_change_over(hist, 182)
    r12m = pct_change_over(hist, 365)

    bench_r3m = pct_change_over(bench, 91) if not bench.empty else np.nan
    bench_r12m = pct_change_over(bench, 365) if not bench.empty else np.nan

    rs_vs_spx_3m = (r3m - bench_r3m) if (r3m == r3m and bench_r3m == bench_r3m) else np.nan
    rs_vs_spx_12m = (r12m - bench_r12m) if (r12m == r12m and bench_r12m == bench_r12m) else np.nan

    rs_vs_sector = np.nan
    sector_avg_r3m = np.nan
    if sector_peers:
        peer_returns = []
        for p in sector_peers:
            if p == ticker:
                continue
            ph = get_price_history(p, period="2y")
            if not ph.empty:
                pr = pct_change_over(ph, 91)
                if pr == pr:
                    peer_returns.append(pr)
        if peer_returns:
            sector_avg_r3m = float(np.mean(peer_returns))
            if r3m == r3m:
                rs_vs_sector = r3m - sector_avg_r3m

    score = _momentum_score(r1m, r3m, r6m, r12m, rs_vs_spx_3m, rs_vs_sector)

    return {
        "return_1m": r1m,
        "return_3m": r3m,
        "return_6m": r6m,
        "return_12m": r12m,
        "relative_strength_vs_spx_3m": rs_vs_spx_3m,
        "relative_strength_vs_spx_12m": rs_vs_spx_12m,
        "relative_strength_vs_sector_3m": rs_vs_sector,
        "sector_avg_return_3m": sector_avg_r3m,
        "momentum_score": score,
    }


def _momentum_score(r1m, r3m, r6m, r12m, rs_spx, rs_sector) -> float:
    """
    Weighted composite mapped to 0-100 via a logistic-style squashing of a
    raw z-like score. Weights emphasize 3m/6m (the strongest documented momentum
    windows) over 1m (noisier, more mean-reverting) and 12m (can include stale trend).
    """
    components = []
    weights = []
    for val, w in [(r1m, 0.10), (r3m, 0.30), (r6m, 0.30), (r12m, 0.15),
                   (rs_spx, 0.10), (rs_sector, 0.05)]:
        if val == val:  # not NaN
            components.append(val)
            weights.append(w)
    if not components:
        return np.nan
    weights = np.array(weights) / np.sum(weights)
    raw = float(np.dot(components, weights))
    # squash: raw return of 0 -> 50; +/-30% return roughly maps to 100/0
    score = 50 + (raw / 0.30) * 50
    return float(np.clip(score, 0, 100))
