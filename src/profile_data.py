"""Step 1 of the data work: LOOK at the raw file before cleaning anything.

Run from the project folder:  python src/profile_data.py
It prints a short report and also saves it to docs/raw_data_profile.txt
"""
import sys
from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/raw/online_retail_II.xlsx")
REPORT_FILE = Path("docs/raw_data_profile.txt")

lines = []


def say(text=""):
    """Print a line and remember it so we can save the whole report."""
    print(text)
    lines.append(str(text))


if not RAW_FILE.exists():
    sys.exit(f"File not found: {RAW_FILE}. Put the downloaded file there first.")

# sheet_name=None means: read EVERY sheet and give me a dict {sheet name: table}
say("Reading the Excel file (this can take 1-3 minutes)...")
sheets = pd.read_excel(RAW_FILE, sheet_name=None)

for name, table in sheets.items():
    say(f"Sheet '{name}': {table.shape[0]:,} rows, {table.shape[1]} columns")

# Stack the sheets into one table (the two sheets are two time periods)
df = pd.concat(sheets.values(), ignore_index=True)

say()
say("Columns and types as pandas read them:")
say(df.dtypes.to_string())

# The UCI page and the Excel file may name columns slightly differently,
# so we map both spellings to one set of names.
df = df.rename(columns={
    "Invoice": "InvoiceNo",
    "Price": "UnitPrice",
    "Customer ID": "CustomerID",
})

say()
say(f"Total rows: {len(df):,}")
say(f"Date range: {df['InvoiceDate'].min()}  ->  {df['InvoiceDate'].max()}")

say()
say("Missing values per column:")
say(df.isna().sum().to_string())
say(f"Rows without CustomerID: {df['CustomerID'].isna().mean():.1%}")

# Invoice numbers starting with 'C' are cancellations
invoice = df["InvoiceNo"].astype(str)
say()
say(f"Cancellation rows (InvoiceNo starts with C): {invoice.str.startswith('C').sum():,}")
say(f"Rows with Quantity <= 0: {(df['Quantity'] <= 0).sum():,}")
say(f"Rows with UnitPrice <= 0: {(df['UnitPrice'] <= 0).sum():,}")
say(f"Exact duplicate rows: {df.duplicated().sum():,}")

# Normal product codes start with a digit (e.g. 85123A). Others look like fees.
code = df["StockCode"].astype(str)
odd = df[~code.str.match(r"^\d")]
say()
say(f"Rows with non-product-looking StockCode: {len(odd):,}")
say("Most common of those codes:")
say(odd["StockCode"].astype(str).value_counts().head(10).to_string())

say()
say("Revenue check (Quantity x UnitPrice), all rows including cancellations:")
say(f"{(df['Quantity'] * df['UnitPrice']).sum():,.2f}")

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
say()
say(f"Saved this report to {REPORT_FILE}")
