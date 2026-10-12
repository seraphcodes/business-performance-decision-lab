"""Centralized thresholds for the decision engine.

These values preserve the existing scoring behavior while allowing future
adjustments from a single configuration source.
"""

# Demand thresholds
DEMAND_HIGH = 5000
DEMAND_MEDIUM = 2000
DEMAND_LOW = 1000

# Profit thresholds
PROFIT_HIGH = 50000
PROFIT_MEDIUM = 20000
PROFIT_LOW = 10000

# Investment thresholds
NPV_POSITIVE = 0
PAYBACK_EXCELLENT = 3
PAYBACK_GOOD = 5
PAYBACK_MODERATE = 8

# Financing thresholds
DEBT_RATIO_STRONG = 40
DEBT_RATIO_CAUTION = 70

# Liquidity thresholds
CURRENT_RATIO_STRONG = 2.0
CURRENT_RATIO_GOOD = 1.5
CURRENT_RATIO_MINIMUM = 1.0
QUICK_RATIO_STRONG = 1.0
QUICK_RATIO_GOOD = 0.8
QUICK_RATIO_MINIMUM = 0.5

# Recommendation thresholds
DECISION_PROCEED = 85
DECISION_CAUTION = 70
DECISION_ANALYSIS = 50

# Economic score thresholds
ECONOMIC_SCORE_EXCELLENT = 85
ECONOMIC_SCORE_STRONG = 70
ECONOMIC_SCORE_AVERAGE = 50

# Investment opportunity thresholds
INVESTMENT_STRONG = 80
INVESTMENT_MODERATE = 60

# Risk profile thresholds
RISK_LOW = 85
RISK_MODERATE = 70
RISK_ELEVATED = 50

# Financing posture thresholds
FINANCING_CONSERVATIVE = 40
FINANCING_BALANCED = 70
