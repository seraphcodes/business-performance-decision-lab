import streamlit as st

from modules.economics.taxation import tax_revenue, deadweight_loss
from utils.formatting import format_currency

st.title("Application: The Costs of Taxation")
st.caption("Session 4")

col1, col2, col3 = st.columns(3)
tax_per_unit = col1.number_input("Tax per unit", min_value=0.0, value=10.0)
quantity_before_tax = col2.number_input("Quantity before tax", min_value=0.0, value=100.0)
quantity_after_tax = col3.number_input("Quantity after tax", min_value=0.0, value=80.0)

quantity_reduction = max(quantity_before_tax - quantity_after_tax, 0.0)
tax_revenue_value = tax_revenue(tax_per_unit, quantity_after_tax)
dwl = deadweight_loss(tax_per_unit, quantity_reduction)

col4, col5 = st.columns(2)
col4.metric("Tax revenue", format_currency(tax_revenue_value))
col5.metric("Deadweight loss", format_currency(dwl))

with st.expander("How this is calculated"):
    st.markdown(
        "- Tax revenue = tax per unit × quantity sold after the tax\n"
        "- Deadweight loss = ½ × tax per unit × reduction in quantity traded"
    )
