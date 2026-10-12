import streamlit as st

st.set_page_config(
    page_title="Business Performance & Decision Lab",
    page_icon="📊",
    layout="wide",
)

st.title("Business Performance & Decision Lab")
st.caption("Working title. A business-intelligence dashboard with a what-if decision simulator.")

st.markdown(
    """
Explore two years of real retail transactions, then test how a price or
volume change could affect profit.

- **Overview**: revenue trends, top products, countries, cancellations.
- **What-If Simulator**: compare today's baseline with a scenario. The data has
  no product costs, so any profit figure uses a cost you enter and is labelled
  as an assumption.
- **Methodology**: how the data was cleaned, the formulas used, and the limits
  of what this data can tell us.

Use the sidebar to switch pages.
"""
)

st.info("Dataset: Online Retail II, UCI Machine Learning Repository, CC BY 4.0.")
