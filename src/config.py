"""Settings and rule tables for the retail data pipeline.

Every rule below is explained, with the evidence behind it, in
docs/cleaning_rules.md. If you change a rule here, change that file too and
re-run the tests.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_WORKBOOK = PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx"
DATABASE = PROJECT_ROOT / "data" / "processed" / "retail.db"
VIEWS_SQL = PROJECT_ROOT / "sql" / "views.sql"

# The workbook names three columns differently from the UCI web page.
RENAME = {"Invoice": "InvoiceNo", "Price": "UnitPrice", "Customer ID": "CustomerID"}
COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]

# ----------------------------------------------------------------------------
# Which stock codes are products?
# ----------------------------------------------------------------------------
# A normal product code is 5 digits with optional letters (85123A). Three more
# families are accepted because the workbook shows product names and positive
# prices for them (see docs/cleaning_rules.md, rule 4): DCGS..., SP<digits>, PADS.
PRODUCT_CODE_PATTERNS = (
    r"\d{5}[A-Z]{0,3}",
    r"DCGS.*",
    r"SP\d+",
    r"PADS",
)
PRODUCT_CODE_REGEX = "^(?:" + "|".join(PRODUCT_CODE_PATTERNS) + ")$"

# Codes that are services, fees or bookkeeping, not products. The meaning of
# each was checked against the most common Description in the real workbook.
SERVICE_CODES = {
    "POST": "postage_carriage", "DOT": "postage_carriage",
    "C2": "postage_carriage", "CARRIAGE": "postage_carriage",
    "M": "manual",
    "ADJUST": "adjustment", "ADJUST2": "adjustment", "B": "adjustment",
    "D": "discount",
    "S": "sample",
    "BANK CHARGES": "fee", "AMAZONFEE": "fee", "CRUK": "fee",
    "TEST001": "test", "TEST002": "test",
}
GIFT_VOUCHER_PREFIX = "GIFT_"  # gift_0001_20 and similar

# ----------------------------------------------------------------------------
# Row categories. Every row gets exactly one; the first match wins, so the
# order below IS the rule priority.
# ----------------------------------------------------------------------------
CLASS_INFO = {
    "sheet_overlap_copy": (
        "Sheet-2 row with an exact twin (all 8 fields) in sheet 1.",
        "Excluded from all metrics: the same transaction exported twice.",
    ),
    "service_or_fee": (
        "StockCode is a service/fee code (postage, fees, manual, discount...).",
        "Kept and reported separately; never counted as product revenue.",
    ),
    "unknown_code": (
        "StockCode is neither a product pattern nor a known service code.",
        "Excluded from sales and reported (currently only zero-value rows).",
    ),
    "cancellation": (
        "Product line on an invoice starting with 'C' (credit note).",
        "Kept; reported as cancellations/returns and netted into net product revenue.",
    ),
    "negative_qty_non_cancel": (
        "Quantity < 0 on a non-'C' invoice (stock adjustments).",
        "Excluded from sales and units sold; kept visible.",
    ),
    "negative_price": (
        "Product line with UnitPrice < 0.",
        "Excluded from sales; reported separately.",
    ),
    "zero_price": (
        "Product line with UnitPrice = 0 and Quantity > 0 (free items).",
        "Excluded from sales; value is zero; counted separately.",
    ),
    "normal_sale": (
        "Quantity > 0, UnitPrice > 0, product-style code, non-'C' invoice.",
        "Basis of gross product sales.",
    ),
    "other_unclassified": (
        "Anything else (for example Quantity = 0).",
        "Should be empty; the build fails the reconciliation check if it is not.",
    ),
}
CLASS_ORDER = list(CLASS_INFO)
ASSIGNABLE_CLASSES = CLASS_ORDER[:-1]  # all but other_unclassified

# ----------------------------------------------------------------------------
# Numbers reproduced from the real workbook by tools/diagnose_workbook.py
# (evidence: docs/diagnostics/diagnostic_report.md, run on 2026-10-28).
# build_db refuses to write the database if the real workbook disagrees.
# ----------------------------------------------------------------------------
EXPECTED_BASELINE = {
    "rows": 1_067_371,
    "raw_total": 19_287_250.57,
    "overlap_rows": 22_523,
    "overlap_value": 377_488.45,
    "deduplicated_total": 18_909_762.12,
    "within_sheet_repeat_rows": 11_812,
}
