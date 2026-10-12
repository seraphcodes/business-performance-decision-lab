import streamlit as st

from modules.finance.capital_structure import wacc, retention_ratio
from utils.formatting import format_percent

st.title("Capital Structure & Distribution")
st.caption("Chapter 5")

col1, col2 = st.columns(2)
debt = col1.number_input("Debt", min_value=0.0, value=400000.0)
equity = col2.number_input("Equity", min_value=0.0, value=600000.0)

col3, col4 = st.columns(2)
cost_of_debt = col3.number_input("Cost of debt (%)", min_value=0.0, value=6.0)
retained_earnings = col4.number_input("Retained earnings", min_value=0.0, value=200000.0)

net_income = st.number_input("Net income", min_value=0.0, value=500000.0)

cost_of_debt_rate = cost_of_debt / 100.0 if cost_of_debt > 1 else cost_of_debt
wacc_value = wacc(debt, equity, cost_of_debt_rate)
retention_ratio_value = retention_ratio(retained_earnings, net_income)

col5, col6 = st.columns(2)
col5.metric("WACC", format_percent(wacc_value * 100))
col6.metric("Retention ratio", f"{retention_ratio_value:.2f}")

with st.expander("How this is calculated"):
    st.markdown(
        "- WACC = (debt weight × cost of debt) + (equity weight × cost of equity)\n"
        "- Retention ratio = retained earnings ÷ net income"
    )
