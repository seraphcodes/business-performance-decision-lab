import streamlit as st

from modules.decision_engine import (
    calculate_profit,
    calculate_revenue,
    calculate_total_cost,
    calculate_variable_cost,
    current_ratio,
    current_ratio_score,
    debt_ratio,
    demand_score,
    economic_score,
    equity_ratio,
    executive_summary,
    financing_score,
    investment_score,
    market_structure_score,
    npv_score,
    payback_period,
    payback_score,
    profit_score,
    quick_ratio,
    quick_ratio_score,
    recommendation_explanation,
    risk_score,
    overall_decision_score,
    recommendation,
)
from modules.finance.investment_decisions import net_present_value
from utils.decision_config import (
    ECONOMIC_SCORE_AVERAGE,
    ECONOMIC_SCORE_EXCELLENT,
    ECONOMIC_SCORE_STRONG,
    FINANCING_BALANCED,
    FINANCING_CONSERVATIVE,
    INVESTMENT_MODERATE,
    INVESTMENT_STRONG,
    RISK_ELEVATED,
    RISK_LOW,
    RISK_MODERATE,
)
from utils.formatting import format_currency, format_percent

st.title("Decision Engine")
st.header("Business Scenario Builder")

business_name = st.text_input("Business Name")
industry = st.text_input("Industry")
market_structure = st.selectbox(
    "Market Structure",
    [
        "Perfect Competition",
        "Monopolistic Competition",
        "Oligopoly",
        "Monopoly",
    ],
)

customers = st.number_input(
    "Expected Customers",
    min_value=0,
    value=500,
)

selling_price = st.number_input(
    "Selling Price",
    min_value=0.0,
    value=20.0,
)

variable_cost = st.number_input(
    "Variable Cost Per Unit",
    min_value=0.0,
    value=8.0,
)

fixed_cost = st.number_input(
    "Fixed Cost",
    min_value=0.0,
    value=5000.0,
)

revenue = calculate_revenue(customers, selling_price)
total_variable_cost = calculate_variable_cost(customers, variable_cost)
total_cost = calculate_total_cost(fixed_cost, total_variable_cost)
profit = calculate_profit(revenue, total_cost)

d_score = demand_score(customers)
m_score = market_structure_score(market_structure)
p_score = profit_score(profit)
econ_score = economic_score(d_score, m_score, p_score)

st.subheader("Scenario Results")

st.metric("Revenue", format_currency(revenue))
st.metric("Total Cost", format_currency(total_cost))
st.metric("Expected Profit", format_currency(profit))

st.header("Economic Analysis")
st.metric("Economic Score", f"{econ_score:.0f}/100")

if econ_score >= ECONOMIC_SCORE_EXCELLENT:
    st.success("Excellent Economic Potential")
elif econ_score >= ECONOMIC_SCORE_STRONG:
    st.success("Strong Economic Potential")
elif econ_score >= ECONOMIC_SCORE_AVERAGE:
    st.warning("Average Economic Potential")
else:
    st.error("Weak Economic Potential")

st.header("Investment Analysis")

investment_required = st.number_input(
    "Investment Required",
    min_value=0.0,
    value=50000.0,
)

project_years = st.number_input(
    "Project Lifetime",
    min_value=1,
    value=5,
)

discount_rate = st.number_input(
    "Discount Rate (%)",
    min_value=0.0,
    value=8.0,
)

cash_flows = [profit] * project_years
npv = net_present_value(investment_required, cash_flows, discount_rate / 100)
payback = payback_period(investment_required, profit)

npv_score_value = npv_score(npv)
payback_score_value = payback_score(payback)
inv_score = investment_score(npv_score_value, payback_score_value)

st.metric("NPV", format_currency(npv))

if payback is None:
    st.metric("Payback Period", "N/A")
else:
    st.metric("Payback Period", f"{payback:.2f} Years")

st.metric("Investment Score", f"{inv_score:.0f}/100")

if inv_score >= INVESTMENT_STRONG:
    st.success("Strong Investment Opportunity")
elif inv_score >= INVESTMENT_MODERATE:
    st.warning("Moderate Investment Opportunity")
else:
    st.error("Weak Investment Opportunity")

st.header("Financing Analysis")

debt_amount = st.number_input(
    "Debt Financing",
    min_value=0.0,
    value=60000.0,
)

equity_amount = st.number_input(
    "Equity Financing",
    min_value=0.0,
    value=40000.0,
)

debt_ratio_value = debt_ratio(debt_amount, equity_amount)
equity_ratio_value = equity_ratio(debt_amount, equity_amount)
fin_score = financing_score(debt_ratio_value)

st.metric("Debt Ratio", format_percent(debt_ratio_value))
st.metric("Equity Ratio", format_percent(equity_ratio_value))
st.metric("Financing Score", f"{fin_score:.0f}/100")

if debt_ratio_value < FINANCING_CONSERVATIVE:
    st.success("Conservative Financing")
elif debt_ratio_value <= FINANCING_BALANCED:
    st.info("Balanced Financing")
else:
    st.warning("Aggressive Financing")

st.header("Risk Analysis")

current_assets = st.number_input(
    "Current Assets",
    min_value=0.0,
    value=20000.0,
)

inventory = st.number_input(
    "Inventory",
    min_value=0.0,
    value=5000.0,
)

current_liabilities = st.number_input(
    "Current Liabilities",
    min_value=0.0,
    value=10000.0,
)

current_ratio_value = current_ratio(current_assets, current_liabilities)
quick_ratio_value = quick_ratio(
    current_assets,
    inventory,
    current_liabilities,
)
debt_score = fin_score

current_score = current_ratio_score(current_ratio_value)
quick_score = quick_ratio_score(quick_ratio_value)
overall_risk_score = risk_score(current_score, quick_score, debt_score)

st.metric("Current Ratio", f"{current_ratio_value:.2f}")
st.metric("Quick Ratio", f"{quick_ratio_value:.2f}")
st.metric("Risk Score", f"{overall_risk_score:.0f}/100")

if overall_risk_score >= RISK_LOW:
    st.success("Low Risk Profile")
elif overall_risk_score >= RISK_MODERATE:
    st.info("Moderate Risk Profile")
elif overall_risk_score >= RISK_ELEVATED:
    st.warning("Elevated Risk Profile")
else:
    st.error("High Risk Profile")

st.header("Decision Logic")

decision_score = overall_decision_score(
    econ_score,
    inv_score,
    fin_score,
    overall_risk_score,
)
decision_recommendation = recommendation(decision_score)

st.metric("Decision Score", f"{decision_score:.0f}/100")

if decision_recommendation == "Proceed":
    st.success("✅ Proceed")
elif decision_recommendation == "Proceed with Caution":
    st.warning("⚠️ Proceed with Caution")
elif decision_recommendation == "Needs Further Analysis":
    st.info("🔍 Needs Further Analysis")
else:
    st.error("❌ Do Not Proceed")

st.info(recommendation_explanation(decision_recommendation))

st.subheader("Decision Components")
st.write(f"Economic Score: {econ_score:.0f}")
st.write(f"Investment Score: {inv_score:.0f}")
st.write(f"Financing Score: {fin_score:.0f}")
st.write(f"Risk Score: {overall_risk_score:.0f}")

st.header("Executive Summary")

summary = executive_summary(
    business_name,
    industry,
    profit,
    econ_score,
    inv_score,
    fin_score,
    overall_risk_score,
    decision_score,
    decision_recommendation,
)

st.text_area(
    "Business Report",
    summary,
    height=350,
)

st.download_button(
    "Download Summary",
    summary,
    file_name="decision_report.txt",
)

if business_name or industry:
    st.caption(f"Scenario for: {business_name or 'Unnamed Business'} in {industry or 'the selected industry'}")

