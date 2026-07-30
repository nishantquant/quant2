"""analysis/risk.py — downside/tail-risk metrics. Risk Score: higher = LOWER risk."""

import numpy as np

from data.fetcher import get_price_history, get_info


def analyze_risk(ticker: str, confidence: float = 0.95) -> dict:
    hist = get_price_history(ticker, period="2y")
    info = get_info(ticker)

    if hist.empty:
        return {"error": f"No price history available for {ticker}."}

    close = hist["Close"].dropna()
    daily_ret = close.pct_change().dropna()

    max_dd = _max_drawdown(close)
    vol_annual = float(daily_ret.std() * np.sqrt(252)) if len(daily_ret) > 5 else np.nan

    downside = daily_ret[daily_ret < 0]
    downside_dev = float(downside.std() * np.sqrt(252)) if len(downside) > 5 else np.nan

    var_95 = float(np.percentile(daily_ret, (1 - confidence) * 100)) if len(daily_ret) > 20 else np.nan

    beta = info.get("beta")
    avg_volume = float(hist["Volume"].tail(30).mean()) if "Volume" in hist.columns else np.nan
    market_cap = info.get("marketCap")
    liquidity_risk = _liquidity_risk(avg_volume, market_cap)

    score = _risk_score(max_dd, vol_annual, downside_dev, beta, liquidity_risk)

    return {
        "max_drawdown": max_dd,
        "annualized_volatility": vol_annual,
        "downside_deviation": downside_dev,
        f"value_at_risk_{int(confidence*100)}pct_daily": var_95,
        "beta": beta,
        "liquidity_risk_0to100": liquidity_risk,
        "risk_score": score,
    }


def _max_drawdown(close) -> float:
    cummax = close.cummax()
    dd = (close / cummax) - 1.0
    return float(dd.min())


def _liquidity_risk(avg_volume, market_cap) -> float:
    """0 (illiquid, risky) to 100 (highly liquid, low risk)."""
    if avg_volume is None or avg_volume != avg_volume:
        return np.nan
    dollar_vol = avg_volume * 1.0  # already using shares; combine with cap below if present
    score = 20 * np.log10(max(dollar_vol, 1))
    return float(np.clip(score - 60, 0, 100))


def _risk_score(max_dd, vol_annual, downside_dev, beta, liquidity_risk) -> float:
    subs = []
    if max_dd is not None and max_dd == max_dd:
        subs.append(float(np.clip(100 + max_dd * 150, 0, 100)))  # -20% dd -> 70, -60% dd -> 10
    if vol_annual is not None and vol_annual == vol_annual:
        subs.append(float(np.clip(100 - vol_annual * 200, 0, 100)))  # 20% vol -> 60, 50% vol -> 0
    if downside_dev is not None and downside_dev == downside_dev:
        subs.append(float(np.clip(100 - downside_dev * 250, 0, 100)))
    if beta is not None and beta == beta:
        subs.append(float(np.clip(100 - abs(beta - 1) * 60, 0, 100)))
    if liquidity_risk is not None and liquidity_risk == liquidity_risk:
        subs.append(liquidity_risk)
    if not subs:
        return np.nan
    return float(np.mean(subs))
