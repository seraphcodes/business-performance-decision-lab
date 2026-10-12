import numpy as np
import plotly.graph_objects as go
import streamlit as st

from modules.economics.supply_demand import find_equilibrium
from utils.formatting import format_currency

st.title("The Market Forces of Supply and Demand")
st.caption("Session 2")

col1, col2 = st.columns(2)
demand_shift = col1.slider("Demand shift", -20, 20, 0)
supply_shift = col2.slider("Supply shift", -20, 20, 0)

eq_price, eq_quantity = find_equilibrium(demand_shift=demand_shift, supply_shift=supply_shift)

if eq_price is not None:
    col3, col4 = st.columns(2)
    col3.metric("Equilibrium price", format_currency(eq_price))
    col4.metric("Equilibrium quantity", f"{eq_quantity:.2f}")

    prices = np.arange(0, 101, 1)
    demand_values = [100 - p + demand_shift for p in prices]
    supply_values = [p + supply_shift for p in prices]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=demand_values, mode="lines", name="Demand", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=prices, y=supply_values, mode="lines", name="Supply", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=[eq_quantity], y=[eq_price], mode="markers", name="Equilibrium", marker=dict(color="red", size=12)))
    fig.update_layout(title="Supply and Demand", xaxis_title="Quantity", yaxis_title="Price", template="plotly_white")
    st.plotly_chart(fig, width="stretch")
else:
    st.warning("No equilibrium was found for the current shifts.")

with st.expander("How this is calculated"):
    st.markdown(
        "Demand and supply shifts move the respective curve left/right. "
        "Equilibrium is the price where quantity demanded equals quantity supplied."
    )
