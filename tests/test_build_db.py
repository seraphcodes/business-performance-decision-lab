"""Tests for src/load.py and src/build_db.py (workbook -> SQLite)."""
import sqlite3

import pandas as pd
import pytest

import src.build_db as build_db_module
from src.build_db import build, build_from_sheets, product_dimension
from src.load import prepare, read_workbook
from src.reconcile import ReconciliationError

HAND_BASELINE = {"rows": 21, "raw_total": 4.63, "overlap_rows": 4, "overlap_value": 48.00,
                 "deduplicated_total": -43.37, "within_sheet_repeat_rows": 2}


def query(database, sql):
    connection = sqlite3.connect(database)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


# ------------------------------------------------------------------ load
def test_prepare_adds_traceability_columns(prepared):
    assert len(prepared) == 21
    assert prepared["RowId"].tolist() == list(range(21))
    first_of_sheet_2 = prepared[prepared["SheetNo"] == 2].iloc[0]
    assert first_of_sheet_2["ExcelRow"] == 2  # header is row 1 in Excel
    assert round(prepared["LineValue"].sum(), 2) == 4.63


def test_prepare_rejects_a_sheet_with_missing_columns():
    with pytest.raises(ValueError, match="missing expected columns"):
        prepare({"Bad": pd.DataFrame({"Invoice": ["1"]})})


def test_workbook_round_trip_through_a_real_xlsx_file(sheets, tmp_path):
    path = tmp_path / "tiny.xlsx"
    with pd.ExcelWriter(path) as writer:
        for name, table in sheets.items():
            table.to_excel(writer, sheet_name=name, index=False)
    from_file = prepare(read_workbook(path))
    assert len(from_file) == 21
    assert round(from_file["LineValue"].sum(), 2) == 4.63


# -------------------------------------------------------------- database
def test_database_holds_every_row_and_ties_to_the_raw_total(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=HAND_BASELINE, log=lambda *_: None)
    assert query(database, "SELECT COUNT(*) FROM fact_lines") == [(21,)]
    assert query(database, "SELECT ROUND(SUM(line_value), 2) FROM fact_lines") == [(4.63,)]
    by_class = dict(query(database, "SELECT row_class, COUNT(*) FROM fact_lines GROUP BY row_class"))
    assert by_class["normal_sale"] == 9 and by_class["sheet_overlap_copy"] == 4


def test_net_product_revenue_from_sql_matches_the_hand_calculation(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    sql = ("SELECT ROUND(SUM(line_value), 2) FROM fact_lines "
           "WHERE row_class IN ('normal_sale', 'cancellation')")
    assert query(database, sql) == [(93.63,)]


def test_all_expected_tables_and_flags_exist(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    tables = {name for (name,) in query(database, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"fact_lines", "dim_product", "cleaning_log", "reconciliation", "build_metadata"}
    assert query(database, "SELECT COUNT(*) FROM fact_lines WHERE is_within_sheet_repeat = 1") == [(2,)]
    assert query(database, "SELECT COUNT(*) FROM fact_lines WHERE customer_id IS NULL") == [(7,)]
    assert query(database, "SELECT COUNT(*) FROM fact_lines WHERE is_partial_month = 1") == [(1,)]


def test_reconciliation_table_is_stored(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    sql = "SELECT value FROM reconciliation WHERE step = 'C'"
    assert query(database, sql) == [(-43.37,)]


def test_product_dimension_picks_the_most_common_description():
    rows = [("85123A", "WHITE HEART")] * 3 + [("85123A", "WHITE HANGING HEART")] + [("22423", "CAKESTAND")]
    df = pd.DataFrame(rows, columns=["StockCode", "Description"])
    df["Description"] = df["Description"].astype(object)
    result = product_dimension(df).set_index("stock_code")
    assert result.loc["85123A", "canonical_description"] == "WHITE HEART"
    assert result.loc["85123A", "n_descriptions"] == 2
    assert result.loc["85123A", "n_lines"] == 4


def test_failed_reconciliation_writes_nothing(sheets, tmp_path):
    database = tmp_path / "retail.db"
    wrong = dict(HAND_BASELINE, rows=999)
    with pytest.raises(ReconciliationError):
        build_from_sheets(sheets, database, baseline=wrong, log=lambda *_: None)
    assert not database.exists()
    assert not (tmp_path / "retail.db.building").exists()


def test_failed_build_keeps_the_previous_database(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=HAND_BASELINE, log=lambda *_: None)
    before = database.read_bytes()
    with pytest.raises(ReconciliationError):
        build_from_sheets(sheets, database, baseline=dict(HAND_BASELINE, rows=1), log=lambda *_: None)
    assert database.read_bytes() == before


def test_build_from_a_workbook_file_and_the_original_is_untouched(sheets, tmp_path):
    workbook = tmp_path / "tiny.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        for name, table in sheets.items():
            table.to_excel(writer, sheet_name=name, index=False)
    fingerprint = workbook.read_bytes()
    database = tmp_path / "out" / "retail.db"
    build(workbook, database, check_baseline=False, log=lambda *_: None)
    assert workbook.read_bytes() == fingerprint
    assert query(database, "SELECT value FROM build_metadata WHERE key = 'rows'") == [("21",)]
    sha = query(database, "SELECT value FROM build_metadata WHERE key = 'source_sha256'")[0][0]
    assert len(sha) == 64


def test_missing_workbook_gives_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Workbook not found"):
        build(tmp_path / "nope.xlsx", tmp_path / "x.db", log=lambda *_: None)


def _views_that_do_not_tie_to_the_bridge(tmp_path):
    """A copy of sql/views.sql where the country view overstates gross sales by 1%."""
    text = build_db_module.VIEWS_SQL.read_text(encoding="utf-8")
    head, tail = text.split("CREATE VIEW v_country_revenue", 1)
    broken = tail.replace("THEN line_value ELSE 0 END) AS gross_product_sales",
                          "THEN line_value * 1.01 ELSE 0 END) AS gross_product_sales", 1)
    assert broken != tail
    path = tmp_path / "broken_views.sql"
    path.write_text(head + "CREATE VIEW v_country_revenue" + broken, encoding="utf-8")
    return path


def test_a_view_that_does_not_tie_to_the_bridge_blocks_the_build(sheets, tmp_path, monkeypatch):
    monkeypatch.setattr(build_db_module, "VIEWS_SQL", _views_that_do_not_tie_to_the_bridge(tmp_path))
    database = tmp_path / "retail.db"
    with pytest.raises(ReconciliationError, match="v_country_revenue"):
        build_from_sheets(sheets, database, baseline=HAND_BASELINE, log=lambda *_: None)
    assert not database.exists()
    assert not (tmp_path / "retail.db.building").exists()


def test_a_view_mismatch_keeps_the_previous_database(sheets, tmp_path, monkeypatch):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=HAND_BASELINE, log=lambda *_: None)
    before = database.read_bytes()
    monkeypatch.setattr(build_db_module, "VIEWS_SQL", _views_that_do_not_tie_to_the_bridge(tmp_path))
    with pytest.raises(ReconciliationError):
        build_from_sheets(sheets, database, baseline=HAND_BASELINE, log=lambda *_: None)
    assert database.read_bytes() == before
    assert not (tmp_path / "retail.db.building").exists()
