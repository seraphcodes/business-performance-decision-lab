"""Tests for src/reconcile.py, using the hand-worked totals in tests/helpers.py."""
import pytest

from src.reconcile import ReconciliationError, bridge, headline_metrics, require, verify


def test_bridge_walks_from_raw_total_to_net_revenue(classified):
    table = bridge(classified).set_index("label")["value"]
    assert table["Raw total, every row of both sheets"] == 4.63
    assert table["less: sheet-overlap copies"] == -48.00
    assert table["= Deduplicated total (A + B)"] == -43.37
    assert table["  sum of categories"] == -43.37  # categories explain every pound
    assert table["Gross product sales (normal_sale)"] == 98.63
    assert table["Cancellation value (cancellation)"] == -5.00
    assert table["Net product revenue (M1 + M2)"] == 93.63


def test_headline_metrics(classified):
    metrics = headline_metrics(classified)
    assert round(metrics["gross_product_sales"], 2) == 98.63
    assert round(metrics["cancellation_value"], 2) == -5.00
    assert round(metrics["net_product_revenue"], 2) == 93.63
    assert round(metrics["cancellation_pct_of_gross"], 4) == round(5 / 98.63, 4)  # 5.07%


def test_all_checks_pass_on_consistent_data(classified):
    assert all(check.passed for check in verify(classified))


def test_a_matching_baseline_passes(classified):
    baseline = {"rows": 21, "raw_total": 4.63, "overlap_rows": 4, "overlap_value": 48.00,
                "deduplicated_total": -43.37, "within_sheet_repeat_rows": 2}
    assert all(check.passed for check in verify(classified, baseline))


def test_a_wrong_baseline_is_reported_and_blocks_the_build(classified):
    baseline = {"rows": 22, "raw_total": 4.63}  # row count deliberately wrong
    failed = [check for check in verify(classified, baseline) if not check.passed]
    assert [check.name for check in failed] == ["Baseline: rows"]
    with pytest.raises(ReconciliationError, match="Baseline: rows"):
        require(classified, baseline)


def test_an_unclassified_row_fails_the_check(classified):
    broken = classified.copy()
    broken.loc[0, "RowClass"] = "other_unclassified"
    failed = [check.name for check in verify(broken) if not check.passed]
    assert "No row is unclassified" in failed


def test_a_tampered_value_breaks_the_reconciliation(classified):
    broken = classified.copy()
    broken.loc[broken["RowClass"] == "normal_sale", "LineValue"] += 0.01
    # category totals still add up to the (changed) total, but the baseline notices
    baseline = {"raw_total": 4.63}
    assert not all(check.passed for check in verify(broken, baseline))
