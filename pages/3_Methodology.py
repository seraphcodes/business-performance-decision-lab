"""Methodology: how the numbers were made, straight from the project's own documents.

The text comes from docs/cleaning_rules.md and docs/metrics.md (one source of truth)
and the reconciliation table is read live from the database that the build checked.
"""
import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import metrics  # noqa: E402
from src.config import DATABASE  # noqa: E402

DB = os.environ.get("RETAIL_DB", str(DATABASE))

st.set_page_config(page_title="Methodology", page_icon="📐", layout="wide")
st.title("Methodology")
st.caption("How the raw workbook becomes the numbers on the Overview page, and what they cannot tell you.")


def read_doc(name):
    path = ROOT / "docs" / name
    return path.read_text(encoding="utf-8") if path.is_file() else f"*{name} not found.*"


st.header("1. From raw rows to revenue")
if Path(DB).is_file():
    bridge = metrics.read_view("SELECT step, label, rows, value FROM reconciliation", DB)
    by_label = bridge.set_index("label")["value"]
    raw = by_label["Raw total, every row of both sheets"]
    overlap = by_label["less: sheet-overlap copies"]
    dedup = by_label["= Deduplicated total (A + B)"]
    services = by_label["  of which service_or_fee"] if "  of which service_or_fee" in by_label else \
        bridge.loc[bridge["label"].str.contains("service_or_fee"), "value"].iloc[0]
    net = by_label["Net product revenue (M1 + M2)"]
    labels = ["Raw total<br>both sheets", "Duplicate copies<br>(sheet overlap)", "After removing<br>duplicates",
              "Remove postage,<br>fees, adjustments", "Net product<br>revenue"]
    # Plain bars: (bottom, height, colour, label). Totals start at the axis floor.
    floor = min(raw, dedup, net) - 250_000
    bars = [
        (floor, raw - floor, "#5b6b82", f"£{raw:,.0f}"),
        (dedup, raw - dedup, "#c0392b", f"-£{raw - dedup:,.0f}"),
        (floor, dedup - floor, "#5b6b82", f"£{dedup:,.0f}"),
        (min(dedup, net), abs(net - dedup), "#2a6fdb", f"+£{net - dedup:,.0f}"),
        (floor, net - floor, "#5b6b82", f"£{net:,.0f}"),
    ]
    waterfall = go.Figure(go.Bar(
        x=labels, y=[h for _, h, _, _ in bars], base=[b for b, _, _, _ in bars],
        marker_color=[c for _, _, c, _ in bars], text=[t for _, _, _, t in bars],
        textposition="outside", cliponaxis=False, hoverinfo="skip"))
    waterfall.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0), showlegend=False,
                            yaxis=dict(range=[floor, raw + 250_000], tickprefix="£", tickformat=",.0f"))
    st.plotly_chart(waterfall, use_container_width=True)
    st.caption("The axis starts near £18.6M so the steps are visible. Cancellations stay inside net product "
               "revenue (they reduce it). Postage, fees and adjustments were a net negative, so taking them "
               "out raises the total.")
    info = metrics.read_view("SELECT key, value FROM build_metadata", DB).set_index("key")["value"]
    st.caption(f"Built {info.get('built_at', '?')} from {info.get('source_file', '?')}. "
               f"Reconciliation checks passed: {info.get('reconciliation_checks_passed', '?')}. "
               "The build refuses to write the database if rows or pounds do not add up.")
    with st.expander("Full reconciliation table"):
        table = bridge.copy()
        table["value"] = table["value"].map(lambda v: f"£{v:,.2f}")
        table["rows"] = table["rows"].map(lambda v: f"{v:,}")
        st.dataframe(table.rename(columns={"step": "Step", "label": "What", "rows": "Rows", "value": "Value"}),
                     hide_index=True, use_container_width=True)
else:
    st.warning("Database not built yet. Run `python -m build_db` to see the live reconciliation.".replace(
        "python -m build_db", "python -m src.build_db"))

st.header("2. Rules and definitions")
with st.expander("Cleaning rules and metric definitions (the full rule table)"):
    st.markdown(read_doc("cleaning_rules.md").split("\n", 1)[1])
with st.expander("Metric views (what each dashboard number is built from)"):
    st.markdown(read_doc("metrics.md").split("\n", 1)[1])

st.header("3. What this data cannot tell you")
st.markdown("""
- **Profit.** There are no product costs, so every figure is revenue.
- **Customer behaviour for everyone.** About 13% of sales value has no customer ID.
- **Order-level return rates.** Credit notes cannot be linked to the original sale.
- **The last month.** December 2011 stops on the 9th.
- **Causes.** The data shows what was sold, not why.
""")
st.info("Dataset: Online Retail II, UCI Machine Learning Repository, CC BY 4.0.")
