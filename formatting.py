"""utils/formatting.py — small display helpers shared by every UI page."""

SIGNAL_COLORS = {
    "positive": "#1a7f37",
    "neutral": "#8a6d00",
    "negative": "#c0362c",
}

SIGNAL_ICONS = {
    "positive": "🟢",
    "neutral": "🟡",
    "negative": "🔴",
}


def fmt_value(value, fmt="{:.2f}"):
    if value is None:
        return "N/A"
    try:
        if value != value:
            return "N/A"
        return fmt.format(value)
    except (TypeError, ValueError):
        return str(value)


def fmt_large_number(n):
    """Format large numbers (market cap, volume) as e.g. $1.23B."""
    if n is None:
        return "N/A"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "N/A"
    sign = "-" if n < 0 else ""
    n = abs(n)
    for unit, div in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if n >= div:
            return f"{sign}${n/div:.2f}{unit}"
    return f"{sign}${n:.2f}"
