"""
backtesting/engine.py

Historical backtesting for simple, transparent strategies (buy & hold, moving-average
crossover, momentum rotation, mean reversion). Every strategy operates only on data
that would have been available at each rebalance date (returns/indicators computed
from trailing windows), avoiding lookahead bias. Full survivorship-bias elimination
is not possible with a free static ticker list (delisted names are absent from
yfinance), so this is disclosed explicitly rather than glossed over.
"""

import numpy as np
import pandas as pd

from fetcher import get_price_history, get_benchmark_history


_FREQ_ALIASES = {"M": "ME", "Q": "QE", "W": "W", "ME": "ME", "QE": "QE"}


def backtest(tickers: list, strategy: str = "buy_and_hold", start_date: str = None,
             end_date: str = None, initial_capital: float = 100_000.0,
             rebalance_freq: str = "M", ma_fast: int = 50, ma_slow: int = 200,
             momentum_lookback_days: int = 90) -> dict:
    rebalance_freq = _FREQ_ALIASES.get(rebalance_freq, rebalance_freq)
    price_data = {}
    for t in tickers:
        h = get_price_history(t, period="5y")
        if h.empty:
            continue
        price_data[t] = h["Close"]

    if not price_data:
        return {"error": "No price data available for the requested tickers."}

    prices = pd.DataFrame(price_data).dropna(how="all")
    if start_date:
        prices = prices[prices.index >= pd.to_datetime(start_date)]
    if end_date:
        prices = prices[prices.index <= pd.to_datetime(end_date)]
    prices = prices.dropna()
    if prices.empty or len(prices) < 30:
        return {"error": "Insufficient overlapping price history for the selected date range."}

    if strategy == "buy_and_hold":
        weights_over_time = _equal_weight_static(prices)
    elif strategy == "ma_crossover":
        weights_over_time = _ma_crossover_weights(prices, ma_fast, ma_slow)
    elif strategy == "momentum_rotation":
        weights_over_time = _momentum_rotation_weights(prices, momentum_lookback_days, rebalance_freq)
    elif strategy == "mean_reversion":
        weights_over_time = _mean_reversion_weights(prices, rebalance_freq)
    else:
        return {"error": f"Unknown strategy '{strategy}'."}

    daily_returns = prices.pct_change().fillna(0)
    strat_daily_ret = (weights_over_time.shift(1).fillna(0) * daily_returns).sum(axis=1)
    equity_curve = initial_capital * (1 + strat_daily_ret).cumprod()

    bench = get_benchmark_history(period="5y")["Close"]
    bench = bench[(bench.index >= prices.index.min()) & (bench.index <= prices.index.max())]
    bench_ret = bench.pct_change().fillna(0)
    bench_curve = initial_capital * (1 + bench_ret).cumprod()

    metrics = _performance_metrics(strat_daily_ret, equity_curve)
    bench_metrics = _performance_metrics(bench_ret, bench_curve)

    return {
        "strategy": strategy,
        "tickers": list(prices.columns),
        "start": str(prices.index.min().date()),
        "end": str(prices.index.max().date()),
        "equity_curve": equity_curve,
        "benchmark_curve": bench_curve,
        "metrics": metrics,
        "benchmark_metrics": bench_metrics,
        "survivorship_bias_note": (
            "Backtest uses currently-listed tickers only; companies that were delisted, "
            "acquired, or went bankrupt during the window are not included, which biases "
            "historical performance upward. This is a known limitation of free data sources."
        ),
    }


def _equal_weight_static(prices):
    n = prices.shape[1]
    w = pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)
    return w


def _ma_crossover_weights(prices, fast, slow):
    ma_fast = prices.rolling(fast).mean()
    ma_slow = prices.rolling(slow).mean()
    signal = (ma_fast > ma_slow).astype(float)
    n_active = signal.sum(axis=1).replace(0, np.nan)
    weights = signal.div(n_active, axis=0).fillna(0)
    return weights


def _rebalance_dates(index, freq):
    periods = index.to_series().dt.to_period(freq)
    return periods.drop_duplicates(keep="last").index if False else index.to_series().groupby(periods).apply(lambda s: s.index[-1]).values


def _momentum_rotation_weights(prices, lookback_days, freq):
    rebal_idx = pd.Series(prices.index, index=prices.index).resample(freq).last().dropna()
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    lookback_periods = max(int(lookback_days / 21 * 21), 21)  # approx trading days
    current_weights = pd.Series(1.0 / prices.shape[1], index=prices.columns)
    for date in prices.index:
        if date in rebal_idx.values:
            window_start = prices.index.get_loc(date)
            start_idx = max(0, window_start - lookback_periods)
            if window_start - start_idx < 5:
                weights.loc[date] = current_weights
                continue
            past = prices.iloc[start_idx:window_start + 1]
            rets = past.iloc[-1] / past.iloc[0] - 1.0
            top = rets.nlargest(max(1, len(rets) // 2))
            new_weights = pd.Series(0.0, index=prices.columns)
            new_weights[top.index] = 1.0 / len(top)
            current_weights = new_weights
        weights.loc[date] = current_weights
    return weights


def _mean_reversion_weights(prices, freq):
    rebal_idx = pd.Series(prices.index, index=prices.index).resample(freq).last().dropna()
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current_weights = pd.Series(1.0 / prices.shape[1], index=prices.columns)
    for date in prices.index:
        if date in rebal_idx.values:
            window_start = prices.index.get_loc(date)
            start_idx = max(0, window_start - 21)
            if window_start - start_idx < 5:
                weights.loc[date] = current_weights
                continue
            past = prices.iloc[start_idx:window_start + 1]
            rets = past.iloc[-1] / past.iloc[0] - 1.0
            bottom = rets.nsmallest(max(1, len(rets) // 2))
            new_weights = pd.Series(0.0, index=prices.columns)
            new_weights[bottom.index] = 1.0 / len(bottom)
            current_weights = new_weights
        weights.loc[date] = current_weights
    return weights


def _performance_metrics(daily_ret: pd.Series, equity_curve: pd.Series) -> dict:
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0)
    n_years = len(daily_ret) / 252.0
    annualized_return = float((1 + total_return) ** (1 / n_years) - 1) if n_years > 0 else np.nan
    vol = float(daily_ret.std() * np.sqrt(252))
    sharpe = float(annualized_return / vol) if vol and vol == vol and vol != 0 else np.nan
    cummax = equity_curve.cummax()
    dd = (equity_curve / cummax) - 1.0
    max_dd = float(dd.min())
    win_rate = float((daily_ret > 0).sum() / (daily_ret != 0).sum()) if (daily_ret != 0).sum() > 0 else np.nan

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
    }
