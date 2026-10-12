from modules.finance.finance_intro import profit as finance_profit
from modules.finance.financing_decisions import (
    debt_ratio as finance_debt_ratio,
    equity_ratio as finance_equity_ratio,
)
from modules.finance.investment_decisions import (
    payback_period as finance_payback_period,
)
from utils.decision_config import (
    CURRENT_RATIO_GOOD,
    CURRENT_RATIO_MINIMUM,
    CURRENT_RATIO_STRONG,
    DEBT_RATIO_CAUTION,
    DEBT_RATIO_STRONG,
    DECISION_ANALYSIS,
    DECISION_CAUTION,
    DECISION_PROCEED,
    DEMAND_HIGH,
    DEMAND_LOW,
    DEMAND_MEDIUM,
    NPV_POSITIVE,
    PAYBACK_EXCELLENT,
    PAYBACK_GOOD,
    PAYBACK_MODERATE,
    PROFIT_HIGH,
    PROFIT_LOW,
    PROFIT_MEDIUM,
    QUICK_RATIO_GOOD,
    QUICK_RATIO_MINIMUM,
    QUICK_RATIO_STRONG,
)
from utils.formatting import format_currency


def calculate_revenue(customers, selling_price):
    return customers * selling_price


def calculate_variable_cost(customers, variable_cost_):
    return customers * variable_cost_


def calculate_total_cost(fixed_cost, total_variable_cost):
    return fixed_cost + total_variable_cost


calculate_profit = finance_profit


def demand_score(customers):
    if customers >= DEMAND_HIGH:
        return 100
    elif customers >= DEMAND_MEDIUM:
        return 80
    elif customers >= DEMAND_LOW:
        return 60
    else:
        return 40


def market_structure_score(market_structure):
    scores = {
        "Perfect Competition": 60,
        "Monopolistic Competition": 70,
        "Oligopoly": 80,
        "Monopoly": 100,
    }

    return scores.get(market_structure, 50)


def profit_score(profit):
    if profit >= PROFIT_HIGH:
        return 100
    elif profit >= PROFIT_MEDIUM:
        return 80
    elif profit >= PROFIT_LOW:
        return 60
    else:
        return 40


def economic_score(demand, market, profit):
    return (demand + market + profit) / 3


payback_period = finance_payback_period


def npv_score(npv):
    if npv > NPV_POSITIVE:
        return 100

    return 30


def payback_score(payback):
    if payback is None:
        return 0

    if payback <= PAYBACK_EXCELLENT:
        return 100
    elif payback <= PAYBACK_GOOD:
        return 80
    elif payback <= PAYBACK_MODERATE:
        return 60
    else:
        return 40


def investment_score(npv_score_value, payback_score_value):
    return (npv_score_value + payback_score_value) / 2


debt_ratio = finance_debt_ratio

equity_ratio = finance_equity_ratio


def financing_score(debt_ratio_value):
    if debt_ratio_value < DEBT_RATIO_STRONG:
        return 100
    elif debt_ratio_value <= DEBT_RATIO_CAUTION:
        return 80
    else:
        return 50


def current_ratio(current_assets, current_liabilities):
    if current_liabilities == 0:
        return 0

    return current_assets / current_liabilities


def quick_ratio(current_assets, inventory, current_liabilities):
    if current_liabilities == 0:
        return 0

    return (current_assets - inventory) / current_liabilities


def current_ratio_score(value):
    if value >= CURRENT_RATIO_STRONG:
        return 100
    elif value >= CURRENT_RATIO_GOOD:
        return 80
    elif value >= CURRENT_RATIO_MINIMUM:
        return 60
    else:
        return 30


def quick_ratio_score(value):
    if value >= QUICK_RATIO_STRONG:
        return 100
    elif value >= QUICK_RATIO_GOOD:
        return 80
    elif value >= QUICK_RATIO_MINIMUM:
        return 60
    else:
        return 30


def risk_score(current_score, quick_score, debt_score):
    return (current_score + quick_score + debt_score) / 3


def overall_decision_score(
    economic_score,
    investment_score,
    financing_score,
    risk_score,
):
    return (
        economic_score
        + investment_score
        + financing_score
        + risk_score
    ) / 4


def recommendation(score):
    if score >= DECISION_PROCEED:
        return "Proceed"
    elif score >= DECISION_CAUTION:
        return "Proceed with Caution"
    elif score >= DECISION_ANALYSIS:
        return "Needs Further Analysis"
    else:
        return "Do Not Proceed"


def executive_summary(
    business_name,
    industry,
    profit,
    economic_score,
    investment_score,
    financing_score,
    risk_score,
    decision_score,
    recommendation,
):
    return f"""
Business: {business_name}

Industry: {industry}

Expected Profit: {format_currency(profit)}

Economic Score: {economic_score:.0f}/100
Investment Score: {investment_score:.0f}/100
Financing Score: {financing_score:.0f}/100
Risk Score: {risk_score:.0f}/100

Decision Score: {decision_score:.0f}/100

Recommendation:
{recommendation}
"""


def recommendation_explanation(recommendation):
    explanations = {
        "Proceed": (
            "The project shows strong economic, financial, and risk characteristics."
        ),
        "Proceed with Caution": (
            "The project appears viable but some metrics should be monitored carefully."
        ),
        "Needs Further Analysis": (
            "Additional investigation is recommended before committing resources."
        ),
        "Do Not Proceed": (
            "The project currently presents insufficient economic or financial attractiveness."
        ),
    }

    return explanations.get(recommendation, "")