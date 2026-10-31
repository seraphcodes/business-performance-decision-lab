"""Tests for src/export_powerbi.py on the hand-worked fixture."""
import pandas as pd
import pytest

from src import metrics
from src.build_db import build_from_sheets
from src.export_powerbi import build_tables, verify, write
from src.reconcile import ReconciliationError


@pytest.fixture
def database(sheets, tmp_path):
    path = tmp_path / "retail.db"
    build_from_sheets(sheets, path, baseline=None, log=lambda *_: None)
    return path


@pytest.fixture
def tables(database):
    return build_tables(database)


def _bridge(database):
    return metrics.read_view("SELECT step, label, rows, value FROM reconciliation", database)


def test_fact_ties_to_the_bridge_and_only_has_sales_rows(tables, database):
    checks = verify(tables, _bridge(database))
    net = [c for c in checks if c["name"] == "net"][0]["value"]
    assert net == 93.63
    assert set(tables["fact_sales"]["row_class"]) == {"normal_sale", "cancellation"}


def test_every_fact_key_has_a_dimension_row(tables):
    fact = tables["fact_sales"]
    assert set(fact["product_key"]) <= set(tables["dim_product"]["product_key"])
    assert "stock_code" not in fact.columns
    assert set(fact["country"]) <= set(tables["dim_country"]["country"])
    assert set(fact["date"]) <= set(tables["dim_date"]["date"])
    assert set(fact["customer_id"].dropna()) == set(tables["dim_customer"]["customer_id"])


def test_partial_month_is_flagged_in_dim_date(tables):
    dates = tables["dim_date"].set_index("date")
    assert dates.loc["2011-12-05", "is_partial_month"] == 1
    assert dates.loc["2011-03-01", "is_partial_month"] == 0


def test_dimensions_have_unique_keys(tables):
    assert tables["dim_product"]["stock_code"].is_unique
    assert tables["dim_product"]["product_key"].is_unique
    assert tables["dim_date"]["date"].is_unique
    assert tables["dim_customer"]["customer_id"].is_unique


def test_export_refuses_when_the_fact_table_does_not_tie(tables, database):
    tables["fact_sales"].loc[0, "line_value"] += 1.0
    with pytest.raises(ReconciliationError, match="gross|net|cancellations"):
        verify(tables, _bridge(database))


def test_export_refuses_when_a_dimension_row_is_missing(tables, database):
    tables["dim_country"] = tables["dim_country"].iloc[0:0]
    with pytest.raises(ReconciliationError, match="dim_country"):
        verify(tables, _bridge(database))


def test_written_csv_files_read_back_the_same(tables, tmp_path):
    out = write(tables, tmp_path / "powerbi")
    back = pd.read_csv(out / "fact_sales.csv")
    assert len(back) == len(tables["fact_sales"])
    assert back["line_value"].sum() == pytest.approx(tables["fact_sales"]["line_value"].sum())
    assert not (tmp_path / "powerbi.building").exists()


def test_customers_only_on_credit_notes_do_not_break_the_export(tmp_path):
    from tests.helpers import raw_row
    rows = [raw_row("500001", "85123A", "WHITE HEART", 2, "2010-03-05 10:00", 5.0, 1001.0),
            raw_row("C500002", "85123A", "WHITE HEART", -1, "2010-03-06 10:00", 5.0, 2002.0)]  # 2002 never bought
    path = tmp_path / "credit.db"
    build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=lambda *_: None)
    tables = build_tables(path)
    verify(tables, _bridge(path))
    fact = tables["fact_sales"]
    assert fact.loc[fact["row_class"] == "cancellation", "customer_id"].isna().all()
    assert set(tables["dim_customer"]["customer_id"]) == {1001}


def _sql_products(database):
    return metrics.read_view("SELECT stock_code, net_sales FROM v_top_products", database)


def test_product_totals_equal_the_sql_view(tables, database):
    verify(tables, _bridge(database), _sql_products(database))


def test_codes_that_differ_only_by_case_get_separate_keys(tmp_path):
    from tests.helpers import raw_row
    rows = [raw_row("500001", "85123A", "WHITE HEART", 2, "2010-03-05 10:00", 5.0, 1001.0),
            raw_row("500002", "85123a", "WHITE HEART", 3, "2010-03-06 10:00", 5.0, 1001.0)]
    path = tmp_path / "case.db"
    build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=lambda *_: None)
    tables = build_tables(path)
    products = tables["dim_product"].set_index("stock_code")
    assert products.loc["85123A", "product_key"] != products.loc["85123a", "product_key"]
    net = tables["fact_sales"].groupby("product_key")["line_value"].sum()
    assert net[products.loc["85123A", "product_key"]] == pytest.approx(10.0)
    assert net[products.loc["85123a", "product_key"]] == pytest.approx(15.0)
    verify(tables, _bridge(path), _sql_products(path))   # still ties to SQL, nothing merged


def test_export_refuses_when_a_product_total_differs_from_sql(tables, database):
    tables["fact_sales"].loc[tables["fact_sales"].index[0], "product_key"] = tables["dim_product"]["product_key"].iloc[-1]
    with pytest.raises(ReconciliationError, match="v_top_products"):
        verify(tables, _bridge(database), _sql_products(database))
