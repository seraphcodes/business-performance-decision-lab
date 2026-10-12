"""Session 1 — Interdependence and gains from trade.

This logic previously lived directly inside app.py instead of its own
module like every other topic. The calculations are unchanged; they are
just given a proper home here so the economics engine is consistent
module-by-module.
"""


def opportunity_cost(good1, good2):
    """Return the opportunity cost of producing one more unit of good 1,
    measured in units of good 2 given up.
    """
    return good2 / good1


def compare_advantage(producer_a_oc, producer_b_oc):
    """Return which producer has the comparative advantage in good 1.

    Returns one of: "A", "B", or "equal".
    """
    if producer_a_oc < producer_b_oc:
        return "A"
    elif producer_a_oc > producer_b_oc:
        return "B"
    return "equal"
