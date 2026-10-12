import streamlit as st

from modules.economics.trade import opportunity_cost, compare_advantage

st.title("Interdependence and Gains from Trade")
st.caption("Session 1")

st.write("Enter how much of each good two producers can make, to find who has the comparative advantage in Product 1.")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Producer A**")
    a_good1 = st.number_input("Producer A - Product 1", min_value=0.0, value=10.0, key="a1")
    a_good2 = st.number_input("Producer A - Product 2", min_value=0.0, value=5.0, key="a2")
with col2:
    st.markdown("**Producer B**")
    b_good1 = st.number_input("Producer B - Product 1", min_value=0.0, value=6.0, key="b1")
    b_good2 = st.number_input("Producer B - Product 2", min_value=0.0, value=12.0, key="b2")

if a_good1 > 0 and a_good2 > 0 and b_good1 > 0 and b_good2 > 0:
    a_oc = opportunity_cost(a_good1, a_good2)
    b_oc = opportunity_cost(b_good1, b_good2)

    col3, col4 = st.columns(2)
    col3.metric("Producer A opportunity cost", f"{a_oc:.2f}")
    col4.metric("Producer B opportunity cost", f"{b_oc:.2f}")

    st.subheader("Comparative advantage")
    winner = compare_advantage(a_oc, b_oc)
    if winner == "A":
        st.success("Producer A has a comparative advantage in Product 1.")
    elif winner == "B":
        st.success("Producer B has a comparative advantage in Product 1.")
    else:
        st.info("Both producers have the same opportunity cost.")

    with st.expander("How this is calculated"):
        st.markdown(
            "Opportunity cost of Product 1 = units of Product 2 given up ÷ units of Product 1 produced. "
            "The producer with the **lower** opportunity cost for a good has the comparative advantage in it."
        )
else:
    st.warning("Enter positive values for all four fields to see the comparison.")
