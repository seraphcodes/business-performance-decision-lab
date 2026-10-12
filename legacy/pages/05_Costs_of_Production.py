import streamlit as st

from modules.economics.costs import (
    average_fixed_cost,
    average_total_cost,
    average_variable_cost,
    marginal_cost,
    total_cost,
)
from utils.formatting import format_currency

st.title("The Costs of Production")
st.caption("Session 5")

col1, col2, col3 = st.columns(3)
fixed_cost = col1.number_input("Fixed cost", min_value=0.0, value=100.0)
variable_cost = col2.number_input("Variable cost", min_value=0.0, value=20.0)
quantity = col3.number_input("Quantity", min_value=0.0, value=10.0)

col4, col5 = st.columns(2)
change_in_cost = col4.number_input("Change in cost", min_value=0.0, value=50.0)
change_in_quantity = col5.number_input("Change in quantity", min_value=0.0, value=5.0)

total_cost_value = total_cost(fixed_cost, variable_cost)
afc = average_fixed_cost(fixed_cost, quantity) if quantity > 0 else 0.0
avc = average_variable_cost(variable_cost, quantity) if quantity > 0 else 0.0
atc = average_total_cost(total_cost_value, quantity) if quantity > 0 else 0.0
mc = marginal_cost(change_in_cost, change_in_quantity) if change_in_quantity > 0 else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total cost", format_currency(total_cost_value))
c2.metric("AFC", format_currency(afc))
c3.metric("AVC", format_currency(avc))
c4.metric("ATC", format_currency(atc))
c5.metric("Marginal cost", format_currency(mc))

with st.expander("How this is calculated"):
    st.markdown(
        "- Total cost = fixed cost + variable cost\n"
        "- AFC / AVC / ATC = fixed / variable / total cost divided by quantity\n"
        "- Marginal cost = change in cost ÷ change in quantity"
    )
