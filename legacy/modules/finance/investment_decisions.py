def net_present_value(initial_investment, cash_flows, discount_rate):
    npv = -initial_investment
    for year, cash_flow in enumerate(cash_flows, start=1):
        npv += cash_flow / (1 + discount_rate) ** year
    return npv

def payback_period(
        initial_investment, annual_cash_flows):
    
    if annual_cash_flows == 0:
        return None
    return (initial_investment / annual_cash_flows)
