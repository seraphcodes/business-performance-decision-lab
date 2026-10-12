import streamlit as st

st.set_page_config(
    page_title="Economics & Finance Decision Engine",
    page_icon="📊",
    layout="wide",
)

st.title("Economics & Finance Decision Engine")
st.caption("A portfolio project reviewing economics and finance through interactive calculators.")

st.markdown(
    """
Use the sidebar to open any module. Each page is self-contained and
covers one topic from the roadmap below.
"""
)

st.subheader("Roadmap")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Economics Engine** ✅")
    st.markdown(
        "- Interdependence & gains from trade\n"
        "- Supply and demand\n"
        "- Consumer & producer welfare\n"
        "- Taxation\n"
        "- Costs of production\n"
        "- Market structures"
    )

with col2:
    st.markdown("**Finance Engine** ✅")
    st.markdown(
        "- Introduction to finance\n"
        "- Financial mathematics\n"
        "- Investment decisions\n"
        "- Financing decisions\n"
        "- Capital structure"
    )

st.markdown("---")

col3, col4 = st.columns(2)
with col3:
    st.markdown("**Decision Engine** 🚧")
    st.caption("Connects economics output (e.g. market-structure profit) to finance input (e.g. NPV cash flows) as one walkthrough.")
with col4:
    st.markdown("**AI Decision Assistant** 🚧")
    st.caption("Plain-language explanation of what a result means and what to consider next.")

col5, col6 = st.columns(2)
with col5:
    st.markdown("**Interactive Graph** 🚧")
    st.caption("Shared, reusable chart component across modules.")
with col6:
    st.markdown("**Startup Prototype** 🚧")
    st.caption("Polished landing experience once the above pieces are connected.")
