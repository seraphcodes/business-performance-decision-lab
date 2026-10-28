"""Shared test data builders: a tiny two-sheet workbook worked out by hand.

Raw column names are used on purpose (Invoice, Price, Customer ID) because that
is what the real workbook has. Hand-calculated totals, row by row:

Sheet "Year 2009-2010" (6 rows)                                        value
  r1  100001 85123A  qty 6  x 2.50  normal sale                        15.00
  r2  100001 22423   qty 2  x 10.00 normal sale                        20.00
  r3  100002 85123A  qty 4  x 2.50  normal sale (also in sheet 2)      10.00
  r4  100002 POST    qty 1  x 18.00 postage (also in sheet 2)          18.00
  r5a 100003 22423   qty 1  x 10.00 normal sale (also in sheet 2)      10.00
  r5b 100003 22423   qty 1  x 10.00 identical second line (also in 2)  10.00
                                                     sheet 1 total     83.00

Sheet "Year 2010-2011" (15 rows)
  copies of r3, r4, r5a, r5b = 4 overlap rows                          48.00
  r6  200001 85123A  qty 3  x 2.50, no customer, normal sale            7.50
  r7  200001 85123A  identical to r6 -> within-sheet repeat             7.50
  r8  C200002 85123A qty -2 x 2.50 credit note -> cancellation         -5.00
  r9  200003 AMAZONFEE qty -1 x 100 -> service/fee (beats qty < 0)   -100.00
  r10 200004 DCGS0076 qty 1 x 16.13 -> product (accepted code family)  16.13
  r11 200005 21730 no description, qty 5, price 0 -> zero_price         0.00
  r12 200006 85123A qty -7 price 0, non-C -> negative_qty_non_cancel    0.00
  r13 A200007 B "Adjust bad debt" qty 1 x -50 -> service/fee          -50.00
  r14 200008 C3 no description, qty 1, price 0 -> unknown_code          0.00
  r15 200009 22423 qty 1 x -5.00 -> negative_price                     -5.00
  r16 200010 85123A qty 1 x 2.50 on 2011-12-05 -> normal, partial month 2.50
                                                     sheet 2 total    -78.37
                                                     (48.00 + -126.37)

Raw total (A) = 83.00 + (-78.37) = 4.63     21 rows
Overlap copies (B) = 4 rows, 48.00          Deduplicated total (C) = -43.37
"""
import pandas as pd
NAN = float("nan")
UK = "United Kingdom"


def raw_row(invoice, code, description, quantity, when, price, customer, country=UK):
    return {"Invoice": invoice, "StockCode": code, "Description": description,
            "Quantity": quantity, "InvoiceDate": pd.Timestamp(when),
            "Price": price, "Customer ID": customer, "Country": country}


def _sheet_1():
    r3 = raw_row("100002", "85123A", "WHITE HEART", 4, "2010-12-02 09:00", 2.50, 12346.0)
    r4 = raw_row("100002", "POST", "POSTAGE", 1, "2010-12-02 09:00", 18.00, 12346.0)
    r5 = raw_row("100003", "22423", "CAKESTAND", 1, "2010-12-03 11:00", 10.00, 12347.0)
    return [
        raw_row("100001", "85123A", "WHITE HEART", 6, "2010-11-30 10:00", 2.50, 12345.0),
        raw_row("100001", "22423", "CAKESTAND", 2, "2010-11-30 10:00", 10.00, 12345.0),
        r3, r4, r5, dict(r5),
    ], (r3, r4, r5)


def _sheet_2(copies):
    r3, r4, r5 = copies
    r6 = raw_row("200001", "85123A", "WHITE HEART", 3, "2011-03-01 10:00", 2.50, NAN)
    return [
        dict(r3), dict(r4), dict(r5), dict(r5),  # the four overlap copies
        r6, dict(r6),
        raw_row("C200002", "85123A", "WHITE HEART", -2, "2011-03-05 12:00", 2.50, 12345.0),
        raw_row("200003", "AMAZONFEE", "AMAZON FEE", -1, "2011-03-06 08:00", 100.00, NAN),
        raw_row("200004", "DCGS0076", "SUNJAR LED NIGHT NIGHT LIGHT", 1, "2011-03-07 09:00", 16.13, 12348.0),
        raw_row("200005", "21730", None, 5, "2011-03-08 09:00", 0.0, NAN),
        raw_row("200006", "85123A", "damaged", -7, "2011-03-09 09:00", 0.0, NAN),
        raw_row("A200007", "B", "Adjust bad debt", 1, "2011-03-10 09:00", -50.0, NAN),
        raw_row("200008", "C3", None, 1, "2011-03-11 09:00", 0.0, NAN),
        raw_row("200009", "22423", "CAKESTAND", 1, "2011-03-12 09:00", -5.0, 12349.0),
        raw_row("200010", "85123A", "WHITE HEART", 1, "2011-12-05 09:00", 2.50, 12345.0),
    ]


def build_sheets():
    """The hand-built workbook as {sheet name: DataFrame}."""
    first, copies = _sheet_1()
    return {"Year 2009-2010": pd.DataFrame(first),
            "Year 2010-2011": pd.DataFrame(_sheet_2(copies))}


def single_row_frame(code, quantity, price, invoice="500001", description="ITEM"):
    """A one-row, one-sheet workbook for testing a single classification rule."""
    return {"Sheet": pd.DataFrame([raw_row(invoice, code, description, quantity,
                                           "2011-05-05 10:00", price, 1.0)])}
