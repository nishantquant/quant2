"""ui/dashboard.py — landing page: market snapshot, top opportunities, risk environment."""

import streamlit as st
import plotly.graph_objects as go

from fetcher import get_price_history
from sector_scanner import scan_all_sectors, DEFAULT_UNIVERSE
from formatting import fmt_value, SIGNAL_ICONS


def render():
    st.title("📊 Market Dashboard")
    st.caption("Free-data quantitative overview. Not investment advice — a decision-support tool.")

    _render_market_condition()
    st.divider()
    _render_sector_opportunity()
    st.divider()
    _render_risk_environment()


def _render_market_condition():
    st.subheader("Market Condition")
    spx = get_price_history("^GSPC", period="1y")
    vix = get_price_history("^VIX", period="6mo")

    cols = st.columns(4)
    if not spx.empty:
        close = spx["Close"]
        ret_1m = close.iloc[-1] / close.iloc[-22] - 1 if len(close) > 22 else float("nan")
        ret_ytd = close.iloc[-1] / close.iloc[0] - 1
        cols[0].metric("S&P 500", f"{close.iloc[-1]:,.0f}", f"{ret_1m:+.1%} (1M)")
        cols[1].metric("Trailing ~1Y Return", f"{ret_ytd:+.1%}")
    if not vix.empty:
        vix_level = vix["Close"].iloc[-1]
        vix_regime = "Complacent" if vix_level < 15 else "Normal" if vix_level < 22 else "Elevated fear" if vix_level < 30 else "Panic"
        cols[2].metric("VIX", f"{vix_level:.1f}", vix_regime)
    cols[3].metric("Data source", "Yahoo Finance", "free / delayed")

    if not spx.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spx.index, y=spx["Close"], name="S&P 500", line=dict(color="#2563eb")))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white",
                           title="S&P 500 — Trailing 1 Year")
        st.plotly_chart(fig, use_container_width=True)


def _render_sector_opportunity():
    st.subheader("Sector Opportunity Ranking")
    st.caption(f"Universe: {sum(len(v) for v in DEFAULT_UNIVERSE.values())} names across "
               f"{len(DEFAULT_UNIVERSE)} sectors. Computing live factor scores can take a moment.")
    if st.button("Run sector scan", type="primary"):
        with st.spinner("Scanning sectors..."):
            df = scan_all_sectors()
        st.session_state["sector_scan_df"] = df

    df = st.session_state.get("sector_scan_df")
    if df is not None:
        display_df = df[["sector", "opportunity_score", "avg_overall_score", "avg_return_3m",
                          "avg_volatility", "avg_pe"]].copy()
        display_df.columns = ["Sector", "Opportunity Score", "Avg Overall Score", "Avg 3M Return",
                               "Avg Volatility", "Avg P/E"]
        st.dataframe(display_df.style.format({
            "Opportunity Score": "{:.1f}", "Avg Overall Score": "{:.1f}",
            "Avg 3M Return": "{:+.1%}", "Avg Volatility": "{:.1%}", "Avg P/E": "{:.1f}",
        }), use_container_width=True, hide_index=True)
    else:
        st.info("Click 'Run sector scan' to compute live sector rankings from free market data.")


def _render_risk_environment():
    st.subheader("Risk Environment")
    vix = get_price_history("^VIX", period="1y")
    if vix.empty:
        st.info("VIX data unavailable.")
        return
    level = vix["Close"].iloc[-1]
    avg_1y = vix["Close"].mean()
    icon = SIGNAL_ICONS["positive"] if level < avg_1y else SIGNAL_ICONS["negative"]
    st.write(f"{icon} Current VIX **{level:.1f}** vs. 1-year average **{avg_1y:.1f}** — "
             f"{'below' if level < avg_1y else 'above'} the trailing norm.")
    st.caption("VIX measures 30-day implied S&P 500 volatility priced into options. Elevated readings "
               "typically coincide with equity drawdowns and wider risk premia; depressed readings can "
               "precede complacency-driven pullbacks.")
