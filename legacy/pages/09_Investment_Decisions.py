import streamlit as st

from modules.finance.investment_decisions import net_present_value, payback_period
from utils.formatting import format_currency

st.title("Investment Decision Making")
st.caption("Chapter 3 — Investment Decision Engine")

initial_investment = st.number_input("Initial investment", min_value=0.0, value=1000.0)

col1, col2, col3 = st.columns(3)
year1 = col1.number_input("Year 1 cash flow", min_value=0.0, value=400.0)
year2 = col2.number_input("Year 2 cash flow", min_value=0.0, value=500.0)
year3 = col3.number_input("Year 3 cash flow", min_value=0.0, value=600.0)

discount_rate = st.number_input("Discount rate", min_value=0.0, value=0.10)

cash_flows = [year1, year2, year3]
npv_value = net_present_value(initial_investment, cash_flows, discount_rate)
payback_value = payback_period(initial_investment, sum(cash_flows) / len(cash_flows))

col4, col5 = st.columns(2)
col4.metric("NPV", format_currency(npv_value))
col5.metric("Payback period", f"{payback_value:.2f} years")

if npv_value > 0:
    st.success("Investment creates value.")
else:
    st.error("Investment destroys value.")

with st.expander("How this is calculated"):
    st.markdown(
        "- NPV = sum of each year's cash flow discounted back to today, minus the initial investment\n"
        "- Payback period = initial investment ÷ average annual cash flow"
    )
