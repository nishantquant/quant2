"""ui/portfolio_analyzer.py — holdings-level diversification, exposure, risk, and correlation."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from fetcher import get_price_history, get_info


def render():
    st.title("💼 Portfolio Analyzer")
    st.caption("Enter holdings to see diversification, sector exposure, risk, and correlation structure.")

    default_df = pd.DataFrame({"Ticker": ["AAPL", "MSFT", "JPM"], "Shares": [10, 5, 8]})
    holdings_df = st.data_editor(default_df, num_rows="dynamic", use_container_width=True)

    if st.button("Analyze portfolio", type="primary"):
        holdings_df = holdings_df.dropna()
        holdings_df["Ticker"] = holdings_df["Ticker"].str.upper()
        if holdings_df.empty:
            st.warning("Add at least one holding.")
            return
        with st.spinner("Analyzing portfolio..."):
            _analyze(holdings_df)


def _analyze(holdings_df):
    tickers = holdings_df["Ticker"].tolist()
    shares = dict(zip(holdings_df["Ticker"], holdings_df["Shares"]))

    prices, sectors, values = {}, {}, {}
    hist_data = {}
    for t in tickers:
        info = get_info(t)
        h = get_price_history(t, period="1y")
        if h.empty:
            st.warning(f"Skipping {t}: no price data.")
            continue
        price = float(h["Close"].iloc[-1])
        prices[t] = price
        sectors[t] = info.get("sector", "Unknown")
        values[t] = price * shares[t]
        hist_data[t] = h["Close"]

    if not values:
        st.error("No valid holdings to analyze.")
        return

    total_value = sum(values.values())
    weights = {t: v / total_value for t, v in values.items()}

    st.subheader("Position Weights")
    weight_df = pd.DataFrame({
        "Ticker": list(weights.keys()),
        "Market Value": [values[t] for t in weights],
        "Weight": [weights[t] for t in weights],
        "Sector": [sectors[t] for t in weights],
    }).sort_values("Weight", ascending=False)
    st.dataframe(weight_df.style.format({"Market Value": "${:,.0f}", "Weight": "{:.1%}"}),
                 use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(weight_df, names="Ticker", values="Weight", title="Position Weights")
        fig.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        sector_exposure = weight_df.groupby("Sector")["Weight"].sum().reset_index()
        fig2 = px.pie(sector_exposure, names="Sector", values="Weight", title="Sector Exposure")
        fig2.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Diversification")
    hhi = sum(w ** 2 for w in weights.values())
    effective_n = 1 / hhi if hhi > 0 else np.nan
    n_sectors = weight_df["Sector"].nunique()
    dc = st.columns(3)
    dc[0].metric("Holdings", len(weights))
    dc[1].metric("Effective # of Positions (1/HHI)", f"{effective_n:.1f}",
                 help="Herfindahl-based measure — accounts for concentration, not just position count. "
                      "A portfolio of 10 equal-weighted names has an effective N of 10; "
                      "one dominated by a single 80% position has an effective N near 1.3 even with 10 holdings.")
    dc[2].metric("Sectors Represented", n_sectors)

    st.subheader("Correlation Matrix")
    ret_df = pd.DataFrame({t: hist_data[t].pct_change() for t in hist_data}).dropna()
    if len(ret_df) > 10:
        corr = ret_df.corr()
        fig3 = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns,
                                          colorscale="RdBu", zmin=-1, zmax=1, reversescale=True))
        fig3.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig3, use_container_width=True)
        avg_corr = (corr.values.sum() - len(corr)) / (len(corr) ** 2 - len(corr)) if len(corr) > 1 else np.nan
        st.caption(f"Average pairwise correlation: {avg_corr:.2f}. Values near 1 indicate holdings move "
                   "together (limited diversification benefit); values near 0 or negative indicate genuine "
                   "diversification.")

    st.subheader("Portfolio Risk")
    if not ret_df.empty:
        w_vec = np.array([weights.get(t, 0) for t in ret_df.columns])
        port_ret = ret_df.values @ w_vec
        port_vol_annual = float(np.std(port_ret) * np.sqrt(252))
        cummax = pd.Series(port_ret).add(1).cumprod().cummax()
        curve = pd.Series(port_ret).add(1).cumprod()
        dd = (curve / cummax - 1).min()
        rc = st.columns(2)
        rc[0].metric("Portfolio Annualized Volatility", f"{port_vol_annual:.1%}")
        rc[1].metric("Trailing 1Y Max Drawdown", f"{dd:.1%}")
