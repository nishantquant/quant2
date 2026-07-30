# Quant Research Terminal

A transparent, explainable quantitative equity research platform built entirely on
**free, public data** (Yahoo Finance via `yfinance`). It is a decision-support tool,
not a trading bot — it never places trades, and every score is traceable back to the
metrics and formulas that produced it.

## What it does

- **Stock Analyzer** — full single-ticker breakdown: price/market structure, momentum,
  value, quality, growth, and risk, each as a 0–100 sub-score, combined into an
  adjustable-weight **Overall Factor Score**, net of a heuristic **AI-dependency
  penalty**. Every metric shows its value, definition, why it matters, and an
  interpretation band. Includes a **Monte Carlo** forecasting tab (GBM, configurable
  simulations/horizon/confidence).
- **Sector Scanner** — sector-adjusted ranking (tech is only ever compared to tech,
  never to utilities), with best-overall / most-undervalued / lowest-risk /
  highest-momentum picks per sector.
- **Portfolio Analyzer** — enter holdings (ticker + shares) and see position/sector
  weights, an effective-N diversification measure, a correlation matrix, and
  portfolio-level volatility and drawdown.
- **Backtesting Engine** — buy & hold, moving-average crossover, momentum rotation, and
  mean-reversion strategies, benchmarked against the S&P 500, with Sharpe ratio, max
  drawdown, win rate. A survivorship-bias disclosure is shown on every result, since a
  free static ticker universe cannot include delisted/acquired names.
- **Dashboard** — S&P 500 snapshot, VIX-based risk regime, and a live sector opportunity
  scan.

## Project structure

This is a **flat, single-folder** layout — every file sits at the top level (no
subfolders), which makes it easy to upload file-by-file to GitHub's web UI. Grouping
is expressed through filename prefixes instead of directories:

```
quant_platform_flat/
├── app.py                        # Streamlit entry point / navigation
├── fetcher.py                    # yfinance wrapper, caching, safe field access
├── analysis_price_market.py      # beta, correlation, liquidity, 52w range, volatility
├── analysis_momentum.py          # trailing returns, relative strength, momentum score
├── analysis_value.py             # P/E, PEG, EV/EBITDA, FCF yield, value score
├── analysis_quality.py           # ROIC, ROE, margins, leverage, coverage, quality score
├── analysis_growth.py            # revenue/EPS growth, stability, FCF growth, growth score
├── analysis_risk.py              # drawdown, vol, downside deviation, VaR, risk score
├── analysis_ai_dependency.py     # heuristic AI-narrative exposure / penalty
├── factor_model.py               # combines all sub-scores into the Overall Score
├── monte_carlo.py                # GBM price-path simulation
├── sector_scanner.py             # sector-adjusted ranking across a peer universe
├── backtest_engine.py            # historical strategy backtests vs. S&P 500
├── ui_dashboard.py                (one Streamlit page module per app page)
├── ui_stock_analyzer.py
├── ui_sector_scanner_page.py
├── ui_portfolio_analyzer.py
├── ui_backtest_page.py
├── explanations.py               # every metric's definition/importance/interpretation bands
├── formatting.py                 # number/currency formatting, signal colors
└── requirements.txt
```

All 20 `.py` files go directly into the root of your GitHub repo — no folders needed.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Free deployment (Streamlit Community Cloud)

1. Push this folder to a public (or private, with Community Cloud connected) GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. "New app" → select the repo → set the main file path to `app.py` → Deploy.
4. No API keys or secrets are required — all data is fetched live from Yahoo Finance
   at request time via `yfinance`.

Community Cloud's free tier sleeps after inactivity and has modest compute — the
30-minute cache (`st.cache_data(ttl=1800)` in `data/fetcher.py`) keeps repeated
requests fast and reduces Yahoo Finance load.

## Known limitations (read before trusting any output)

- **Data provider**: Yahoo Finance data is delayed and occasionally has missing or
  restated fields (especially for small/mid caps and non-US names). Every metric
  degrades to "N/A" rather than crashing when a field is unavailable — but "N/A" means
  the sub-score is being computed from fewer inputs, not that the company is neutral.
- **AI-dependency score is a proxy**, built from business-description keyword density,
  a valuation-expansion heuristic, and realized volatility — not a verified
  segment-revenue disclosure. Treat it as a caution flag, not a measurement.
- **Monte Carlo** assumes returns are i.i.d. and calibrated to the trailing lookback
  window's own mean/volatility (Geometric Brownian Motion). It will not anticipate
  regime changes, earnings surprises, or macro shocks.
- **Backtests use only currently-listed tickers** — delisted, acquired, or bankrupt
  companies are absent from the universe, which biases historical performance upward
  (survivorship bias). This is disclosed on every backtest result.
- **No fundamentals-grade DCF** is computed — the Value module reports relative
  multiples (P/E, PEG, EV/EBITDA, FCF yield) rather than a discounted-cash-flow
  intrinsic value, since a defensible DCF needs assumptions (terminal growth, discount
  rate) that are subjective by nature; a single "fair value" number from those inputs
  would overstate precision.
- This tool does not place trades, connect to a brokerage, or provide personalized
  investment advice. It is for research and education.

## Extending

- **More sectors/tickers**: edit `DEFAULT_UNIVERSE` in `models/sector_scanner.py`, or
  pass a custom ticker list from the Sector Scanner page.
- **New metrics**: add the calculation to the relevant `analysis/*.py` module, then
  register its explanation (what it measures / why it matters / interpretation bands)
  in `utils/explanations.py` — the UI picks it up automatically via `explain(key, value)`.
- **New backtest strategies**: add a `_your_strategy_weights(prices, ...)` function to
  `backtesting/engine.py` and wire it into the `strategy ==` dispatch in `backtest()`.
