def future_value(present_value, interest_rate, years):
    return present_value * ((1 + interest_rate) ** years)

def present_value(future_value_amount, interest_rate, years):
    return future_value_amount / ((1 + interest_rate) ** years)

def compound_interest(principal, interest_rate,years):
    fv = future_value(principal, interest_rate, years)
    return fv - principal
