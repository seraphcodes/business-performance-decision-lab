"""Shared formatting helpers.

Every number shown in the app goes through these functions, so the whole
app formats money and percentages the same way.
"""

# The Online Retail II data is in British pounds.
GBP = "£"


def format_currency(value: float, symbol: str = GBP) -> str:
    """Format a number as money in pounds by default, e.g. 1234.5 -> '£1,234.50'.

    Pass another symbol for other currencies. Negative numbers put the minus sign first
    ('-£5.00'), not after the symbol ('£-5.00').
    """
    rounded = round(value, 2)
    sign = "-" if rounded < 0 else ""
    return f"{sign}{symbol}{abs(rounded):,.2f}"


def format_percent(value: float) -> str:
    """Format a number as a percentage string, e.g. 12.3 -> '12.30%'."""
    return f"{value:.2f}%"
