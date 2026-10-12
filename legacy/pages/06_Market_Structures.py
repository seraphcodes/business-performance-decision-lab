import streamlit as st

from modules.economics.market_structures import classify_market

st.title("Market Structures")
st.caption("Session 6")

market_type = st.selectbox(
    "Choose a market structure",
    ["Perfect Competition", "Monopolistic Competition", "Oligopoly", "Monopoly"],
)

st.info(classify_market(market_type))
