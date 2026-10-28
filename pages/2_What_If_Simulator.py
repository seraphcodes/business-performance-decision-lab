"""What-If Simulator: a narrow, assumption-labelled scenario calculator.

Not a forecast. The baseline is the last 12 full months of real data; the price
change, volume change and cost share are inputs the user chooses. See src/scenario.py.
"""
import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import metrics  # noqa: E402
from src.config import DATABASE  # noqa: E402
from src.scenario import baseline, breakeven_volume_pct, scenario, sensitivity  # noqa: E402
from utils.formatting import format_currency  # noqa: E402

DB = os.environ.get("RETAIL_DB", str(DATABASE))

st.set_page_config(page_title="What-If Simulator", page_icon="🧮", layout="wide")
st.title("What-If Simulator")
st.warning(
    "**This is arithmetic, not a forecast.** The baseline is real (last 12 full months). "
    "Price change, volume change and cost are **your assumptions**. The data has no product costs, "
    "so every profit figure depends entirely on the cost share you enter. "
    "The page does not predict how customers would react to a price change."
)

if not Path(DB).is_file():
    st.error("The database is missing. Run `python -m src.build_db` in the project folder first.")
    st.stop()


@st.cache_data(show_spinner=False)
def load_baseline(db):
    return baseline(metrics.monthly_revenue(db, include_partial=False), months=12)


base = load_baseline(DB)
st.caption(f"Baseline: {base['first_month']} to {base['last_month']} ({base['months']} full months). "
           f"Net product revenue {format_currency(base['net'])}; "
           f"cancellation rate {base['cancellation_rate'] * 100:.2f}% of gross, held constant.")

with st.sidebar:
    st.header("Your assumptions")
    price = st.slider("Price change (%)", -30, 30, 5, 1)
    volume = st.slider("Volume change (%)", -50, 50, 0, 1)
    cost_share = st.slider("Product cost as % of net revenue (ASSUMPTION)", 10, 90, 60, 5,
                           help="Not in the data. Try several values: the profit result moves a lot.")

result = scenario(base, price, volume, cost_share)

columns = st.columns(4)
columns[0].metric("Net revenue, scenario", format_currency(result["net"]))
columns[1].metric("Change in net revenue", format_currency(result["net_change"]))
columns[2].metric("Profit, scenario (assumed cost)", format_currency(result["profit"]))
columns[3].metric("Change in profit (assumed cost)", format_currency(result["profit_change"]))
st.caption(f"Baseline profit under the same cost assumption: {format_currency(result['base_profit'])}. "
           "Revenue figures follow from the data; profit figures follow from the cost share you chose.")

st.subheader("Break-even volume")
even = breakeven_volume_pct(price, cost_share)
if price == 0:
    st.write("Price is unchanged, so profit changes only if volume changes.")
elif even is None:
    st.write(f"With a {price}% price change and a {cost_share}% cost share the unit margin is zero or "
             "negative, so no volume increase can bring profit back to the baseline.")
else:
    direction = "can fall by up to" if even < 0 else "must rise by at least"
    st.write(f"With a **{price:+d}%** price change and a **{cost_share}%** cost share, profit stays at the "
             f"baseline if volume {direction} **{abs(even):.1f}%**.")

st.subheader("Sensitivity: change in profit (assumed cost)")
prices = list(range(-20, 25, 5))
volumes = list(range(-30, 35, 5))
grid = sensitivity(base, prices, volumes, cost_share)
limit = float(abs(grid.values).max()) or 1.0
heat = go.Figure(go.Heatmap(
    z=grid.values, x=[f"{v:+d}%" for v in volumes], y=[f"{p:+d}%" for p in prices],
    zmin=-limit, zmax=limit, colorscale="RdBu", colorbar=dict(title="£"),
    hovertemplate="Price %{y}, volume %{x}<br>£%{z:,.0f}<extra></extra>"))
heat.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0),
                   xaxis_title="Volume change", yaxis_title="Price change")
st.plotly_chart(heat, use_container_width=True)
st.caption("Blue = profit above baseline, red = below. Price and volume are varied independently: "
           "in reality a price rise usually lowers volume, which this page deliberately does not guess.")

with st.expander("How the numbers are calculated"):
    st.markdown("""
- **Gross sales** = baseline gross x (1 + price change) x (1 + volume change).
- **Net revenue** = gross x (1 - baseline cancellation rate).
- **Cost** = cost share x baseline net revenue x (1 + volume change). Unit cost is assumed unchanged.
- **Profit** = net revenue - cost.
- **Break-even volume** = (1 - cost share) / (1 + price change - cost share) - 1.
""")
