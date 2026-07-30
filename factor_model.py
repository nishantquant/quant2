"""models/factor_model.py — combine sub-scores into one overall 0-100 score with user-adjustable weights."""

import numpy as np

from analysis_momentum import analyze_momentum
from analysis_value import analyze_value
from analysis_quality import analyze_quality
from analysis_growth import analyze_growth
from analysis_risk import analyze_risk
from analysis_ai_dependency import analyze_ai_dependency
from analysis_price_market import analyze_price_market

DEFAULT_WEIGHTS = {
    "momentum": 0.20,
    "value": 0.20,
    "quality": 0.25,
    "growth": 0.20,
    "risk": 0.15,
}


def run_full_analysis(ticker: str, sector_peers: list = None, weights: dict = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS
    w = {k: weights.get(k, DEFAULT_WEIGHTS[k]) for k in DEFAULT_WEIGHTS}
    total_w = sum(w.values()) or 1.0
    w = {k: v / total_w for k, v in w.items()}

    price_market = analyze_price_market(ticker)
    momentum = analyze_momentum(ticker, sector_peers=sector_peers)
    value = analyze_value(ticker)
    quality = analyze_quality(ticker)
    growth = analyze_growth(ticker)
    risk = analyze_risk(ticker)
    ai_dep = analyze_ai_dependency(ticker)

    subscores = {
        "momentum": momentum.get("momentum_score"),
        "value": value.get("value_score"),
        "quality": quality.get("quality_score"),
        "growth": growth.get("growth_score"),
        "risk": risk.get("risk_score"),
    }

    weighted_sum, weight_used = 0.0, 0.0
    for k, score in subscores.items():
        if score is not None and score == score:
            weighted_sum += score * w[k]
            weight_used += w[k]
    overall = (weighted_sum / weight_used) if weight_used > 0 else np.nan

    penalty = ai_dep.get("overall_score_penalty", 0.0)
    overall_after_penalty = float(np.clip(overall - penalty, 0, 100)) if overall == overall else np.nan

    return {
        "ticker": ticker,
        "weights_used": w,
        "subscores": subscores,
        "overall_score_pre_ai_penalty": overall,
        "ai_dependency_penalty": penalty,
        "overall_score": overall_after_penalty,
        "price_market": price_market,
        "momentum": momentum,
        "value": value,
        "quality": quality,
        "growth": growth,
        "risk": risk,
        "ai_dependency": ai_dep,
    }
