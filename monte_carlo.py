"""
models/monte_carlo.py

Monte Carlo forecasting via Geometric Brownian Motion, calibrated to the stock's
own trailing daily return distribution (mean and volatility over the lookback
window). This is a MODEL, not a prediction: it assumes past drift/volatility
carry into the future, which is a strong and frequently wrong assumption
(regime changes, earnings events, macro shocks are not captured). Present
results as scenario probabilities conditioned on historical parameters, never
as forecasts of what will happen.
"""

import numpy as np

from fetcher import get_price_history


def run_monte_carlo(ticker: str, n_simulations: int = 2000, horizon_days: int = 252,
                     confidence: float = 0.90, lookback: str = "2y", seed: int = None) -> dict:
    hist = get_price_history(ticker, period=lookback)
    if hist.empty or len(hist) < 30:
        return {"error": f"Insufficient price history for {ticker} to calibrate a simulation."}

    close = hist["Close"].dropna()
    log_ret = np.log(close / close.shift(1)).dropna()
    mu = float(log_ret.mean())
    sigma = float(log_ret.std())
    s0 = float(close.iloc[-1])

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_simulations, horizon_days))
    daily_log_ret = (mu - 0.5 * sigma ** 2) + sigma * z
    cum_log_ret = np.cumsum(daily_log_ret, axis=1)
    price_paths = s0 * np.exp(cum_log_ret)

    ending_prices = price_paths[:, -1]
    ending_returns = ending_prices / s0 - 1.0

    prob_positive = float(np.mean(ending_returns > 0) * 100)
    prob_loss = float(np.mean(ending_returns < 0) * 100)
    expected_return = float(np.mean(ending_returns) * 100)
    median_return = float(np.median(ending_returns) * 100)

    lo_pct = (1 - confidence) / 2 * 100
    hi_pct = 100 - lo_pct
    ci_low = float(np.percentile(ending_returns, lo_pct) * 100)
    ci_high = float(np.percentile(ending_returns, hi_pct) * 100)

    downside_losses = ending_returns[ending_returns < 0]
    expected_downside = float(np.mean(downside_losses) * 100) if len(downside_losses) else 0.0
    var_5pct = float(np.percentile(ending_returns, 5) * 100)

    # Subsample paths for charting so we don't ship thousands of series to the UI
    n_display = min(200, n_simulations)
    display_paths = price_paths[:n_display]

    return {
        "ticker": ticker,
        "n_simulations": n_simulations,
        "horizon_days": horizon_days,
        "confidence": confidence,
        "calibration": {"daily_mean_log_return": mu, "daily_volatility": sigma, "start_price": s0},
        "expected_return_pct": expected_return,
        "median_return_pct": median_return,
        "probability_positive_return_pct": prob_positive,
        "probability_loss_pct": prob_loss,
        "confidence_interval_pct": (ci_low, ci_high),
        "expected_downside_pct": expected_downside,
        "value_at_risk_5pct_pct": var_5pct,
        "display_paths": display_paths.tolist(),
        "methodology_note": (
            "Geometric Brownian Motion calibrated to trailing daily log-return mean and "
            "volatility. Assumes returns are i.i.d. and normally distributed, and that the "
            "historical drift/volatility regime persists — assumptions that frequently fail "
            "around earnings, macro shocks, and regime changes."
        ),
    }
