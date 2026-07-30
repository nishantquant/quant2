"""ui/stock_analyzer.py — the core single-stock deep-dive page."""

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from factor_model import run_full_analysis, DEFAULT_WEIGHTS
from monte_carlo import run_monte_carlo
from fetcher import get_price_history
from explanations import explain
from formatting import fmt_value, fmt_large_number, SIGNAL_ICONS


def render():
    st.title("🔍 Stock Analyzer")

    col1, col2 = st.columns([2, 1])
    ticker = col1.text_input("Ticker", value="AAPL").strip().upper()
    with col2:
        with st.expander("Factor weights"):
            weights = {}
            for k, default in DEFAULT_WEIGHTS.items():
                weights[k] = st.slider(k.capitalize(), 0.0, 1.0, default, 0.05, key=f"w_{k}")

    if not ticker:
        st.info("Enter a ticker to begin.")
        return

    if st.button("Run analysis", type="primary") or st.session_state.get("last_ticker") == ticker:
        st.session_state["last_ticker"] = ticker
        with st.spinner(f"Analyzing {ticker}..."):
            result = run_full_analysis(ticker, weights=weights)
        _render_result(ticker, result)


def _metric_card(col, key, value, extra_fmt=None):
    e = explain(key, value)
    fmt = extra_fmt or e["fmt"]
    icon = SIGNAL_ICONS.get(e["signal"], "")
    col.metric(e["name"], f"{icon} {fmt_value(value, fmt)}", help=f"{e['what_it_measures']}\n\n{e['why_it_matters']}\n\nCurrent read: {e['label']}")


def _render_result(ticker, result):
    if "error" in result.get("price_market", {}):
        st.error(result["price_market"]["error"])
        return

    pm = result["price_market"]
    st.header(f"{ticker} — Overview")

    overall = result["overall_score"]
    e = explain("overall_score", overall)
    st.metric("Overall Factor Score", f"{SIGNAL_ICONS.get(e['signal'],'')} {fmt_value(overall, '{:.1f}')} / 100",
               help=f"{e['what_it_measures']} {e['why_it_matters']} Current read: {e['label']}")
    st.caption(f"Pre-AI-dependency-penalty score: {fmt_value(result['overall_score_pre_ai_penalty'], '{:.1f}')} "
               f"— penalty applied: -{fmt_value(result['ai_dependency_penalty'], '{:.1f}')} pts")

    cols = st.columns(5)
    cols[0].metric("Price", fmt_value(pm.get("current_price"), "${:.2f}"))
    cols[1].metric("Market Cap", fmt_large_number(pm.get("market_cap")))
    cols[2].metric("52W High", fmt_value(pm.get("52w_high"), "${:.2f}"))
    cols[3].metric("52W Low", fmt_value(pm.get("52w_low"), "${:.2f}"))
    _metric_card(cols[4], "beta", pm.get("beta"))

    hist = get_price_history(ticker, period="1y")
    if not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], line=dict(color="#2563eb"), name="Close"))
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10),
                           title=f"{ticker} — Trailing 1 Year")
        st.plotly_chart(fig, use_container_width=True)

    tabs = st.tabs(["Momentum", "Value", "Quality", "Growth", "Risk", "AI Dependency", "Monte Carlo"])

    with tabs[0]:
        m = result["momentum"]
        c = st.columns(3)
        _metric_card(c[0], "momentum_score", m.get("momentum_score"))
        c[1].metric("1M / 3M Return", f"{fmt_value(m.get('return_1m'),'{:+.1%}')} / {fmt_value(m.get('return_3m'),'{:+.1%}')}")
        c[2].metric("6M / 12M Return", f"{fmt_value(m.get('return_6m'),'{:+.1%}')} / {fmt_value(m.get('return_12m'),'{:+.1%}')}")
        st.caption(f"Relative strength vs. S&P 500 (3M): {fmt_value(m.get('relative_strength_vs_spx_3m'), '{:+.1%}')}")

    with tabs[1]:
        v = result["value"]
        c = st.columns(3)
        _metric_card(c[0], "pe_ratio", v.get("pe_ratio"))
        _metric_card(c[1], "peg_ratio", v.get("peg_ratio"))
        _metric_card(c[2], "ev_ebitda", v.get("ev_ebitda"))
        c2 = st.columns(3)
        _metric_card(c2[0], "fcf_yield", v.get("fcf_yield"))
        c2[1].metric("Forward P/E", fmt_value(v.get("forward_pe")))
        c2[2].metric("Price/Book", fmt_value(v.get("price_to_book")))
        st.caption("Fair value note: this platform reports relative valuation multiples, not a single-point "
                   "DCF fair value. Combine with growth/quality context above and peer/sector comparisons "
                   "before drawing a fair-value range.")

    with tabs[2]:
        q = result["quality"]
        c = st.columns(3)
        _metric_card(c[0], "roic", q.get("roic"))
        _metric_card(c[1], "roe", q.get("roe"))
        _metric_card(c[2], "gross_margin", q.get("gross_margin"))
        c2 = st.columns(3)
        _metric_card(c2[0], "debt_to_equity", q.get("debt_to_equity"))
        _metric_card(c2[1], "interest_coverage", q.get("interest_coverage"))
        c2[2].metric("FCF Positive Years", fmt_value(q.get("fcf_consistency_pct_positive_years"), "{:.0f}%"))

    with tabs[3]:
        g = result["growth"]
        c = st.columns(3)
        _metric_card(c[0], "revenue_growth", g.get("revenue_growth_yoy"))
        c[1].metric("Earnings Growth YoY", fmt_value(g.get("earnings_growth_yoy"), "{:+.1%}"))
        c[2].metric("Revenue CAGR (multi-yr)", fmt_value(g.get("revenue_cagr_multi_year"), "{:+.1%}"))
        c2 = st.columns(2)
        c2[0].metric("FCF Growth YoY", fmt_value(g.get("fcf_growth_yoy"), "{:+.1%}"))
        c2[1].metric("Earnings Stability", fmt_value(g.get("earnings_stability_score"), "{:.0f}/100"))

    with tabs[4]:
        r = result["risk"]
        c = st.columns(3)
        _metric_card(c[0], "max_drawdown", r.get("max_drawdown"))
        c[1].metric("Annualized Volatility", fmt_value(r.get("annualized_volatility"), "{:.1%}"))
        c[2].metric("Downside Deviation", fmt_value(r.get("downside_deviation"), "{:.1%}"))
        var_key = [k for k in r if k.startswith("value_at_risk")]
        if var_key:
            st.metric("Value at Risk (95%, daily)", fmt_value(r.get(var_key[0]), "{:+.2%}"))
        st.caption("Risk Score is inverted: a HIGHER score means LOWER risk.")

    with tabs[5]:
        ai = result["ai_dependency"]
        st.warning(ai.get("methodology_note", ""))
        c = st.columns(3)
        c[0].metric("AI Keyword Mentions", ai.get("ai_keyword_mentions"))
        c[1].metric("AI Dependency Risk", fmt_value(ai.get("ai_dependency_risk_0to100"), "{:.0f}/100"))
        c[2].metric("Score Penalty Applied", f"-{fmt_value(ai.get('overall_score_penalty'), '{:.1f}')} pts")

    with tabs[6]:
        _render_monte_carlo(ticker)


def _render_monte_carlo(ticker):
    c1, c2, c3 = st.columns(3)
    n_sims = c1.selectbox("Simulations", [500, 1000, 2000, 5000], index=2)
    horizon = c2.selectbox("Forecast horizon (trading days)", [21, 63, 126, 252], index=3,
                            format_func=lambda d: {21: "1 Month", 63: "3 Months", 126: "6 Months", 252: "1 Year"}[d])
    confidence = c3.selectbox("Confidence interval", [0.80, 0.90, 0.95], index=1,
                               format_func=lambda x: f"{x:.0%}")

    if st.button("Run Monte Carlo simulation"):
        with st.spinner("Simulating..."):
            mc = run_monte_carlo(ticker, n_simulations=n_sims, horizon_days=horizon, confidence=confidence)
        if "error" in mc:
            st.error(mc["error"])
            return

        c = st.columns(4)
        c[0].metric("Expected Return", f"{mc['expected_return_pct']:+.1f}%")
        c[1].metric("Probability of Positive Return", f"{mc['probability_positive_return_pct']:.0f}%",
                    help=f"In {mc['n_simulations']:,} simulations calibrated to {ticker}'s trailing return "
                         f"distribution, this share ended above the starting price. This describes what the "
                         f"model produced historically-conditioned — not a guarantee of future outcomes.")
        c[2].metric("Probability of Loss", f"{mc['probability_loss_pct']:.0f}%")
        c[3].metric("Expected Downside (avg. of losing paths)", f"{mc['expected_downside_pct']:.1f}%")

        ci = mc["confidence_interval_pct"]
        st.write(f"**{mc['confidence']:.0%} confidence interval:** {ci[0]:+.1f}% to {ci[1]:+.1f}%")

        paths = np.array(mc["display_paths"])
        fig = go.Figure()
        for i in range(min(100, len(paths))):
            fig.add_trace(go.Scatter(y=paths[i], mode="lines", line=dict(width=0.5, color="rgba(37,99,235,0.15)"),
                                      showlegend=False, hoverinfo="skip"))
        median_path = np.median(paths, axis=0)
        fig.add_trace(go.Scatter(y=median_path, mode="lines", line=dict(width=2, color="#dc2626"), name="Median path"))
        fig.update_layout(height=350, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10),
                           title=f"{ticker} — Simulated Price Paths ({mc['horizon_days']} trading days)")
        st.plotly_chart(fig, use_container_width=True)

        st.caption(mc["methodology_note"])
