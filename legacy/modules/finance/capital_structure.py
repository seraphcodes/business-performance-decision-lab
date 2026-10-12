def wacc(debt, equity, cost_of_debt, cost_of_equity=0.0):
    """Return the weighted average cost of capital using debt and equity weights.

    If only the cost of debt is supplied, the calculation reduces to the
    debt-weighted cost of debt.
    """
    total = debt + equity
    if total == 0:
        return 0.0

    debt_weight = debt / total
    equity_weight = equity / total
    return (debt_weight * cost_of_debt) + (equity_weight * cost_of_equity)


def retention_ratio(retained_earnings, net_income):
    """Return the retention ratio as retained earnings divided by net income."""
    if net_income == 0:
        return 0.0

    return retained_earnings / net_income

