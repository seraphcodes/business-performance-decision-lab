"""Step 2: flag duplicates and give every row exactly one category.

Nothing is deleted. Rows are labelled, so every excluded row stays visible and
the numbers can be reconciled back to the raw total.
"""
import numpy as np
import pandas as pd

from src.config import (
    ASSIGNABLE_CLASSES,
    GIFT_VOUCHER_PREFIX,
    PRODUCT_CODE_REGEX,
    SERVICE_CODES,
)

# The 8 original fields. Two rows are "identical" only if all 8 match.
_KEY = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]


def _key_frame(df):
    """The 8 identifying fields, where 'missing' counts as a real value.

    pandas treats NaN as never equal to NaN in some operations. Replacing
    missing values with a fixed marker makes 'missing equals missing', which is
    what we want when asking whether two rows are the same line.
    """
    key = pd.DataFrame({column: df[column].to_numpy() for column in _KEY if column not in
                        ("Description", "CustomerID")}, index=df.index)
    description = df["Description"].astype(object)
    key["Description"] = description.where(df["Description"].notna(), "<missing>").to_numpy()
    key["CustomerID"] = df["CustomerID"].astype(float).fillna(-1).to_numpy()
    key["SheetNo"] = df["SheetNo"].to_numpy()
    return key


def flag_sheet_overlap(df):
    """True for sheet-2 rows that are an exact copy of a sheet-1 row.

    The n-th occurrence of an identical row in sheet 1 is paired with the n-th
    occurrence in sheet 2. A line repeated 3 times in BOTH sheets therefore
    gives 3 overlap copies, while a line repeated inside one sheet only is
    never treated as overlap. A row whose twin differs in any field (for
    example a different quantity) is not a copy.
    """
    flags = pd.Series(False, index=df.index)
    sheet_numbers = sorted(df["SheetNo"].unique())
    if len(sheet_numbers) == 1:
        return flags
    if len(sheet_numbers) != 2:
        raise ValueError("This pipeline supports the 2-sheet layout of Online Retail II.")

    first, second = sheet_numbers
    key = _key_frame(df)
    key["_row"] = df.index
    key["_occurrence"] = key.groupby(["SheetNo"] + _KEY, sort=False).cumcount()
    columns = _KEY + ["_occurrence", "_row"]
    sheet_1 = key.loc[key["SheetNo"] == first, columns]
    sheet_2 = key.loc[key["SheetNo"] == second, columns]
    matches = sheet_1.merge(sheet_2, on=_KEY + ["_occurrence"], suffixes=("_1", "_2"))
    flags.loc[matches["_row_2"].to_numpy()] = True
    return flags


def flag_within_sheet_repeats(df, overlap_copy):
    """True for the 2nd, 3rd... copy of an identical line that is NOT overlap.

    These are flagged, not removed: a customer can legitimately order the same
    product twice on one invoice, and the data cannot prove otherwise.
    """
    key = _key_frame(df)
    remaining = key.loc[~overlap_copy.to_numpy()]
    repeated = remaining.duplicated(subset=_KEY, keep="first")
    flags = pd.Series(False, index=df.index)
    flags.loc[repeated.index[repeated]] = True
    return flags


def classify(df):
    """Add IsOverlapCopy, IsWithinSheetRepeat, ServiceType and RowClass."""
    out = df.copy()
    out["IsOverlapCopy"] = flag_sheet_overlap(out)
    out["IsWithinSheetRepeat"] = flag_within_sheet_repeats(out, out["IsOverlapCopy"])

    code = out["StockCode"].str.upper()
    service = code.map(SERVICE_CODES)
    service = service.mask(code.str.startswith(GIFT_VOUCHER_PREFIX), "gift_voucher")
    out["ServiceType"] = service

    is_product = code.str.match(PRODUCT_CODE_REGEX)
    is_credit_note = out["InvoiceNo"].str.startswith("C")
    quantity, price = out["Quantity"], out["UnitPrice"]

    # Order matters: the first condition that is true decides the category.
    conditions = [
        out["IsOverlapCopy"],
        service.notna(),
        ~is_product,
        is_credit_note,
        quantity < 0,
        price < 0,
        price == 0,
        (quantity > 0) & (price > 0),
    ]
    out["RowClass"] = np.select(conditions, ASSIGNABLE_CLASSES, default="other_unclassified")
    return out


def add_time_columns(df):
    """Give every line of an invoice the invoice's FIRST timestamp.

    83 invoices in the real data carry more than one timestamp. Using the
    earliest keeps each invoice in a single day and month. The last month of
    the dataset is flagged as partial if the data ends before the month does
    (the real data ends on 9 Dec 2011).
    """
    out = df.copy()
    first = out.groupby("InvoiceNo")["InvoiceDate"].transform("min")
    out["InvoiceTimestamp"] = first
    out["InvoiceDay"] = first.dt.strftime("%Y-%m-%d")
    out["YearMonth"] = first.dt.strftime("%Y-%m")
    last = out["InvoiceDate"].max()
    ends_early = last.day < last.days_in_month
    out["IsPartialMonth"] = ends_early & (out["YearMonth"] == last.strftime("%Y-%m"))
    return out
