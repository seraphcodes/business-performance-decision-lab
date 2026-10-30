"""Step 4: build the analytical SQLite database from the original workbook.

Run from the project folder:
    python -m src.build_db

What happens:
  1. read the workbook (read-only)       2. label duplicates and categories
  3. reconcile: rows and pounds must add up, and must match the numbers the
     diagnostic found in the real workbook. If anything disagrees, NOTHING is
     written and the build stops with a clear message.
  4. write data/processed/retail.db (replaced atomically: a failed build never
     leaves a half-written database)

Tables: fact_lines (every row, labelled), dim_product, cleaning_log,
reconciliation, build_metadata. Views (sql/views.sql): v_monthly_revenue,
v_monthly_service_lines, v_top_products, v_country_revenue, v_invoice_summary,
v_customer_coverage. The build checks the views add up to the reconciliation.
"""
import argparse
import hashlib
import os
import platform
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.classify import add_time_columns, classify
from src.config import CLASS_INFO, DATABASE, EXPECTED_BASELINE, RAW_WORKBOOK, VIEWS_SQL
from src.load import prepare, read_workbook
from src.reconcile import (Check, ReconciliationError, bridge, class_summary,
                           headline_metrics, require)

PIPELINE_VERSION = "M2"


def fact_table(df):
    """The row-level table: every original row, labelled, nothing dropped."""
    fact = pd.DataFrame({
        "row_id": df["RowId"],
        "sheet_no": df["SheetNo"],
        "excel_row": df["ExcelRow"],
        "invoice_no": df["InvoiceNo"],
        "stock_code": df["StockCode"],
        "description": df["Description"].astype(object),
        "quantity": df["Quantity"],
        "unit_price": df["UnitPrice"],
        "customer_id": df["CustomerID"].astype("Int64"),
        "country": df["Country"],
        "line_value": df["LineValue"],
        "line_timestamp": df["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_timestamp": df["InvoiceTimestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_day": df["InvoiceDay"],
        "year_month": df["YearMonth"],
        "is_partial_month": df["IsPartialMonth"].astype(int),
        "row_class": df["RowClass"],
        "service_type": df["ServiceType"].astype(object),
        "is_overlap_copy": df["IsOverlapCopy"].astype(int),
        "is_within_sheet_repeat": df["IsWithinSheetRepeat"].astype(int),
        "missing_description": df["MissingDescription"].astype(int),
        "missing_customer": df["MissingCustomer"].astype(int),
    })
    return fact


def product_dimension(df):
    """One row per StockCode with its most common description.

    1,232 stock codes in the real data have more than one description, so
    product analysis must group by StockCode, never by Description.
    """
    described = df.loc[df["Description"].notna(), ["StockCode", "Description"]].copy()
    described["Description"] = described["Description"].astype(str).str.strip()
    described = described[described["Description"] != ""]
    counts = described.groupby(["StockCode", "Description"]).size().rename("n").reset_index()
    best = (counts.sort_values(["StockCode", "n", "Description"], ascending=[True, False, True])
                  .drop_duplicates("StockCode"))
    result = best[["StockCode", "Description"]].rename(
        columns={"StockCode": "stock_code", "Description": "canonical_description"})
    result["n_descriptions"] = result["stock_code"].map(
        counts.groupby("StockCode").size()).astype(int)
    result["n_lines"] = result["stock_code"].map(df.groupby("StockCode").size()).astype(int)
    return result.reset_index(drop=True)


def cleaning_log(df):
    """What each category means, how many rows it holds, and how it is treated."""
    summary = class_summary(df)
    rows = []
    for _, row in summary.iterrows():
        definition, treatment = CLASS_INFO[row["RowClass"]]
        rows.append({"kind": "category", "name": row["RowClass"], "rows": int(row["rows"]),
                     "units": int(row["units"]), "value": round(float(row["value"]), 2),
                     "definition": definition, "treatment": treatment})
    flags = [
        ("IsWithinSheetRepeat", "Repeated identical line inside one sheet",
         "Kept and flagged; sensitivity reported in the methodology."),
        ("MissingDescription", "Description is missing", "Kept; never carries revenue in this data."),
        ("MissingCustomer", "Customer ID is missing", "Kept; excluded from customer-level analysis only."),
    ]
    for column, definition, treatment in flags:
        subset = df[df[column]]
        rows.append({"kind": "flag", "name": column, "rows": int(len(subset)),
                     "units": int(subset["Quantity"].sum()),
                     "value": round(float(subset["LineValue"].sum()), 2),
                     "definition": definition, "treatment": treatment})
    return pd.DataFrame(rows)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(df, source, checks):
    items = {
        "pipeline_version": PIPELINE_VERSION,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": Path(source).name if source else "(in memory)",
        "source_sha256": _sha256(source) if source and Path(source).is_file() else "n/a",
        "rows": str(len(df)),
        "reconciliation_checks_passed": f"{sum(c.passed for c in checks)} of {len(checks)}",
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }
    return pd.DataFrame({"key": list(items), "value": list(items.values())})


def view_checks(connection, df, tolerance=0.005):
    """The SQL views must add up to the same headline numbers as the pandas bridge."""
    expected = headline_metrics(df)
    totals = {
        "v_monthly_revenue": connection.execute(
            "SELECT SUM(gross_product_sales), SUM(cancellation_value), SUM(net_product_revenue) "
            "FROM v_monthly_revenue").fetchone(),
        "v_country_revenue": connection.execute(
            "SELECT SUM(gross_product_sales), SUM(cancellation_value), SUM(net_product_revenue) "
            "FROM v_country_revenue").fetchone(),
    }
    checks = []
    for view, values in totals.items():
        for label, key, value in zip(("gross", "cancellation", "net"),
                                     ("gross_product_sales", "cancellation_value",
                                      "net_product_revenue"), values):
            value = value or 0.0
            checks.append(Check(f"View {view}: {label} equals the bridge",
                                abs(value - expected[key]) <= tolerance,
                                f"view {value:,.2f} vs bridge {expected[key]:,.2f}"))
    top = connection.execute("SELECT SUM(gross_sales) FROM v_top_products").fetchone()[0] or 0.0
    checks.append(Check("View v_top_products: gross equals the bridge",
                        abs(top - expected["gross_product_sales"]) <= tolerance,
                        f"view {top:,.2f} vs bridge {expected['gross_product_sales']:,.2f}"))
    inv = connection.execute("SELECT SUM(gross_value) FROM v_invoice_summary").fetchone()[0] or 0.0
    checks.append(Check("View v_invoice_summary: gross equals the bridge",
                        abs(inv - expected["gross_product_sales"]) <= tolerance,
                        f"view {inv:,.2f} vs bridge {expected['gross_product_sales']:,.2f}"))
    known = connection.execute("SELECT SUM(gross_value), COUNT(*) FROM v_customer_value").fetchone()
    guest = connection.execute("SELECT SUM(gross_without_customer) FROM v_customer_coverage").fetchone()[0]
    known_value, guest_value = known[0] or 0.0, guest or 0.0
    checks.append(Check("Customer views: known customers + unknown = gross sales (bridge)",
                        abs(known_value + guest_value - expected["gross_product_sales"]) <= tolerance,
                        f"{known_value:,.2f} + {guest_value:,.2f} vs bridge {expected['gross_product_sales']:,.2f}"))
    rfm = connection.execute("SELECT SUM(monetary), COUNT(*) FROM v_customer_rfm").fetchone()
    checks.append(Check("View v_customer_rfm: same customers and value as v_customer_value",
                        abs((rfm[0] or 0.0) - known_value) <= tolerance and rfm[1] == known[1],
                        f"{rfm[1]} customers / {(rfm[0] or 0.0):,.2f} vs {known[1]} / {known_value:,.2f}"))
    return checks


def _write_database(df, database, source, checks, log):
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    building = database.with_name(database.name + ".building")
    if building.exists():
        building.unlink()
    connection = sqlite3.connect(building)
    try:
        log("Writing tables...")
        fact_table(df).to_sql("fact_lines", connection, index=False, chunksize=50_000)
        product_dimension(df).to_sql("dim_product", connection, index=False)
        cleaning_log(df).to_sql("cleaning_log", connection, index=False)
        bridge(df).to_sql("reconciliation", connection, index=False)
        for column in ("row_class", "year_month", "stock_code", "invoice_no",
                       "customer_id", "country", "invoice_day"):
            connection.execute(f"CREATE INDEX idx_fact_{column} ON fact_lines({column})")
        connection.executescript(Path(VIEWS_SQL).read_text(encoding="utf-8"))
        extra = view_checks(connection, df)
        checks.extend(extra)
        failed = [c for c in extra if not c.passed]
        if failed:
            raise ReconciliationError("; ".join(f"{c.name} ({c.detail})" for c in failed))
        metadata(df, source, checks).to_sql("build_metadata", connection, index=False)
        connection.commit()
    except BaseException:
        connection.close()
        building.unlink(missing_ok=True)
        raise
    connection.close()
    os.replace(building, database)  # atomic swap: old database stays until here


def build_from_sheets(sheets, database, baseline=EXPECTED_BASELINE, source=None, log=print):
    """The whole pipeline, starting from already-loaded sheets (testable)."""
    df = prepare(sheets)
    log(f"Loaded {len(df):,} rows from {len(sheets)} sheets. Classifying...")
    df = add_time_columns(classify(df))
    checks = require(df, baseline)  # raises ReconciliationError, writes nothing
    _write_database(df, database, source, checks, log)
    return df, checks


def build(workbook=RAW_WORKBOOK, database=DATABASE, check_baseline=True, log=print):
    workbook = Path(workbook)
    if not workbook.is_file():
        raise FileNotFoundError(f"Workbook not found: {workbook}")
    log(f"Reading {workbook.name} (this can take a few minutes)...")
    sheets = read_workbook(workbook)
    baseline = EXPECTED_BASELINE if check_baseline else None
    df, checks = build_from_sheets(sheets, database, baseline, source=workbook, log=log)
    log("")
    log(bridge(df).to_string(index=False))
    log("")
    for check in checks:
        log(f"{'PASS' if check.passed else 'FAIL'}: {check.name}  ({check.detail})")
    log(f"\nDatabase written: {Path(database).resolve()}")
    return df, checks


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the retail SQLite database.")
    parser.add_argument("--workbook", default=str(RAW_WORKBOOK))
    parser.add_argument("--database", default=str(DATABASE))
    parser.add_argument("--skip-baseline-check", action="store_true",
                        help="only for test data; the real workbook must pass the baseline")
    args = parser.parse_args(argv)
    try:
        build(args.workbook, args.database, check_baseline=not args.skip_baseline_check)
    except (ReconciliationError, FileNotFoundError, ValueError) as error:
        # Expected problems get a clean message. Anything else shows its full
        # traceback, which is what we need to debug it.
        sys.exit(f"\nBUILD STOPPED: {error}")


if __name__ == "__main__":
    main()
