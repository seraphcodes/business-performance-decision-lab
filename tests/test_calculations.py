"""Tests for src/calculations.py.

Each expected number below was worked out by hand first, then written
here. A test that only repeats the code's own formula proves nothing.
"""
from src.calculations import (
    calculate_profit,
    calculate_revenue,
    calculate_total_cost,
    calculate_variable_cost,
    net_present_value,
)


def close(a, b, tolerance=0.01):
    return abs(a - b) <= tolerance


def test_revenue():
    assert calculate_revenue(100, 2.5) == 250


def test_profit_from_revenue_and_costs():
    revenue = calculate_revenue(100, 2.5)            # 250
    variable = calculate_variable_cost(100, 1.0)     # 100
    total = calculate_total_cost(50, variable)       # 150
    assert calculate_profit(revenue, total) == 100


def test_zero_units_leaves_only_fixed_cost_loss():
    total = calculate_total_cost(50, calculate_variable_cost(0, 1.0))
    assert calculate_profit(calculate_revenue(0, 2.5), total) == -50


def test_npv_textbook_example():
    # -1000 + 400/1.1 + 500/1.1^2 + 600/1.1^3 = 227.65 (worked by hand)
    assert close(net_present_value(1000, [400, 500, 600], 0.10), 227.65)


def test_npv_with_zero_rate_is_simple_sum():
    assert net_present_value(150, [100, 100], 0.0) == 50


def test_npv_with_no_cash_flows_is_minus_investment():
    assert net_present_value(1000, [], 0.10) == -1000
