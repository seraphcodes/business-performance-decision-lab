"""Tests for src/classify.py: overlap, repeats, categories, time columns.

Expected values come from the hand-worked table at the top of tests/helpers.py.
"""
import pandas as pd
import pytest

from src.classify import add_time_columns, classify
from src.load import prepare
from tests.helpers import raw_row, single_row_frame


# --------------------------------------------------------------- overlap
def test_exactly_the_four_sheet_2_twins_are_overlap_copies(classified):
    copies = classified[classified["IsOverlapCopy"]]
    assert len(copies) == 4
    assert set(copies["SheetNo"]) == {2}
    assert round(copies["LineValue"].sum(), 2) == 48.00


def test_line_repeated_in_both_sheets_is_overlap_not_a_repeat(classified):
    # r5a and r5b are identical lines in BOTH sheets: both sheet-2 twins are
    # overlap copies (2 matches), not "duplicates" of each other.
    twins = classified[(classified["InvoiceNo"] == "100003") & (classified["SheetNo"] == 2)]
    assert twins["IsOverlapCopy"].tolist() == [True, True]


def test_a_twin_with_a_different_quantity_is_not_an_overlap_copy():
    base = dict(code="85123A", description="WHITE HEART", price=2.5)
    one = raw_row("700001", base["code"], base["description"], 4, "2010-12-02 09:00", 2.5, 1.0)
    two = dict(one)
    two["Quantity"] = 5  # one field differs
    sheets = {"A": pd.DataFrame([one]), "B": pd.DataFrame([two])}
    assert not classify(prepare(sheets))["IsOverlapCopy"].any()


def test_missing_description_in_both_sheets_still_matches():
    row = raw_row("700002", "21730", None, 1, "2010-12-02 09:00", 0.0, float("nan"))
    sheets = {"A": pd.DataFrame([row]), "B": pd.DataFrame([dict(row)])}
    assert classify(prepare(sheets))["IsOverlapCopy"].tolist() == [False, True]


@pytest.mark.parametrize("description, customer", [("WHITE HEART", 1.0), (None, float("nan"))])
def test_extra_copies_in_sheet_2_beyond_sheet_1_are_repeats_not_overlap(description, customer):
    # The line exists ONCE in sheet 1 and THREE times in sheet 2. Pairing is
    # occurrence by occurrence, so only the first sheet-2 line is an overlap
    # copy. The other two are extra identical lines (repeats), whether or not
    # the Description and Customer ID are missing.
    row = raw_row("700003", "85123A", description, 2, "2010-12-02 09:00", 2.5, customer)
    sheets = {"A": pd.DataFrame([row]), "B": pd.DataFrame([row, dict(row), dict(row)])}
    result = classify(prepare(sheets))
    assert result["IsOverlapCopy"].sum() == 1
    assert result["IsWithinSheetRepeat"].sum() == 2


def test_single_sheet_has_no_overlap():
    result = classify(prepare(single_row_frame("85123A", 1, 2.0)))
    assert not result["IsOverlapCopy"].any()


# --------------------------------------------------------------- repeats
def test_within_sheet_repeats_are_flagged_not_removed(classified):
    # r5b repeats r5a inside sheet 1 (10.00); r7 repeats r6 inside sheet 2 (7.50).
    repeats = classified[classified["IsWithinSheetRepeat"]]
    assert len(repeats) == 2
    assert round(repeats["LineValue"].sum(), 2) == 17.50
    assert len(classified) == 21  # nothing was dropped


# ------------------------------------------------------------ categories
def test_every_category_count_and_value(classified):
    summary = classified.groupby("RowClass")["LineValue"].agg(["size", "sum"])
    expected = {  # category: (rows, value) worked out by hand
        "sheet_overlap_copy": (4, 48.00),
        "service_or_fee": (3, -132.00),       # POST 18 + AMAZONFEE -100 + B -50
        "unknown_code": (1, 0.00),            # C3
        "cancellation": (1, -5.00),           # r8
        "negative_qty_non_cancel": (1, 0.00),  # r12
        "negative_price": (1, -5.00),         # r15
        "zero_price": (1, 0.00),              # r11
        "normal_sale": (9, 98.63),            # 65.00 + 7.50 + 7.50 + 16.13 + 2.50
    }
    assert set(summary.index) == set(expected)
    for name, (rows, value) in expected.items():
        assert summary.loc[name, "size"] == rows, name
        assert round(summary.loc[name, "sum"], 2) == value, name


@pytest.mark.parametrize("code, quantity, price, invoice, expected", [
    ("85123A", 2, 1.0, "500001", "normal_sale"),
    ("85123a", 2, 1.0, "500001", "normal_sale"),         # lower-case letter
    ("15056BL", 1, 3.0, "500001", "normal_sale"),        # two-letter suffix
    ("DCGS0058", 1, 0.95, "500001", "normal_sale"),      # accepted code family
    ("DCGSSGIRL", 1, 3.36, "500001", "normal_sale"),
    ("SP1002", 1, 2.95, "500001", "normal_sale"),
    ("PADS", 1, 36.6, "500001", "normal_sale"),
    ("POST", 1, 18.0, "500001", "service_or_fee"),
    ("m", 1, 5.0, "500001", "service_or_fee"),           # lower-case service code
    ("gift_0001_20", 1, 20.0, "500001", "service_or_fee"),
    ("AMAZONFEE", -1, 100.0, "500001", "service_or_fee"),  # beats Quantity < 0
    ("POST", 1, 18.0, "C500007", "service_or_fee"),      # beats credit note
    ("C3", 1, 0.0, "500001", "unknown_code"),
    ("GIFT", 1, 0.0, "500001", "unknown_code"),
    ("85123A", -2, 2.5, "C500002", "cancellation"),
    ("DCGS0058", -1, 0.95, "C500003", "cancellation"),
    ("85123A", -7, 0.0, "500004", "negative_qty_non_cancel"),
    ("85123A", 1, -5.0, "500005", "negative_price"),
    ("85123A", 5, 0.0, "500006", "zero_price"),
    ("85123A", 0, 2.0, "500008", "other_unclassified"),  # nothing matches
])
def test_single_row_category(code, quantity, price, invoice, expected):
    frame = single_row_frame(code, quantity, price, invoice)
    assert classify(prepare(frame))["RowClass"].iloc[0] == expected


def test_service_types(classified):
    types = classified.loc[classified["RowClass"] == "service_or_fee"].set_index("StockCode")
    assert types.loc["POST", "ServiceType"] == "postage_carriage"
    assert types.loc["AMAZONFEE", "ServiceType"] == "fee"
    assert types.loc["B", "ServiceType"] == "adjustment"


def test_flags_for_missing_description_and_customer(classified):
    assert classified["MissingDescription"].sum() == 2   # r11, r14
    assert classified["MissingCustomer"].sum() == 7      # r6, r7, r9, r11, r12, r13, r14


# ------------------------------------------------------------------ time
def test_invoice_uses_its_first_timestamp():
    early = raw_row("800001", "85123A", "X", 1, "2011-05-31 23:58", 1.0, 1.0)
    late = raw_row("800001", "22423", "Y", 1, "2011-06-01 00:02", 1.0, 1.0)
    result = add_time_columns(classify(prepare({"S": pd.DataFrame([early, late])})))
    assert set(result["YearMonth"]) == {"2011-05"}
    assert set(result["InvoiceDay"]) == {"2011-05-31"}


def test_only_the_dataset_final_partial_month_is_flagged(classified):
    partial = classified[classified["IsPartialMonth"]]
    assert partial["YearMonth"].unique().tolist() == ["2011-12"]
    assert len(partial) == 1  # r16, the only line in Dec 2011
    assert classified.loc[classified["InvoiceNo"] == "100003", "YearMonth"].eq("2010-12").all()


def test_last_month_is_not_partial_if_data_reaches_month_end():
    row = raw_row("900001", "85123A", "X", 1, "2011-12-31 10:00", 1.0, 1.0)
    result = add_time_columns(classify(prepare({"S": pd.DataFrame([row])})))
    assert not result["IsPartialMonth"].any()
