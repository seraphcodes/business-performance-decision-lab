import numpy as np

def demand(price, demand_shift=0):
    return 100 - price + demand_shift

def supply(price, supply_shift=0):
    return price + supply_shift

def find_equilibrium(demand_shift=0, supply_shift=0):
    prices = np.arange(0, 101, 1)

    for p in prices:
        qd = demand(p, demand_shift)
        qs = supply(p, supply_shift)

        if abs(qd - qs) <= 1:
            return p, (qd + qs) / 2

    return None, None