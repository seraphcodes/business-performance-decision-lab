"""Shared formatting helpers.

Every page was previously writing its own f"${x:,.2f}" / f"{x:.2f}%"
strings, with inconsistent use of the thousands separator. Centralizing
that here means the whole app formats numbers the same way, and a future
change (e.g. switching currency symbol) only happens in one place.
"""


def format_currency(value: float) -> str:
    """Format a number as US currency, e.g. 1234.5 -> '$1,234.50'."""
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    """Format a number as a percentage string, e.g. 12.3 -> '12.30%'."""
    return f"{value:.2f}%"
