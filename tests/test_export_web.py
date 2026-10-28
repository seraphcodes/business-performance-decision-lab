"""Tests for src/export_web.py using the hand-worked fixture (net 93.63)."""
import json

import pandas as pd
import pytest

from src.build_db import build_from_sheets
from src.export_web import build_payload, verify, write
from src.reconcile import ReconciliationError


@pytest.fixture
def payload(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    return build_payload(database, docs_dir=tmp_path)


def test_payload_has_every_section_and_hand_values(payload):
    assert set(payload) == {"meta", "kpis", "monthly", "services", "products", "countries",
                            "coverage", "bridge", "docs"}
    assert round(payload["kpis"]["net_product_revenue"], 2) == 93.63
    months = {row["year_month"]: row for row in payload["monthly"]}
    assert round(months["2011-03"]["net_product_revenue"], 2) == 26.13
    assert months["2011-12"]["is_partial_month"] == 1
    assert [row["stock_code"] for row in payload["products"][:3]] == ["22423", "85123A", "DCGS0076"]
    assert all(check["passed"] for check in payload["meta"]["export_checks"])


def test_written_files_are_valid_and_match(payload, tmp_path):
    path = write(payload, tmp_path / "web")
    as_json = json.loads((tmp_path / "web" / "metrics.json").read_text(encoding="utf-8"))
    as_js = path.read_text(encoding="utf-8")
    assert as_js.startswith("window.METRICS = ") and as_js.rstrip().endswith(";")
    assert json.loads(as_js[len("window.METRICS = "):].rstrip().rstrip(";")) == as_json


def test_export_refuses_when_views_do_not_tie_to_the_bridge(sheets, tmp_path):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    from src import metrics
    monthly = metrics.monthly_revenue(database, include_partial=True)
    countries = metrics.country_revenue(database)
    products = metrics.read_view("SELECT * FROM v_top_products", database)
    bridge = metrics.read_view("SELECT step, label, rows, value FROM reconciliation", database)
    verify(monthly, countries, products, bridge)  # consistent data passes
    broken = monthly.copy()
    broken.loc[0, "net_product_revenue"] += 1.00
    with pytest.raises(ReconciliationError, match="monthly net"):
        verify(broken, countries, products, bridge)
