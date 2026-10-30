"""Export the verified data as a star schema of CSV files for Power BI Desktop.

    python -m src.export_powerbi

Reads data/processed/retail.db (read-only) and writes data/processed/powerbi/*.csv
(that folder is git-ignored: the files hold one row per sales line and are only
for your own Power BI report). Same rules as the website export:
  * the sales population only (normal_sale + cancellation lines);
  * the totals must tie to the reconciliation bridge, or nothing is written;
  * files are written to a temporary folder first and swapped in at the end.

Tables: fact_sales, dim_date, dim_product, dim_country, dim_customer, cohort_activity.
"""
import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

from src import metrics
from src.config import DATABASE, PROJECT_ROOT
from src.export_web import TOLERANCE, _bridge_value
from src.reconcile import ReconciliationError

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "powerbi"


def build_tables(database=DATABASE):
    fact = metrics.read_view(
        "SELECT row_id, invoice_no, invoice_day AS date, stock_code, customer_id, country, "
        "quantity, unit_price, line_value, row_class FROM fact_lines "
        "WHERE row_class IN ('normal_sale', 'cancellation') ORDER BY row_id", database)
    fact["customer_id"] = fact["customer_id"].astype("Int64")
    # Credit notes are not matched to customers anywhere in this project (docs/customer_analytics.md),
    # and some customers only appear on credit notes, so they have no row in dim_customer.
    # Keep the customer only on purchase lines; cancellation lines get a blank customer.
    fact.loc[fact["row_class"] == "cancellation", "customer_id"] = pd.NA

    months = metrics.read_view(
        "SELECT year_month, MAX(is_partial_month) AS is_partial_month FROM fact_lines "
        "WHERE row_class IN ('normal_sale', 'cancellation') GROUP BY year_month", database)
    dates = pd.DataFrame({"date": sorted(fact["date"].unique())})
    dates["year_month"] = dates["date"].str[:7]
    dates["year"] = dates["date"].str[:4].astype(int)
    dates["month_no"] = dates["date"].str[5:7].astype(int)
    dates["month_name"] = pd.to_datetime(dates["date"]).dt.strftime("%b")
    dates = dates.merge(months, on="year_month", how="left")

    products = metrics.read_view(
        "SELECT stock_code, canonical_description AS description FROM dim_product "
        "WHERE stock_code IN (SELECT DISTINCT stock_code FROM fact_lines "
        "WHERE row_class IN ('normal_sale', 'cancellation')) ORDER BY stock_code", database)
    countries = pd.DataFrame({"country": sorted(fact["country"].dropna().unique())})
    customers = metrics.read_view(
        "SELECT v.customer_id, v.first_month, v.first_day, v.last_day, v.orders, v.gross_value, "
        "r.recency_days, r.r_score, r.f_score, r.m_score, r.segment "
        "FROM v_customer_value v JOIN v_customer_rfm r USING (customer_id) ORDER BY v.customer_id",
        database)
    customers["customer_id"] = customers["customer_id"].astype("Int64")
    cohorts = metrics.cohort_retention(database)
    return {"fact_sales": fact, "dim_date": dates, "dim_product": products,
            "dim_country": countries, "dim_customer": customers, "cohort_activity": cohorts}


def verify(tables, bridge):
    """The exported fact table must tie to the bridge, and every key must have a dimension row."""
    fact = tables["fact_sales"]
    gross = fact.loc[fact["row_class"] == "normal_sale", "line_value"].sum()
    cancel = fact.loc[fact["row_class"] == "cancellation", "line_value"].sum()
    checks = [("gross", gross, _bridge_value(bridge, "Gross product sales")),
              ("cancellations", cancel, _bridge_value(bridge, "Cancellation value")),
              ("net", gross + cancel, _bridge_value(bridge, "Net product revenue"))]
    problems = [f"{name}: {got:,.2f} vs bridge {want:,.2f}" for name, got, want in checks
                if abs(got - want) > TOLERANCE]
    for column, dim, key in (("stock_code", "dim_product", "stock_code"), ("country", "dim_country", "country"),
                             ("date", "dim_date", "date")):
        missing = set(fact[column].dropna()) - set(tables[dim][key])
        if missing:
            problems.append(f"{len(missing)} {column} values have no row in {dim}")
    known = set(fact["customer_id"].dropna())
    if known != set(tables["dim_customer"]["customer_id"].dropna()):
        problems.append("customers in fact_sales and dim_customer differ")
    if problems:
        raise ReconciliationError("Power BI export refused: " + "; ".join(problems))
    return [{"name": name, "value": round(got, 2)} for name, got, _ in checks]


def write(tables, out_dir=OUT_DIR):
    out_dir = Path(out_dir)
    building = out_dir.with_name(out_dir.name + ".building")
    if building.exists():
        shutil.rmtree(building)
    building.mkdir(parents=True)
    try:
        for name, table in tables.items():
            table.to_csv(building / f"{name}.csv", index=False, encoding="utf-8")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        building.rename(out_dir)
    except BaseException:
        shutil.rmtree(building, ignore_errors=True)
        raise
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export CSV tables for Power BI Desktop.")
    parser.add_argument("--database", default=str(DATABASE))
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    try:
        tables = build_tables(args.database)
        bridge = metrics.read_view("SELECT step, label, rows, value FROM reconciliation", args.database)
        checks = verify(tables, bridge)
        path = write(tables, args.out)
    except (ReconciliationError, FileNotFoundError) as error:
        sys.exit(f"\nPOWER BI EXPORT STOPPED: {error}")
    print(f"Wrote {len(tables)} CSV files to {path}")
    for name, table in tables.items():
        print(f"  {name:16s} {len(table):>9,} rows")
    print("Checks vs bridge: " + ", ".join(f"{c['name']} {c['value']:,.2f}" for c in checks))


if __name__ == "__main__":
    main()
