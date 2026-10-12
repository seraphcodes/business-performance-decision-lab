def profit(revenue, costs):
    """Return profit as revenue minus costs."""
    return revenue - costs


def profit_margin(revenue, costs):
    """Return profit margin as a percentage of revenue."""
    if revenue == 0:
        return 0.0
    return (profit(revenue, costs) / revenue) * 100


def return_on_investment(profit_value, investment):
    """Return return on investment as a percentage of the investment."""
    if investment == 0:
        return 0.0
    return (profit_value / investment) * 100

