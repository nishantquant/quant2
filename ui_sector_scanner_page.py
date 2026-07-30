"""ui/sector_scanner_page.py — sector-adjusted screening and rankings."""

import streamlit as st

from sector_scanner import scan_sector, DEFAULT_UNIVERSE
from formatting import fmt_value


def render():
    st.title("🏭 Sector Scanner")
    st.caption("Stocks are ranked only against sector peers — technology is never compared directly against utilities.")

    sector = st.selectbox("Sector", list(DEFAULT_UNIVERSE.keys()))
    custom = st.text_input("Custom ticker list for this sector (comma-separated, optional)")
    tickers = [t.strip().upper() for t in custom.split(",") if t.strip()] if custom else None

    if st.button("Scan sector", type="primary"):
        with st.spinner(f"Scanning {sector}..."):
            result = scan_sector(sector, tickers)
        st.session_state["last_sector_scan"] = result

    result = st.session_state.get("last_sector_scan")
    if not result:
        st.info("Select a sector and click Scan.")
        return
    if "error" in result:
        st.error(result["error"])
        return

    s = result["summary"]
    c = st.columns(4)
    c[0].metric("Avg 3M Return", fmt_value(s.get("avg_return_3m"), "{:+.1%}"))
    c[1].metric("Avg Volatility", fmt_value(s.get("avg_volatility"), "{:.1%}"))
    c[2].metric("Avg P/E", fmt_value(s.get("avg_pe")))
    c[3].metric("Avg Overall Score", fmt_value(s.get("avg_overall_score"), "{:.1f}"))

    best = result["best_in_category"]
    st.subheader("Best in Category")
    bc = st.columns(4)
    bc[0].metric("Best Overall", best.get("best_overall") or "N/A")
    bc[1].metric("Most Undervalued", best.get("most_undervalued") or "N/A")
    bc[2].metric("Lowest Risk", best.get("lowest_risk") or "N/A")
    bc[3].metric("Highest Momentum", best.get("highest_momentum") or "N/A")

    st.subheader("Full Ranking")
    df = result["table"].copy()
    if "overall_score" in df.columns:
        df = df.sort_values("overall_score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)
