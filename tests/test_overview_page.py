"""Smoke test: the Overview page renders from a real (tiny) database without errors."""
from pathlib import Path

import pytest

from src.build_db import build_from_sheets

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
PAGE = str(Path(__file__).resolve().parent.parent / "pages" / "1_Overview.py")


def test_overview_renders_with_hand_values(sheets, tmp_path, monkeypatch):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    monkeypatch.setenv("RETAIL_DB", str(database))
    app = streamlit_testing.AppTest.from_file(PAGE, default_timeout=30).run()
    assert not app.exception
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Net product revenue"] == "£93.63"
    assert values["Orders (invoices)"] == "6"
    assert values["Average order value (gross)"] == "£16.44"


def test_overview_explains_a_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIL_DB", str(tmp_path / "missing.db"))
    app = streamlit_testing.AppTest.from_file(PAGE, default_timeout=30).run()
    assert not app.exception
    assert "build_db" in app.error[0].value


METHODOLOGY = str(Path(__file__).resolve().parent.parent / "pages" / "3_Methodology.py")


def test_methodology_shows_the_live_reconciliation(sheets, tmp_path, monkeypatch):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    monkeypatch.setenv("RETAIL_DB", str(database))
    app = streamlit_testing.AppTest.from_file(METHODOLOGY, default_timeout=30).run()
    assert not app.exception
    shown = app.dataframe[0].value
    assert "£93.63" in shown["Value"].tolist()  # net product revenue from the hand-worked fixture
    assert any("Label, never delete" in block.value or "label, never delete" in block.value.lower()
               for block in app.markdown)


def test_methodology_survives_a_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIL_DB", str(tmp_path / "missing.db"))
    app = streamlit_testing.AppTest.from_file(METHODOLOGY, default_timeout=30).run()
    assert not app.exception
    assert app.warning


SIMULATOR = str(Path(__file__).resolve().parent.parent / "pages" / "2_What_If_Simulator.py")


def test_simulator_renders_and_labels_assumptions(sheets, tmp_path, monkeypatch):
    # The 21-row fixture has only 3 full months (Nov 2010, Dec 2010, Mar 2011): net 35 + 30 + 26.13.
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    monkeypatch.setenv("RETAIL_DB", str(database))
    app = streamlit_testing.AppTest.from_file(SIMULATOR, default_timeout=30).run()
    assert not app.exception
    assert any("not a forecast" in warning.value for warning in app.warning)
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Net revenue, scenario"].startswith("£")
    app.slider[0].set_value(0).run()   # price change 0 (volume already 0)
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Change in profit (assumed cost)"] == "£0.00"


def test_simulator_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIL_DB", str(tmp_path / "missing.db"))
    app = streamlit_testing.AppTest.from_file(SIMULATOR, default_timeout=30).run()
    assert not app.exception
    assert "build_db" in app.error[0].value


def test_methodology_warns_that_the_default_chart_axis_is_zoomed(sheets, tmp_path, monkeypatch):
    database = tmp_path / "retail.db"
    build_from_sheets(sheets, database, baseline=None, log=lambda *_: None)
    monkeypatch.setenv("RETAIL_DB", str(database))
    app = streamlit_testing.AppTest.from_file(METHODOLOGY, default_timeout=30).run()
    assert not app.exception
    assert any("Zoomed view" in warning.value and "not £0" in warning.value for warning in app.warning)
    app.toggle[0].set_value(True).run()   # full-scale view
    assert not app.exception
    assert not any("Zoomed view" in warning.value for warning in app.warning)
    assert any("Full-scale view" in caption.value for caption in app.caption)
