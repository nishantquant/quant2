"""
app.py — Quantitative Equity Research Platform

Entry point. Run with:
    streamlit run app.py

All data comes from free, public sources (Yahoo Finance via yfinance). This is
a transparent decision-support tool, not a trading bot: it never places trades
and every score shown is explainable back to its component metrics.
"""

import streamlit as st

import ui_dashboard as dashboard
import ui_stock_analyzer as stock_analyzer
import ui_sector_scanner_page as sector_scanner_page
import ui_portfolio_analyzer as portfolio_analyzer
import ui_backtest_page as backtest_page

st.set_page_config(page_title="Quant Research Terminal", page_icon="📈", layout="wide")

PAGES = {
    "Dashboard": dashboard,
    "Stock Analyzer": stock_analyzer,
    "Sector Scanner": sector_scanner_page,
    "Portfolio Analyzer": portfolio_analyzer,
    "Backtesting Engine": backtest_page,
}

with st.sidebar:
    st.title("📈 Quant Research Terminal")
    st.caption("Free-data quantitative equity research — for education and decision support, not automated trading.")
    page = st.radio("Navigate", list(PAGES.keys()))
    st.divider()
    st.caption(
        "**Data:** Yahoo Finance (yfinance), delayed, free tier.\n\n"
        "**Disclaimer:** Not investment advice. Scores and simulations are built from historical data and "
        "explicit, inspectable formulas — read the methodology notes on each page before acting on any output."
    )

PAGES[page].render()
