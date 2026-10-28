"""Read-only access to the metric views, for the dashboard and for checking numbers.

    python -m src.metrics        # prints the headline report (paste it into the chat to check)

Nothing here recomputes business logic: the definitions live in sql/views.sql
and are documented in docs/metrics.md.
"""
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
