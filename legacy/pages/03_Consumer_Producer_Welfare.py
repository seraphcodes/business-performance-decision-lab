import streamlit as st

from modules.economics.welfare import consumer_surplus, producer_surplus, total_welfare
from utils.formatting import format_currency

st.title("Consumers & Producers")
st.caption("Session 3 — Market Welfare Analyzer")

col1, col2, col3 = st.columns(3)
willingness_to_pay = col1.number_input("Willingness to pay", value=100.0)
market_price = col2.number_input("Market price", value=80.0)
production_cost = col3.number_input("Production cost", value=50.0)

cs = consumer_surplus(willingness_to_pay, market_price)
ps = producer_surplus(market_price, production_cost)
tw = total_welfare(cs, ps)

col4, col5, col6 = st.columns(3)
col4.metric("Consumer surplus", format_currency(cs))
col5.metric("Producer surplus", format_currency(ps))
col6.metric("Total welfare", format_currency(tw))

with st.expander("How this is calculated"):
    st.markdown(
        "- Consumer surplus = willingness to pay − market price\n"
        "- Producer surplus = market price − production cost\n"
        "- Total welfare = consumer surplus + producer surplus"
    )
