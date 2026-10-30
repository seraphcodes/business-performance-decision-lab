"""Overview: revenue trend, cancellations, top products, countries.

Every number comes from the SQL views (see docs/metrics.md) through src/metrics.py.
This page only displays them; it recomputes nothing.
"""
import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import metrics  # noqa: E402
from src.config import DATABASE  # noqa: E402
from utils.formatting import format_currency, format_percent  # noqa: E402

DB = os.environ.get("RETAIL_DB", str(DATABASE))
BLUE, GREY, RED = "#2a6fdb", "#8a94a6", "#c0392b"

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("Overview")
st.caption("Online Retail II, Dec 2009 - 9 Dec 2011. Revenue, not profit: the data has no product costs.")

if not Path(DB).is_file():
    st.error("The database is missing. Run `python -m src.build_db` in the project folder first.")
    st.stop()


@st.cache_data(show_spinner=False)
def load(db):
    return {
        "kpis": metrics.headline_kpis(db),
        "monthly": metrics.monthly_revenue(db, include_partial=True),
        "products": metrics.top_products(db, n=10),
        "countries": metrics.country_revenue(db),
        "services": metrics.monthly_service_lines(db),
    }


data = load(DB)
kpis, monthly = data["kpis"], data["monthly"]

with st.sidebar:
    st.header("View options")
    show_partial = st.toggle("Include the incomplete last month (Dec 2011, 9 days)", value=False)
    exclude_uk = st.toggle("Countries: hide the United Kingdom", value=False)

# ------------------------------------------------------------------ KPIs
columns = st.columns(5)
columns[0].metric("Net product revenue", format_currency(kpis["net_product_revenue"]),
                  help="Gross product sales plus cancellations (credit notes count as negative). "
                       "Postage, fees and stock adjustments are not included.")
columns[1].metric("Gross product sales", format_currency(kpis["gross_product_sales"]),
                  help="Quantity x unit price of normal sales lines. It still includes orders that were cancelled later.")
columns[2].metric(f"Cancellations ({format_percent(kpis['cancellation_rate_pct'])} of gross)",
                  format_currency(kpis["cancellation_value"]),
                  help="Value of credit-note lines (negative). The % is cancellations divided by gross sales; "
                       "credit notes cannot be linked to the original sale.")
columns[3].metric("Orders (invoices)", f"{kpis['sales_invoices']:,}",
                  help="Invoices with at least one normal sales line. Credit notes are not counted.")
columns[4].metric("Average order value (gross)", format_currency(kpis["avg_order_value"]),
                  help="Gross product sales divided by the number of invoices. Because gross sales include orders "
                       "cancelled later, a net-based average would be lower.")
st.caption(
    f"Whole period, {kpis['known_customers']:,} identified customers. "
    f"Only {kpis['known_customer_share_pct']:.0f}% of sales value has a customer ID, so customer "
    "analysis covers that share. Postage, fees and stock adjustments are excluded from product revenue."
)

# --------------------------------------------------------- monthly trend
shown = monthly if show_partial else monthly[monthly["is_partial_month"] == 0]
st.subheader("Net product revenue by month")
bar_colors = [GREY if partial else BLUE for partial in shown["is_partial_month"]]
trend = go.Figure(go.Bar(
    x=shown["year_month"], y=shown["net_product_revenue"], marker_color=bar_colors,
    hovertemplate="%{x}<br>£%{y:,.0f}<extra></extra>"))
trend.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="£ per month",
                    yaxis_tickprefix="£", yaxis_tickformat=",.0f",
                    xaxis=dict(type="category"))
st.plotly_chart(trend, use_container_width=True)
st.caption("November is the peak in both years. Grey = incomplete month. "
           "December 2009 and 2010 end on the 23rd (holiday closure), so they are lower than a full December.")

# ---------------------------------------------------------- cancellations
st.subheader("Cancellation rate by month")
rate = go.Figure(go.Scatter(
    x=shown["year_month"], y=shown["cancellation_rate_pct"], mode="lines+markers",
    line=dict(color=RED), hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"))
rate.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="% of gross sales",
                   yaxis_ticksuffix="%", xaxis=dict(type="category"))
st.plotly_chart(rate, use_container_width=True)
st.caption(
    "Credit notes cannot be matched to the original sale, so the rate compares cancellations with "
    "sales in the same month. Spikes such as Jan 2011 (13.6%) come from a few very large orders "
    "that were cancelled; see Methodology."
)

# -------------------------------------------------------- products, countries
left, right = st.columns(2)
with left:
    st.subheader("Top 10 products by net sales")
    products = data["products"].iloc[::-1]
    labels = [f"{code}  {str(desc)[:28]}" for code, desc in zip(products["stock_code"], products["description"])]
    figure = go.Figure(go.Bar(x=products["net_sales"], y=labels, orientation="h", marker_color=BLUE,
                              hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"))
    figure.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), xaxis_tickprefix="£",
                         xaxis_tickformat=",.0f")
    st.plotly_chart(figure, use_container_width=True)
    st.caption("Net = sales minus cancellations, grouped by stock code. Whole period (Dec 2009 - 9 Dec 2011).")
with right:
    st.subheader("Top 10 countries by net revenue")
    countries = data["countries"]
    if exclude_uk:
        countries = countries[countries["country"] != "United Kingdom"]
    countries = countries.sort_values("net_product_revenue", ascending=False).head(10).iloc[::-1]
    figure = go.Figure(go.Bar(x=countries["net_product_revenue"], y=countries["country"], orientation="h",
                              marker_color=BLUE, hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"))
    figure.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), xaxis_tickprefix="£",
                         xaxis_tickformat=",.0f")
    st.plotly_chart(figure, use_container_width=True)
    uk_share = (data["countries"].set_index("country").loc["United Kingdom", "net_product_revenue"]
                / kpis["net_product_revenue"] * 100)
    st.caption(f"Whole period. The United Kingdom is {uk_share:.0f}% of net revenue; hide it to compare the rest.")

with st.expander("Table: monthly figures"):
    table = shown.rename(columns={
        "year_month": "Month", "gross_product_sales": "Gross", "cancellation_value": "Cancellations",
        "net_product_revenue": "Net", "sales_invoices": "Orders", "known_customers": "Customers",
        "cancellation_rate_pct": "Cancel %", "avg_order_value": "Avg order"})
    st.dataframe(table[["Month", "Gross", "Cancellations", "Net", "Orders", "Customers", "Cancel %", "Avg order"]],
                 hide_index=True, use_container_width=True)
