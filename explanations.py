"""
utils/explanations.py

Central repository of metric metadata. Every quantitative metric in the platform
is registered here with:
  - what it measures
  - why it matters
  - interpretation bands (value range -> label -> signal)

This module has ZERO computation logic. It only classifies/explains numbers that
other modules have already computed. Keeping this separate means every page in
the UI can pull the same explanation text for the same metric, and new metrics
are added by extending METRIC_DEFINITIONS instead of writing new UI strings
scattered across pages.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class Band:
    lo: float          # inclusive lower bound (-inf allowed)
    hi: float          # exclusive upper bound (+inf allowed)
    label: str         # e.g. "Strong"
    signal: str        # "positive" | "neutral" | "negative"


@dataclass
class MetricDef:
    key: str
    name: str
    what_it_measures: str
    why_it_matters: str
    bands: List[Band]
    higher_is_better: bool = True
    fmt: str = "{:.2f}"  # display format


def classify(value: Optional[float], bands: List[Band]) -> Tuple[str, str]:
    """Return (label, signal) for a value against a list of Bands.
    Bands are checked in order; the first matching band wins.
    Returns ('N/A', 'neutral') if value is None/NaN or no band matches.
    """
    if value is None:
        return "N/A", "neutral"
    try:
        if value != value:  # NaN check without importing numpy here
            return "N/A", "neutral"
    except TypeError:
        return "N/A", "neutral"
    for b in bands:
        if b.lo <= value < b.hi:
            return b.label, b.signal
    return "N/A", "neutral"


# ---------------------------------------------------------------------------
# METRIC DEFINITIONS
# ---------------------------------------------------------------------------

METRIC_DEFINITIONS = {

    "beta": MetricDef(
        key="beta", name="Beta",
        what_it_measures="Sensitivity of the stock's returns to overall market (S&P 500) returns.",
        why_it_matters="Determines how much systematic (market) risk the position adds to a portfolio; "
                        "high-beta names amplify both rallies and drawdowns.",
        bands=[
            Band(-999, 0.8, "Defensive / low volatility", "neutral"),
            Band(0.8, 1.2, "Market-like movement", "neutral"),
            Band(1.2, 999, "High volatility vs. market", "negative"),
        ],
    ),

    "distance_from_52w_high": MetricDef(
        key="distance_from_52w_high", name="Distance from 52-Week High",
        what_it_measures="Percentage below the trailing 52-week high closing price.",
        why_it_matters="A proxy for drawdown/technical damage and potential mean-reversion setups.",
        bands=[
            Band(-1, 5, "Near highs — strength", "positive"),
            Band(5, 20, "Moderate pullback", "neutral"),
            Band(20, 200, "Deep drawdown", "negative"),
        ],
    ),

    "momentum_score": MetricDef(
        key="momentum_score", name="Momentum Score",
        what_it_measures="Composite 0-100 score of 1/3/6/12-month returns and relative strength vs. sector and S&P 500.",
        why_it_matters="Momentum is a well-documented equity factor; persistence of trend often continues "
                        "over 3-12 month horizons (subject to sharp reversals at extremes).",
        bands=[
            Band(90, 101, "Exceptional momentum", "positive"),
            Band(70, 90, "Strong", "positive"),
            Band(50, 70, "Neutral", "neutral"),
            Band(-1, 50, "Weak", "negative"),
        ],
    ),

    "pe_ratio": MetricDef(
        key="pe_ratio", name="P/E Ratio (Trailing)",
        what_it_measures="Price paid per dollar of trailing twelve-month earnings.",
        why_it_matters="Baseline valuation multiple; must be read relative to growth, sector, and rate environment.",
        bands=[
            Band(-999, 15, "Statistically cheap", "positive"),
            Band(15, 25, "Reasonable / in-line", "neutral"),
            Band(25, 999, "Expensive vs. historical norm", "negative"),
        ],
    ),

    "peg_ratio": MetricDef(
        key="peg_ratio", name="PEG Ratio",
        what_it_measures="P/E divided by expected earnings growth rate — valuation adjusted for growth.",
        why_it_matters="Distinguishes 'expensive but growing fast' from 'expensive and stagnant'.",
        bands=[
            Band(-999, 1.0, "Potentially undervalued relative to growth", "positive"),
            Band(1.0, 2.0, "Fair valuation", "neutral"),
            Band(2.0, 999, "Potentially expensive", "negative"),
        ],
    ),

    "ev_ebitda": MetricDef(
        key="ev_ebitda", name="EV/EBITDA",
        what_it_measures="Enterprise value relative to EBITDA — capital-structure-neutral valuation multiple.",
        why_it_matters="Comparable across companies with different leverage/tax structures; a core sell-side multiple.",
        bands=[
            Band(-999, 8, "Cheap", "positive"),
            Band(8, 15, "Fair", "neutral"),
            Band(15, 999, "Rich", "negative"),
        ],
    ),

    "fcf_yield": MetricDef(
        key="fcf_yield", name="Free Cash Flow Yield",
        what_it_measures="Trailing free cash flow divided by market capitalization.",
        why_it_matters="Cash-based valuation check that is harder to manipulate via accounting choices than earnings.",
        bands=[
            Band(-999, 0.02, "Low cash generation relative to price", "negative"),
            Band(0.02, 0.05, "Moderate", "neutral"),
            Band(0.05, 999, "High cash yield", "positive"),
        ],
        fmt="{:.2%}",
    ),

    "roic": MetricDef(
        key="roic", name="ROIC (Return on Invested Capital)",
        what_it_measures="Operating profit after tax generated per dollar of invested capital (debt + equity).",
        why_it_matters="Core measure of business quality and competitive moat; sustainably high ROIC above the cost "
                        "of capital is the engine of long-term compounding.",
        bands=[
            Band(-999, 0.05, "Weak — value destructive if below cost of capital", "negative"),
            Band(0.05, 0.10, "Below average", "neutral"),
            Band(0.10, 999, "Strong", "positive"),
        ],
        fmt="{:.1%}",
    ),

    "roe": MetricDef(
        key="roe", name="ROE (Return on Equity)",
        what_it_measures="Net income divided by shareholder equity.",
        why_it_matters="Profitability on the equity base; can be inflated by leverage, so read alongside debt/equity.",
        bands=[
            Band(-999, 0.10, "Weak", "negative"),
            Band(0.10, 0.20, "Solid", "neutral"),
            Band(0.20, 999, "Excellent", "positive"),
        ],
        fmt="{:.1%}",
    ),

    "gross_margin": MetricDef(
        key="gross_margin", name="Gross Margin",
        what_it_measures="Revenue minus cost of goods sold, as a percentage of revenue.",
        why_it_matters="Pricing power and cost structure; typically the most stable margin line.",
        bands=[
            Band(-999, 0.25, "Low / commoditized", "negative"),
            Band(0.25, 0.50, "Moderate", "neutral"),
            Band(0.50, 1.01, "High — pricing power", "positive"),
        ],
        fmt="{:.1%}",
    ),

    "debt_to_equity": MetricDef(
        key="debt_to_equity", name="Debt / Equity",
        what_it_measures="Total debt relative to shareholder equity.",
        why_it_matters="Balance-sheet risk; higher leverage magnifies both returns and downside in a downturn.",
        bands=[
            Band(-999, 0.5, "Conservative balance sheet", "positive"),
            Band(0.5, 1.5, "Moderate leverage", "neutral"),
            Band(1.5, 999, "Highly levered", "negative"),
        ],
    ),

    "interest_coverage": MetricDef(
        key="interest_coverage", name="Interest Coverage (EBIT / Interest Expense)",
        what_it_measures="How many times operating income covers interest obligations.",
        why_it_matters="A key solvency check, especially in a higher-rate environment with refinancing risk.",
        bands=[
            Band(-999, 3, "Thin cushion — refinancing risk", "negative"),
            Band(3, 8, "Adequate", "neutral"),
            Band(8, 9999, "Strong cushion", "positive"),
        ],
    ),

    "revenue_growth": MetricDef(
        key="revenue_growth", name="Revenue Growth (YoY)",
        what_it_measures="Year-over-year change in total revenue.",
        why_it_matters="Top-line growth is the primary driver of long-run equity returns absent margin expansion.",
        bands=[
            Band(-999, 0.0, "Contracting", "negative"),
            Band(0.0, 0.10, "Modest growth", "neutral"),
            Band(0.10, 999, "Strong growth", "positive"),
        ],
        fmt="{:.1%}",
    ),

    "max_drawdown": MetricDef(
        key="max_drawdown", name="Maximum Drawdown",
        what_it_measures="Largest peak-to-trough decline over the lookback window.",
        why_it_matters="Captures tail/sequencing risk that volatility (std dev) alone does not.",
        bands=[
            Band(-1.0, -0.40, "Severe historical drawdown", "negative"),
            Band(-0.40, -0.20, "Moderate drawdown", "neutral"),
            Band(-0.20, 0.0, "Contained drawdown", "positive"),
        ],
        fmt="{:.1%}",
    ),

    "sharpe_ratio": MetricDef(
        key="sharpe_ratio", name="Sharpe Ratio",
        what_it_measures="Excess return per unit of total volatility.",
        why_it_matters="Standard risk-adjusted return measure; enables comparison across dissimilar strategies/assets.",
        bands=[
            Band(-999, 0.5, "Poor risk-adjusted return", "negative"),
            Band(0.5, 1.0, "Acceptable", "neutral"),
            Band(1.0, 999, "Strong risk-adjusted return", "positive"),
        ],
    ),

    "overall_score": MetricDef(
        key="overall_score", name="Overall Factor Score",
        what_it_measures="Weighted composite of Momentum, Value, Quality, Growth and Risk sub-scores (0-100), "
                         "net of the AI-dependency penalty.",
        why_it_matters="Single decision-support number for ranking and screening; weights are user-adjustable "
                        "and should never be treated as a black box — inspect the sub-scores.",
        bands=[
            Band(75, 101, "High-conviction opportunity", "positive"),
            Band(50, 75, "Reasonable / mixed", "neutral"),
            Band(-1, 50, "Weak overall profile", "negative"),
        ],
    ),
}


def explain(key: str, value: Optional[float]):
    """Return a dict with value, label, signal, and the metric metadata for display."""
    m = METRIC_DEFINITIONS.get(key)
    if m is None:
        return {"value": value, "label": "N/A", "signal": "neutral",
                "name": key, "what_it_measures": "", "why_it_matters": "", "fmt": "{:.2f}"}
    label, signal = classify(value, m.bands)
    return {
        "value": value, "label": label, "signal": signal,
        "name": m.name, "what_it_measures": m.what_it_measures,
        "why_it_matters": m.why_it_matters, "fmt": m.fmt,
    }
