"""ui/backtest_page.py — historical backtesting UI."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backtest_engine import backtest


def render():
    st.title("⏱️ Backtesting Engine")
    st.caption("Test simple, transparent rules against history. Past performance does not predict future results.")

    tickers_input = st.text_input("Tickers (comma-separated)", value="AAPL, MSFT, JPM, XOM")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    c1, c2, c3 = st.columns(3)
    strategy = c1.selectbox("Strategy", ["buy_and_hold", "ma_crossover", "momentum_rotation", "mean_reversion"],
                             format_func=lambda s: {
                                 "buy_and_hold": "Buy & Hold (equal weight)",
                                 "ma_crossover": "Moving Average Crossover",
                                 "momentum_rotation": "Momentum Rotation",
                                 "mean_reversion": "Mean Reversion",
                             }[s])
    initial_capital = c2.number_input("Initial Capital ($)", value=100000, step=10000)
    rebalance_freq = c3.selectbox("Rebalance Frequency", ["M", "Q", "W"],
                                   format_func=lambda f: {"M": "Monthly", "Q": "Quarterly", "W": "Weekly"}[f])

    c4, c5 = st.columns(2)
    start_date = c4.date_input("Start date", value=pd.Timestamp.today() - pd.Timedelta(days=365 * 3))
    end_date = c5.date_input("End date", value=pd.Timestamp.today())

    if st.button("Run backtest", type="primary"):
        with st.spinner("Running backtest..."):
            result = backtest(tickers, strategy=strategy, start_date=str(start_date), end_date=str(end_date),
                               initial_capital=initial_capital, rebalance_freq=rebalance_freq)
        if "error" in result:
            st.error(result["error"])
            return

        m, bm = result["metrics"], result["benchmark_metrics"]
        c = st.columns(4)
        c[0].metric("Total Return", f"{m['total_return']:+.1%}", f"vs S&P {bm['total_return']:+.1%}")
        c[1].metric("Annualized Return", f"{m['annualized_return']:+.1%}", f"vs S&P {bm['annualized_return']:+.1%}")
        c[2].metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}", f"vs S&P {bm['sharpe_ratio']:.2f}")
        c[3].metric("Max Drawdown", f"{m['max_drawdown']:.1%}", f"vs S&P {bm['max_drawdown']:.1%}")
        st.metric("Win Rate (daily)", f"{m['win_rate']:.1%}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result["equity_curve"].index, y=result["equity_curve"],
                                  name="Strategy", line=dict(color="#2563eb")))
        fig.add_trace(go.Scatter(x=result["benchmark_curve"].index, y=result["benchmark_curve"],
                                  name="S&P 500", line=dict(color="#9ca3af", dash="dash")))
        fig.update_layout(height=400, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10),
                           title=f"Equity Curve — {strategy} ({result['start']} to {result['end']})")
        st.plotly_chart(fig, use_container_width=True)

        st.warning(result["survivorship_bias_note"])
