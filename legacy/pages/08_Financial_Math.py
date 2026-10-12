import streamlit as st

from modules.finance.financial_math import future_value, present_value
from utils.formatting import format_currency

st.title("Financial Mathematics Fundamentals")
st.caption("Chapter 2")

col1, col2 = st.columns(2)
present_value_input = col1.number_input("Present value", min_value=0.0, value=1000.0)
future_value_input = col2.number_input("Future value", min_value=0.0, value=2000.0)

col3, col4 = st.columns(2)
interest_rate = col3.number_input("Interest rate", min_value=0.0, value=0.08)
years = col4.number_input("Years", min_value=0.0, value=5.0)

fv_result = future_value(present_value_input, interest_rate, years)
pv_result = present_value(future_value_input, interest_rate, years)
compound_interest_earned = fv_result - present_value_input

col5, col6, col7 = st.columns(3)
col5.metric("Future value", format_currency(fv_result))
col6.metric("Present value", format_currency(pv_result))
col7.metric("Compound interest earned", format_currency(compound_interest_earned))

with st.expander("How this is calculated"):
    st.markdown(
        "- Future value = present value × (1 + rate) ^ years\n"
        "- Present value = future value ÷ (1 + rate) ^ years"
    )
