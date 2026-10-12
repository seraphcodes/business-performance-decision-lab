import streamlit as st

from modules.finance.finance_intro import profit, profit_margin, return_on_investment
from utils.formatting import format_currency, format_percent

st.title("Introduction to Finance")
st.caption("Chapter 1 — Business Finance Dashboard")

col1, col2, col3 = st.columns(3)
revenue = col1.number_input("Revenue", min_value=0.0, value=1000.0)
costs = col2.number_input("Costs", min_value=0.0, value=600.0)
investment = col3.number_input("Investment", min_value=0.0, value=500.0)

profit_value = profit(revenue, costs)
margin_value = profit_margin(revenue, costs)
roi_value = return_on_investment(profit_value, investment)

col4, col5, col6 = st.columns(3)
col4.metric("Profit", format_currency(profit_value))
col5.metric("Profit margin", format_percent(margin_value))
col6.metric("ROI", format_percent(roi_value))

with st.expander("How this is calculated"):
    st.markdown(
        "- Profit = revenue − costs\n"
        "- Profit margin = profit ÷ revenue\n"
        "- ROI = profit ÷ investment"
    )
