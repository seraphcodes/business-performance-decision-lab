"""Business calculations for the What-If Simulator.

These are "pure" functions: numbers go in, a number comes out. They know
nothing about Streamlit or the database, which makes them easy to test.

Reused from the original project (decision_engine.py and
investment_decisions.py); only the argument names were made more general.
"""


def calculate_revenue(units, price):
    """Revenue = units sold x selling price per unit."""
    return units * price


def calculate_variable_cost(units, unit_cost):
    """Variable cost = units sold x cost per unit."""
    return units * unit_cost


def calculate_total_cost(fixed_cost, total_variable_cost):
    """Total cost = fixed costs + variable costs."""
    return fixed_cost + total_variable_cost


def calculate_profit(revenue, total_cost):
    """Profit = revenue - total cost."""
    return revenue - total_cost


def net_present_value(initial_investment, cash_flows, discount_rate):
    """NPV = today's value of future cash flows minus the money put in.

    cash_flows is a list: the first item arrives after year 1, and so on.
    discount_rate is a fraction (0.10 means 10%).
    """
    npv = -initial_investment
    for year, cash_flow in enumerate(cash_flows, start=1):
        npv += cash_flow / (1 + discount_rate) ** year
    return npv
