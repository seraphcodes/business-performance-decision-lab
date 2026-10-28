"""Step 1: read the original workbook and put it in one tidy table.

Nothing is removed or changed here except naming and types. The original file
is only ever opened for reading.
"""
import numpy as np
import pandas as pd

from src.config import COLUMNS, RENAME


def read_workbook(path):
    """Return {sheet name: table} exactly as stored in the Excel file."""
    return pd.read_excel(path, sheet_name=None)


def prepare(sheets):
    """Stack all sheets into one table with consistent column names.

    Adds bookkeeping columns so every later number can be traced back:
      SheetNo, Sheet, ExcelRow  where the row came from (ExcelRow is the row
                                number you would see in Excel, header = row 1)
      RowId                     unique number, 0..n-1, in file order
      LineValue                 Quantity x UnitPrice
      MissingDescription / MissingCustomer   simple flags
    """
    if not sheets:
        raise ValueError("The workbook contains no sheets.")

    frames = []
    for number, (name, table) in enumerate(sheets.items(), start=1):
        table = table.rename(columns=RENAME)
        missing = [column for column in COLUMNS if column not in table.columns]
        if missing:
            raise ValueError(f"Sheet '{name}' is missing expected columns: {missing}")
        table = table[COLUMNS].copy()
        table["SheetNo"] = number
        table["Sheet"] = name
        table["ExcelRow"] = np.arange(2, len(table) + 2)
        frames.append(table)

    df = pd.concat(frames, ignore_index=True)
    df["RowId"] = np.arange(len(df))
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["UnitPrice"] = df["UnitPrice"].astype(float)
    df["CustomerID"] = df["CustomerID"].astype(float)
    df["LineValue"] = df["Quantity"].astype(float) * df["UnitPrice"]
    df["MissingDescription"] = df["Description"].isna()
    df["MissingCustomer"] = df["CustomerID"].isna()
    return df
