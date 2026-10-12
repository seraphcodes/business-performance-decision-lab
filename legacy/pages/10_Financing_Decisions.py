import streamlit as st

from modules.finance.financing_decisions import financing_mix
from utils.formatting import format_percent

st.title("Financing Decisions")
st.caption("Chapter 4")

col1, col2 = st.columns(2)
debt_amount = col1.number_input("Debt amount", min_value=0.0, value=400000.0)
equity_amount = col2.number_input("Equity amount", min_value=0.0, value=600000.0)

mix = financing_mix(debt_amount, equity_amount)

col3, col4 = st.columns(2)
col3.metric("Debt ratio", format_percent(mix["debt_ratio"]))
col4.metric("Equity ratio", format_percent(mix["equity_ratio"]))

with st.expander("How this is calculated"):
    st.markdown(
        "- Debt ratio = debt ÷ (debt + equity)\n"
        "- Equity ratio = equity ÷ (debt + equity)"
    )
