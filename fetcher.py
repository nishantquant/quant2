"""
data/fetcher.py

All external data access goes through this module. Wrapping yfinance here means:
  1. every other module gets a stable, predictable dict/DataFrame shape
  2. caching lives in one place (st.cache_data decorators)
  3. if yfinance's schema changes or a field is missing, we fail gracefully
     (return None for that field) rather than crashing the whole page

No paid data sources are used anywhere in this platform.
"""

import numpy as np
import pandas as pd
import yfinance as yf

try:
    import streamlit as st
    _cache = st.cache_data(ttl=60 * 30, show_spinner=False)  # 30 min cache
except Exception:  # allow module to be imported/tested outside Streamlit
    def _cache(fn):
        return fn


SP500_TICKER = "^GSPc" if False else "^GSPC"


@_cache
def get_price_history(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Return OHLCV history. Empty DataFrame on failure."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


@_cache
def get_info(ticker: str) -> dict:
    """Return the raw yfinance .info / .get_info() dict. Empty dict on failure."""
    try:
        t = yf.Ticker(ticker)
        try:
            info = t.get_info()
        except Exception:
            info = t.info
        return info or {}
    except Exception:
        return {}


@_cache
def get_financials(ticker: str) -> dict:
    """Bundle of financial statements needed for fundamental analysis.
    Returns dict of DataFrames: income_stmt, balance_sheet, cashflow (annual),
    plus quarterly variants for growth calcs. Missing statements -> empty DataFrame.
    """
    out = {}
    try:
        t = yf.Ticker(ticker)
        out["income_stmt"] = _safe_df(t.income_stmt)
        out["income_stmt_q"] = _safe_df(t.quarterly_income_stmt)
        out["balance_sheet"] = _safe_df(t.balance_sheet)
        out["cashflow"] = _safe_df(t.cashflow)
        out["cashflow_q"] = _safe_df(t.quarterly_cashflow)
    except Exception:
        pass
    return out


def _safe_df(x):
    if x is None:
        return pd.DataFrame()
    try:
        return x if isinstance(x, pd.DataFrame) else pd.DataFrame(x)
    except Exception:
        return pd.DataFrame()


@_cache
def get_benchmark_history(period: str = "2y") -> pd.DataFrame:
    return get_price_history(SP500_TICKER, period=period)


def safe_get_row(df: pd.DataFrame, *row_names):
    """Fetch the first matching row (by any of row_names, case-insensitive substring)
    from a yfinance financial statement DataFrame. Returns a pd.Series indexed by date, or None.
    """
    if df is None or df.empty:
        return None
    lower_index = {str(i).lower(): i for i in df.index}
    for name in row_names:
        for lidx, orig in lower_index.items():
            if name.lower() in lidx:
                return df.loc[orig]
    return None


def pct_change_over(df: pd.DataFrame, days: int) -> float:
    """Simple trailing return over N calendar days using close price. NaN-safe."""
    if df is None or df.empty or "Close" not in df.columns:
        return np.nan
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return np.nan
    end = closes.iloc[-1]
    cutoff = closes.index[-1] - pd.Timedelta(days=days)
    prior = closes[closes.index <= cutoff]
    if prior.empty:
        start = closes.iloc[0]
    else:
        start = prior.iloc[-1]
    if start == 0 or np.isnan(start):
        return np.nan
    return (end / start) - 1.0
