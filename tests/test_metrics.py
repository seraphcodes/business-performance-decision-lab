"""Tests for sql/views.sql and src/metrics.py.

Hand-calculated expectations come from the fixture in tests/helpers.py.
A randomized test cross-checks every view against an independent pandas calculation.
"""
import random
import sqlite3

import pandas as pd
import pytest

from src import metrics
from src.build_db import build_from_sheets
from tests.helpers import raw_row

quiet = lambda *_: None  # noqa: E731


@pytest.fixture
def db(sheets, tmp_path):
    path = tmp_path / "retail.db"
    build_from_sheets(sheets, path, baseline=None, log=quiet)
    return path


def test_monthly_revenue_hand_values(db):
    table = metrics.monthly_revenue(db, include_partial=True).set_index("year_month")
    assert round(table.loc["2010-11", "gross_product_sales"], 2) == 35.00
    assert round(table.loc["2010-12", "gross_product_sales"], 2) == 30.00
    mar = table.loc["2011-03"]
    assert round(mar["gross_product_sales"], 2) == 31.13
    assert round(mar["cancellation_value"], 2) == -5.00
    assert round(mar["net_product_revenue"], 2) == 26.13
    assert mar["cancellation_rate_pct"] == pytest.approx(16.06, abs=0.01)
    assert round(table.loc["2011-12", "gross_product_sales"], 2) == 2.50
    assert table.loc["2011-12", "is_partial_month"] == 1


def test_partial_month_is_excluded_by_default(db):
    assert "2011-12" not in metrics.monthly_revenue(db)["year_month"].tolist()


def test_services_never_enter_product_revenue(db):
    service = metrics.monthly_service_lines(db)
    assert round(service["value"].sum(), 2) == -132.00
    assert round(metrics.monthly_revenue(db, include_partial=True)["net_product_revenue"].sum(), 2) == 93.63


def test_top_products_ranked_by_stock_code(db):
    top = metrics.top_products(db, n=3)
    # 85123A sold 42.50 but 5.00 was cancelled -> net 37.50, so it ranks BELOW 22423 (40.00)
    assert top["stock_code"].tolist() == ["22423", "85123A", "DCGS0076"]
    assert [round(v, 2) for v in top["gross_sales"]] == [40.00, 42.50, 16.13]
    assert [round(v, 2) for v in top["cancelled_value"]] == [0.00, -5.00, 0.00]
    assert [round(v, 2) for v in top["net_sales"]] == [40.00, 37.50, 16.13]
    assert top["sales_rank"].tolist() == [1, 2, 3]


def test_headline_kpis(db):
    kpis = metrics.headline_kpis(db)
    assert round(kpis["net_product_revenue"], 2) == 93.63
    assert kpis["sales_invoices"] == 6
    assert kpis["known_customers"] == 4
    assert round(kpis["avg_order_value"], 2) == 16.44
    assert round(kpis["cancellation_rate_pct"], 2) == 5.07
    assert round(kpis["known_customer_share_pct"], 2) == 84.79


def test_country_views_add_up_to_total(db):
    country = metrics.country_revenue(db)
    assert round(country["net_product_revenue"].sum(), 2) == 93.63


def test_database_is_opened_read_only(db):
    connection = metrics.connect(db)
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("DELETE FROM fact_lines")
    connection.close()


def test_missing_database_gives_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_db"):
        metrics.connect(tmp_path / "nope.db")


def _random_sheets(seed, n=300):
    rng = random.Random(seed)
    codes = ["85123A", "22423", "21730", "DCGS0076", "POST", "AMAZONFEE", "C3", "20725"]
    countries = ["United Kingdom", "France", "Germany"]
    rows = []
    for i in range(n):
        code = rng.choice(codes)
        quantity = rng.choice([-3, -1, 1, 2, 5, 12])
        price = rng.choice([0.0, 0.85, 1.25, 2.5, 4.95, -1.0])
        prefix = "C" if rng.random() < 0.15 else ""
        customer = rng.choice([float("nan"), 12001.0, 12002.0, 12003.0])
        day = rng.randint(1, 28)
        month = rng.choice([1, 2, 3])
        row = raw_row(f"{prefix}{600000 + i // 3}", code, "ITEM " + code, quantity,
                      f"2011-{month:02d}-{day:02d} 10:00", price, customer)
        row["Country"] = rng.choice(countries)
        rows.append(row)
    half = len(rows) // 2
    return {"A": pd.DataFrame(rows[:half + 20]), "B": pd.DataFrame(rows[half:])}


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_views_match_an_independent_pandas_calculation(seed, tmp_path):
    path = tmp_path / "r.db"
    df, _ = build_from_sheets(_random_sheets(seed), path, baseline=None, log=quiet)
    sales = df[df["RowClass"].isin(["normal_sale", "cancellation"])]
    expected = sales.groupby("YearMonth").apply(lambda g: pd.Series({
        "gross": g.loc[g["RowClass"] == "normal_sale", "LineValue"].sum(),
        "cancel": g.loc[g["RowClass"] == "cancellation", "LineValue"].sum(),
        "invoices": g.loc[g["RowClass"] == "normal_sale", "InvoiceNo"].nunique(),
    }), include_groups=False)
    got = metrics.monthly_revenue(path, include_partial=True).set_index("year_month")
    assert set(got.index) == set(expected.index)
    for month in expected.index:
        assert got.loc[month, "gross_product_sales"] == pytest.approx(expected.loc[month, "gross"], abs=1e-6)
        assert got.loc[month, "cancellation_value"] == pytest.approx(expected.loc[month, "cancel"], abs=1e-6)
        assert got.loc[month, "sales_invoices"] == expected.loc[month, "invoices"]
    by_country = sales.groupby("Country")["LineValue"].sum()
    got_country = metrics.country_revenue(path).set_index("country")["net_product_revenue"]
    for name, value in by_country.items():
        assert got_country[name] == pytest.approx(value, abs=1e-6)
    normal = df[df["RowClass"] == "normal_sale"]
    top_table = metrics.top_products(path, n=1000).set_index("stock_code")
    for code, value in normal.groupby("StockCode")["LineValue"].sum().items():
        assert top_table.loc[code, "gross_sales"] == pytest.approx(value, abs=1e-6)
    for code, value in sales.groupby("StockCode")["LineValue"].sum().items():
        assert top_table.loc[code, "net_sales"] == pytest.approx(value, abs=1e-6)
    ranked = metrics.top_products(path, n=1000)
    assert ranked["net_sales"].is_monotonic_decreasing  # rank follows net sales value, not units


def test_service_line_counts_only_count_service_rows(db):
    assert metrics.monthly_service_lines(db)["line_count"].sum() == 3  # POST, AMAZONFEE, B
