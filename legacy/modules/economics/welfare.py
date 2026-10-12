def consumer_surplus(willingness_to_pay, market_price):
    return willingness_to_pay - market_price


def producer_surplus(market_price, production_cost):
    return market_price - production_cost


def total_welfare(consumer_surplus_value, producer_surplus_value):
    return consumer_surplus_value + producer_surplus_value