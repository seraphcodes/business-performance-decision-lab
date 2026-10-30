"""The published numbers must agree everywhere.

web/data/metrics.json is the export of the last verified build. The README and the docs quote
its headline figures by hand, so these tests catch a document that was not updated (this is how
a stale cancellation figure once slipped through), and a website that embeds an old copy of a doc.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXPORT = json.loads((ROOT / "web" / "data" / "metrics.json").read_text(encoding="utf-8"))
STALE = "719,656.34"   # cancellation value of the M0 proposal, before rule 4 resolved the review codes


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def step(code):
    return next(row for row in EXPORT["bridge"] if row["step"] == code)


def test_export_headline_figures_equal_the_bridge():
    kpis = EXPORT["kpis"]
    for key, code in (("gross_product_sales", "M1"), ("cancellation_value", "M2"), ("net_product_revenue", "M3")):
        assert kpis[key] == pytest.approx(step(code)["value"], abs=0.005), key
    assert step("M1")["value"] + step("M2")["value"] == pytest.approx(step("M3")["value"], abs=0.005)


def test_readme_quotes_the_bridge_figures():
    readme = read("README.md")
    raw, net = step("A")["value"], step("M3")["value"]
    gross, canc = step("M1")["value"], step("M2")["value"]
    for text in (f"£{raw:,.2f}", f"£{net:,.2f}", f"£{gross:,.2f}", f"£{abs(canc):,.2f}",
                 f"£{abs(step('B')['value']):,.2f}", f"£{step('C')['value']:,.2f}"):
        assert text in readme, text


def test_cleaning_rules_quote_the_cancellation_rows_and_value():
    rules = read("docs/cleaning_rules.md")
    canc = step("M2")
    assert f"{canc['rows']:,} product rows, -£{abs(canc['value']):,.2f}" in rules


@pytest.mark.parametrize("path", ["README.md", "docs/cleaning_rules.md", "docs/metrics.md"])
def test_no_document_quotes_the_superseded_cancellation_figure(path):
    assert STALE not in read(path)


def test_website_embeds_the_current_docs():
    assert EXPORT["docs"]["cleaning_rules"] == read("docs/cleaning_rules.md")
    assert EXPORT["docs"]["metrics"] == read("docs/metrics.md")


def test_the_diagnostic_report_says_it_is_a_historical_snapshot():
    assert "Historical snapshot" in read("docs/diagnostics/diagnostic_report.md")
