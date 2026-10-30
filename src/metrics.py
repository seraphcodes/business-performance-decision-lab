"""Read-only access to the metric views, for the dashboard and for checking numbers.

    python -m src.metrics        # prints the headline report (paste it into the chat to check)

Nothing here recomputes business logic: the definitions live in sql/views.sql
and are documented in docs/metrics.md.
"""
import math
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATABASE


def connect(database=DATABASE):
    """Open the database read-only, so the app can never change the data."""
    path = Path(database)
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}. Run: python -m src.build_db")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def read_view(sql, database=DATABASE, params=()):
    connection = connect(database)
    try:
        return pd.read_sql_query(sql, connection, params=params)
    finally:
        connection.close()


def monthly_revenue(database=DATABASE, include_partial=False):
    """Monthly table. The partial last month is left out unless asked for."""
    table = read_view("SELECT * FROM v_monthly_revenue ORDER BY year_month", database)
    if not include_partial:
        table = table[table["is_partial_month"] == 0]
    return table.reset_index(drop=True)


def monthly_service_lines(database=DATABASE):
    return read_view("SELECT * FROM v_monthly_service_lines ORDER BY year_month, service_type",
                     database)


def top_products(database=DATABASE, n=10):
    return read_view("SELECT * FROM v_top_products ORDER BY sales_rank, stock_code LIMIT ?",
                     database, params=(int(n),))


def country_revenue(database=DATABASE):
    return read_view("SELECT * FROM v_country_revenue ORDER BY gross_product_sales DESC, country",
                     database)


def customer_coverage(database=DATABASE):
    return read_view("SELECT * FROM v_customer_coverage ORDER BY year_month", database)


def cohort_retention(database=DATABASE):
    """Cohort x months-since-first-order table (full months only; see v_cohort_activity)."""
    return read_view("SELECT * FROM v_cohort_activity ORDER BY cohort_month, months_since", database)


def customer_rfm(database=DATABASE):
    return read_view("SELECT * FROM v_customer_rfm ORDER BY customer_id", database)


SEGMENT_ORDER = ["Champions", "Loyal", "Recent", "Needs attention", "At risk", "Inactive"]


def rfm_segments(database=DATABASE):
    """One row per RFM segment: how many customers, and how much of the gross sales."""
    rfm = customer_rfm(database)
    total_customers, total_value = len(rfm), rfm["monetary"].sum()
    rows = []
    for name in SEGMENT_ORDER:
        part = rfm[rfm["segment"] == name]
        if part.empty:
            continue
        rows.append({
            "segment": name,
            "customers": int(len(part)),
            "customers_pct": 100 * len(part) / total_customers,
            "gross_value": float(part["monetary"].sum()),
            "gross_value_pct": 100 * part["monetary"].sum() / total_value if total_value else 0.0,
            "avg_recency_days": float(part["recency_days"].mean()),
            "avg_orders": float(part["frequency"].mean()),
        })
    return pd.DataFrame(rows)


def customer_concentration(database=DATABASE, shares=(0.01, 0.05, 0.10, 0.20)):
    """Share of known-customer gross sales held by the top p% of customers (largest first).

    The top p% means the largest ceil(p * n) customers; ties are broken by customer id.
    """
    values = read_view("SELECT customer_id, gross_value FROM v_customer_value "
                       "ORDER BY gross_value DESC, customer_id", database)["gross_value"]
    n, total = len(values), float(values.sum())
    rows = []
    for share in shares:
        k = min(n, math.ceil(round(share * n, 9))) if n else 0
        value = float(values.head(k).sum())
        rows.append({"top_pct": round(100 * share, 4), "customers": int(k), "gross_value": value,
                     "share_of_known_pct": 100 * value / total if total else 0.0})
    return pd.DataFrame(rows)


def customer_summary(database=DATABASE):
    """Whole-period customer facts used on the customer page (all from the views)."""
    connection = connect(database)
    try:
        customers, repeaters, known_value = connection.execute(
            "SELECT COUNT(*), SUM(orders >= 2), SUM(gross_value) FROM v_customer_value").fetchone()
        all_gross = connection.execute(
            "SELECT SUM(gross_with_customer + gross_without_customer) FROM v_customer_coverage").fetchone()[0]
        snapshot = connection.execute(
            "SELECT date(MAX(invoice_day), '+1 day') FROM fact_lines WHERE row_class = 'normal_sale'").fetchone()[0]
        first_month = connection.execute("SELECT MIN(year_month) FROM v_monthly_revenue").fetchone()[0]
        last_full = connection.execute(
            "SELECT MAX(year_month) FROM v_monthly_revenue WHERE is_partial_month = 0").fetchone()[0]
    finally:
        connection.close()
    customers, repeaters = int(customers or 0), int(repeaters or 0)
    known_value, all_gross = float(known_value or 0.0), float(all_gross or 0.0)
    return {
        "known_customers": customers,
        "repeat_customers": repeaters,
        "repeat_customers_pct": 100 * repeaters / customers if customers else 0.0,
        "known_gross": known_value,
        "all_gross": all_gross,
        "known_share_of_gross_pct": 100 * known_value / all_gross if all_gross else 0.0,
        "snapshot_day": snapshot,
        "first_data_month": first_month,
        "last_full_month": last_full,
    }


def headline_kpis(database=DATABASE):
    """One dict of whole-period numbers; all come from the views."""
    connection = connect(database)
    try:
        gross, cancel, net, sales_invoices, credit_notes = connection.execute(
            "SELECT SUM(gross_product_sales), SUM(cancellation_value), SUM(net_product_revenue), "
            "SUM(sales_invoices), SUM(credit_notes) FROM v_monthly_revenue").fetchone()
        orders, customers = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM v_invoice_summary").fetchone()
        with_customer = connection.execute(
            "SELECT SUM(gross_with_customer) FROM v_customer_coverage").fetchone()[0]
    finally:
        connection.close()
    gross = gross or 0.0
    return {
        "gross_product_sales": gross,
        "cancellation_value": cancel or 0.0,
        "net_product_revenue": net or 0.0,
        "cancellation_rate_pct": 100 * -(cancel or 0.0) / gross if gross else 0.0,
        "sales_invoices": int(orders),
        "credit_notes": int(credit_notes or 0),
        "known_customers": int(customers),
        "avg_order_value": gross / orders if orders else 0.0,
        "known_customer_share_pct": 100 * (with_customer or 0.0) / gross if gross else 0.0,
    }


def main():
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    kpis = headline_kpis()
    print("HEADLINE KPIs")
    for key, value in kpis.items():
        print(f"  {key:28s} {value:>16,.2f}")
    print("\nMONTHLY (all months, partial flagged)")
    print(monthly_revenue(include_partial=True).round(2).to_string(index=False))
    print("\nTOP 10 PRODUCTS")
    print(top_products(n=10).round(2).to_string(index=False))
    print("\nTOP 10 COUNTRIES")
    print(country_revenue().head(10).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
