"""Step 3: prove that every pound and every row is accounted for.

The bridge walks from the raw total (every row, nothing excluded) down to the
headline metrics. Excluded and separately classified rows stay in the table.
"""
import math
from collections import namedtuple

import pandas as pd

from src.config import ASSIGNABLE_CLASSES, CLASS_ORDER

TOLERANCE = 0.005  # half a penny; sums of floats are compared with this

Check = namedtuple("Check", "name passed detail")


class ReconciliationError(Exception):
    """Raised when the numbers do not add up. The database is not written."""


def _total(values):
    """Exact float summation (order-independent to the last bit)."""
    return math.fsum(values.astype(float).tolist())


def class_summary(df):
    """Rows, units, value and invoices for each category, in rule order."""
    grouped = df.groupby("RowClass").agg(
        rows=("RowId", "size"),
        units=("Quantity", "sum"),
        value=("LineValue", "sum"),
        invoices=("InvoiceNo", "nunique"),
    )
    return grouped.reindex(CLASS_ORDER).fillna(0).reset_index()


def headline_metrics(df):
    """The three revenue metrics, defined exactly as in docs/cleaning_rules.md."""
    gross = _total(df.loc[df["RowClass"] == "normal_sale", "LineValue"])
    cancelled = _total(df.loc[df["RowClass"] == "cancellation", "LineValue"])
    return {
        "gross_product_sales": gross,
        "cancellation_value": cancelled,
        "net_product_revenue": gross + cancelled,
        "cancellation_pct_of_gross": (-cancelled / gross) if gross else 0.0,
    }


def bridge(df):
    """Raw total -> deduplicated total -> categories -> headline metrics."""
    overlap = df["IsOverlapCopy"]
    raw_total = _total(df["LineValue"])
    copy_value = _total(df.loc[overlap, "LineValue"])
    rows = []

    def add(step, label, row_count, value):
        rows.append({"step": step, "label": label, "rows": int(row_count), "value": round(value, 2)})

    add("A", "Raw total, every row of both sheets", len(df), raw_total)
    add("B", "less: sheet-overlap copies", overlap.sum(), -copy_value)
    add("C", "= Deduplicated total (A + B)", (~overlap).sum(), raw_total - copy_value)
    category_total = 0.0
    for name in ASSIGNABLE_CLASSES[1:] + ["other_unclassified"]:
        subset = df.loc[df["RowClass"] == name]
        value = _total(subset["LineValue"])
        category_total += value
        add("", f"  of which {name}", len(subset), value)
    add("", "  sum of categories", (~overlap).sum(), category_total)

    metrics = headline_metrics(df)
    add("M1", "Gross product sales (normal_sale)", (df["RowClass"] == "normal_sale").sum(),
        metrics["gross_product_sales"])
    add("M2", "Cancellation value (cancellation)", (df["RowClass"] == "cancellation").sum(),
        metrics["cancellation_value"])
    add("M3", "Net product revenue (M1 + M2)",
        df["RowClass"].isin(["normal_sale", "cancellation"]).sum(), metrics["net_product_revenue"])
    return pd.DataFrame(rows)


def _close(a, b):
    return abs(a - b) <= TOLERANCE


def verify(df, baseline=None):
    """Run every reconciliation check and return the list of results."""
    overlap = df["IsOverlapCopy"]
    raw_total = _total(df["LineValue"])
    overlap_value = _total(df.loc[overlap, "LineValue"])
    non_overlap_total = _total(df.loc[~overlap, "LineValue"])
    summary = class_summary(df)
    checks = []

    def add(name, passed, detail):
        checks.append(Check(name, bool(passed), detail))

    unclassified = int(summary.loc[summary["RowClass"] == "other_unclassified", "rows"].iloc[0])
    add("No row is unclassified", unclassified == 0, f"{unclassified} unclassified rows")
    add("Category rows add up to total rows",
        int(summary["rows"].sum()) == len(df),
        f"{int(summary['rows'].sum()):,} vs {len(df):,}")
    category_value = math.fsum(summary["value"].tolist())
    add("Category values add up to the raw total", _close(category_value, raw_total),
        f"{category_value:,.2f} vs {raw_total:,.2f}")
    add("Raw total minus overlap copies equals the deduplicated total",
        _close(raw_total - overlap_value, non_overlap_total),
        f"{raw_total - overlap_value:,.2f} vs {non_overlap_total:,.2f}")

    if baseline:
        repeats = int(df["IsWithinSheetRepeat"].sum())
        actual = {
            "rows": len(df),
            "raw_total": raw_total,
            "overlap_rows": int(overlap.sum()),
            "overlap_value": overlap_value,
            "deduplicated_total": non_overlap_total,
            "within_sheet_repeat_rows": repeats,
        }
        for key, expected in baseline.items():
            if isinstance(expected, float):
                add(f"Baseline: {key}", _close(actual[key], expected),
                    f"{actual[key]:,.2f} vs expected {expected:,.2f}")
            else:
                add(f"Baseline: {key}", actual[key] == expected,
                    f"{actual[key]:,} vs expected {expected:,}")
    return checks


def require(df, baseline=None):
    """Like verify, but raise ReconciliationError if any check fails."""
    checks = verify(df, baseline)
    failed = [check for check in checks if not check.passed]
    if failed:
        lines = "\n".join(f"  - {check.name}: {check.detail}" for check in failed)
        raise ReconciliationError("Reconciliation failed, nothing was written:\n" + lines)
    return checks
