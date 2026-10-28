#!/usr/bin/env python
"""
diagnose_workbook.py - READ-ONLY diagnostics for the Online Retail II workbook.

What it does
  * Opens the workbook for reading only and proves it was not touched by
    comparing a SHA-256 fingerprint before and after.
  * Measures each sheet, finds rows that appear in BOTH sheets, and separates
    them from repeated lines that exist inside a single sheet.
  * Puts every row into exactly one PROPOSED category and shows rows, units and
    value per category.
  * Builds a revenue bridge from the raw total down to proposed net product
    revenue, so no excluded row is hidden.
  * Writes a compact report and a few small CSV samples to an output folder.

What it does NOT do
  * It deletes and changes nothing. Categories are proposals for us to review.
  * It needs only pandas, numpy and openpyxl (already in requirements.txt).

Run (from any folder):
    python diagnose_workbook.py "C:\\path\\to\\online_retail_II.xlsx" --out diagnostics

Reading the Excel file takes a few minutes. Share diagnostic_report.md and, if
asked, the small CSV files. Never share the workbook itself.
"""
import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Settings you may edit. Everything here is a PROPOSAL, not a fact.
# ----------------------------------------------------------------------------
PROVISIONAL_BASELINE = 19_287_250.57  # raw total from the earlier profile run

RENAME = {"Invoice": "InvoiceNo", "Price": "UnitPrice", "Customer ID": "CustomerID"}
COLS = ["InvoiceNo", "StockCode", "Description", "Quantity",
        "InvoiceDate", "UnitPrice", "CustomerID", "Country"]

# A normal product code: 5 digits, optionally followed by letters (85123A).
PRODUCT_CODE = r"^\d{5}[A-Z]{0,3}$"

# Codes that look like services, fees or bookkeeping rather than products.
# The report prints the most common Description for each code, so the meaning
# is checked against the data and not assumed.
SERVICE_CODES = {
    "POST": "postage_carriage", "DOT": "postage_carriage",
    "C2": "postage_carriage", "CARRIAGE": "postage_carriage",
    "M": "manual", "ADJUST": "adjustment", "ADJUST2": "adjustment",
    "B": "adjustment", "D": "discount", "S": "sample",
    "BANK CHARGES": "fee", "AMAZONFEE": "fee", "CRUK": "fee",
    "TEST001": "test", "TEST002": "test",
}

CLASS_DEFS = {
    "sheet_overlap_copy": "Sheet-2 row with an exact twin (all 8 fields) in sheet 1. "
                          "Proposed: exclude (same transaction exported twice).",
    "service_or_fee": "StockCode is in SERVICE_CODES (postage, fees, manual, discount...). "
                      "Proposed: keep, report separately, never count as product revenue.",
    "review_code": "StockCode is not 5 digits(+letters) and not in SERVICE_CODES. "
                   "Needs a human decision (see review_codes.csv).",
    "cancellation": "Product line on an invoice starting with 'C' (credit note). "
                    "Proposed: keep, report separately as cancellations/returns.",
    "negative_qty_non_cancel": "Quantity < 0 on a non-'C' invoice (write-offs, damages, "
                               "corrections?). Proposed: keep, report separately, not sales.",
    "negative_price": "UnitPrice < 0 (bad-debt adjustments?). Proposed: not sales, report separately.",
    "zero_price": "UnitPrice = 0 and Quantity > 0 (free items, samples, lost stock?). "
                  "Value is 0. Proposed: not sales, count separately.",
    "normal_sale": "Quantity > 0, UnitPrice > 0, product-style code, non-'C' invoice. "
                   "Basis for gross product sales.",
    "other_unclassified": "Anything else. Should be empty.",
}
CLASS_ORDER = list(CLASS_DEFS)

SAMPLE_N = 30  # max rows in any CSV sample

# ----------------------------------------------------------------------------
R = []  # report lines


def out(text=""):
    R.append(str(text))


def block(df):
    out("```text")
    out(df.to_string(index=False))
    out("```")


def gbp(x):
    return f"{x:,.2f}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fsum(series):
    return math.fsum(series.astype(float).tolist())


# ----------------------------------------------------------------------------
def load(path):
    sheets = pd.read_excel(path, sheet_name=None)  # read-only: pandas never writes
    frames = []
    for no, (name, t) in enumerate(sheets.items(), start=1):
        t = t.rename(columns=RENAME)
        missing = [c for c in COLS if c not in t.columns]
        if missing:
            sys.exit(f"Sheet '{name}' is missing expected columns: {missing}")
        t = t[COLS].copy()
        t["SheetNo"] = no
        t["Sheet"] = name
        t["ExcelRow"] = np.arange(2, len(t) + 2)  # row number as seen in Excel
        frames.append(t)
    df = pd.concat(frames, ignore_index=True)
    df["RowId"] = np.arange(len(df))
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Line"] = df["Quantity"].astype(float) * df["UnitPrice"].astype(float)
    # Key columns where "missing" is a real value, so missing equals missing.
    df["K_Desc"] = df["Description"].astype(object).where(df["Description"].notna(), "<missing>")
    df["K_Cust"] = df["CustomerID"].astype(float).fillna(-1)
    return df, list(sheets.keys())


KEY = ["InvoiceNo", "StockCode", "K_Desc", "Quantity",
       "InvoiceDate", "UnitPrice", "K_Cust", "Country"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", help="path to online_retail_II.xlsx (opened read-only)")
    ap.add_argument("--out", default="diagnostics", help="folder for the report (default: diagnostics)")
    args = ap.parse_args()

    wb = Path(args.workbook).resolve()
    outdir = Path(args.out).resolve()
    if not wb.is_file():
        sys.exit(f"Workbook not found: {wb}")
    if outdir == wb.parent:
        sys.exit("Choose an output folder different from the workbook's folder.")
    outdir.mkdir(parents=True, exist_ok=True)

    hash_before = sha256(wb)
    print("Reading workbook (a few minutes)...")
    df, sheet_names = load(wb)
    print(f"Loaded {len(df):,} rows. Analysing...")

    raw_total = fsum(df["Line"])

    # ---------------------------------------------------------------- 1
    out("# Online Retail II - workbook diagnostic report")
    out()
    out("## 1. Provenance")
    out(f"- File: `{wb.name}`  ({wb.stat().st_size:,} bytes)")
    out(f"- SHA-256 before reading: `{hash_before}`")
    out(f"- Run at: {datetime.now().isoformat(timespec='seconds')}")
    out(f"- Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}")
    out(f"- Sheets found: {sheet_names}")

    # ---------------------------------------------------------------- 2
    df["Occ"] = df.groupby(["SheetNo"] + KEY, sort=False).cumcount()
    out()
    out("## 2. Per-sheet profile")
    rows = []
    for no, g in df.groupby("SheetNo"):
        rows.append({
            "sheet": g["Sheet"].iloc[0], "rows": len(g),
            "first_date": g["InvoiceDate"].min(), "last_date": g["InvoiceDate"].max(),
            "invoices": g["InvoiceNo"].nunique(),
            "extra_exact_copies_in_sheet": int((g["Occ"] > 0).sum()),
            "raw_value": gbp(fsum(g["Line"])),
        })
    block(pd.DataFrame(rows))
    out(f"Total rows: {len(df):,}.  Raw total (Quantity x UnitPrice, every row): **{gbp(raw_total)}**")
    diff = round(raw_total, 2) - PROVISIONAL_BASELINE
    out(f"Provisional baseline {gbp(PROVISIONAL_BASELINE)}: "
        + ("**reproduced exactly**" if abs(diff) < 0.005 else f"**DIFFERS by {gbp(diff)}**"))
    out()
    out("Invoice prefixes (first character not a digit):")
    pref = df.loc[~df["InvoiceNo"].str.match(r"^\d"), "InvoiceNo"].str[0].value_counts()
    out("```text")
    out(pref.to_string() if len(pref) else "(none)")
    out("```")

    # ---------------------------------------------------------------- 3 overlap
    out()
    out("## 3. Sheet overlap (is any transaction exported twice?)")
    df["OverlapCopy"] = False
    matched = pd.DataFrame()
    window = None
    if df["SheetNo"].nunique() == 2:
        s1, s2 = df[df.SheetNo == 1], df[df.SheetNo == 2]
        w_start, w_end = s2["InvoiceDate"].min(), s1["InvoiceDate"].max()
        if w_start <= w_end:
            window = (w_start, w_end)
        on = KEY + ["Occ"]
        # Match the n-th occurrence of an identical row in sheet 1 with the n-th
        # occurrence in sheet 2. A line repeated 3 times in BOTH sheets gives 3
        # matches (overlap). A line repeated 3 times in one sheet only gives 0.
        matched = s1[on + ["RowId", "ExcelRow"]].merge(
            s2[on + ["RowId", "ExcelRow"]], on=on, suffixes=("_s1", "_s2"))
        df.loc[df["RowId"].isin(matched["RowId_s2"]), "OverlapCopy"] = True
    else:
        out("Expected exactly 2 sheets; overlap test skipped.")

    n_copy = int(df["OverlapCopy"].sum())
    copy_value = fsum(df.loc[df.OverlapCopy, "Line"])
    if window:
        out(f"Date window where both sheets have data: {window[0]}  ->  {window[1]}")
        inw = df[(df.InvoiceDate >= window[0]) & (df.InvoiceDate <= window[1])]
        t = inw.groupby("Sheet").agg(rows=("RowId", "size"), invoices=("InvoiceNo", "nunique"),
                                     value=("Line", "sum")).reset_index()
        t["value"] = t["value"].map(gbp)
        out("Rows inside that window, per sheet:")
        block(t)
    else:
        out("The two sheets do not share a date window.")
    out(f"Rows in sheet 2 that have an exact twin in sheet 1: **{n_copy:,}** "
        f"(value {gbp(copy_value)}) = the amount the raw total double-counts.")
    if n_copy:
        md = df.loc[df.OverlapCopy, "InvoiceDate"]
        out(f"- Dates of those rows: {md.min()} -> {md.max()}")
        if window:
            outside = int(((md < window[0]) | (md > window[1])).sum())
            out(f"- Matched rows outside the shared window (should be 0): {outside:,}")
            w2 = df[(df.SheetNo == 2) & (df.InvoiceDate >= window[0]) & (df.InvoiceDate <= window[1])]
            w1 = df[(df.SheetNo == 1) & (df.InvoiceDate >= window[0]) & (df.InvoiceDate <= window[1])]
            out(f"- Sheet-2 window rows with a twin: {int(w2.OverlapCopy.sum()):,} of {len(w2):,} "
                f"({w2.OverlapCopy.mean():.1%})")
            m1 = int(df.loc[df.RowId.isin(matched.RowId_s1), "RowId"].count())
            out(f"- Sheet-1 window rows with a twin: {m1:,} of {len(w1):,} ({m1 / max(len(w1), 1):.1%})")

        # invoice-level view
        a = df[df.SheetNo == 1].groupby("InvoiceNo").size().rename("n1")
        b = df[df.SheetNo == 2].groupby("InvoiceNo").size().rename("n2")
        mm = matched.groupby("InvoiceNo").size().rename("m")
        inv = pd.concat([a, b], axis=1, join="inner").join(mm).fillna({"m": 0})
        inv["m"] = inv["m"].astype(int)
        cat = np.select(
            [(inv.m == inv.n1) & (inv.m == inv.n2), (inv.m == inv.n2) & (inv.m < inv.n1),
             (inv.m == inv.n1) & (inv.m < inv.n2), inv.m == 0],
            ["identical_in_both", "sheet2_is_subset_of_sheet1", "sheet1_is_subset_of_sheet2",
             "same_invoice_no_but_no_matching_line"], default="partly_different")
        inv["category"] = cat
        out()
        out(f"Invoice numbers present in BOTH sheets: **{len(inv):,}**. How their lines compare:")
        block(inv["category"].value_counts().rename_axis("category").reset_index(name="invoices"))
        bad = inv[inv.category != "identical_in_both"].head(15).index
        if len(bad):
            ex = df[df.InvoiceNo.isin(bad)].sort_values(["InvoiceNo", "SheetNo", "ExcelRow"])
            ex.drop(columns=["K_Desc", "K_Cust", "Occ", "RowId", "Line"]).to_csv(
                outdir / "overlap_conflicts_sample.csv", index=False)
            out(f"Examples of non-identical shared invoices saved to overlap_conflicts_sample.csv "
                f"({len(bad)} invoices).")
    out()
    out("**How duplicates are told apart.** A row is called a *sheet-overlap copy* only if the same "
        "invoice line (all 8 fields) exists in sheet 1 AND sheet 2, matched occurrence by occurrence. "
        "A line that merely repeats inside one sheet is NOT treated as overlap; it is analysed in section 4.")

    # ---------------------------------------------------------------- 4 repeats
    out()
    out("## 4. Repeated identical lines inside one sheet (after removing overlap copies)")
    rest = df[~df.OverlapCopy].copy()
    rest["WithinRepeat"] = rest.duplicated(subset=KEY, keep="first")
    prev_same = (rest[KEY].shift(1) == rest[KEY]).all(axis=1)
    df["WithinRepeat"] = False
    df.loc[rest.index[rest.WithinRepeat], "WithinRepeat"] = True
    rep = rest[rest.WithinRepeat]
    out(f"- Extra identical lines: **{len(rep):,}** on {rep.InvoiceNo.nunique():,} invoices; "
        f"value of the extra copies {gbp(fsum(rep.Line))}")
    if len(rep):
        adj = int(prev_same[rep.index].sum())
        out(f"- Directly below an identical line in the file: {adj:,} ({adj / len(rep):.1%}). "
            f"Back-to-back copies hint at double entry; scattered ones are more often genuine repeat lines.")
        if window:
            inwin = ((rep.InvoiceDate >= window[0]) & (rep.InvoiceDate <= window[1])).mean()
            share_rows = ((rest.InvoiceDate >= window[0]) & (rest.InvoiceDate <= window[1])).mean()
            out(f"- Share of these repeats inside the overlap window: {inwin:.1%} "
                f"(window holds {share_rows:.1%} of all rows). Similar shares = not an overlap effect.")
        cls = rep.StockCode.str.upper().where(rep.StockCode.str.upper().str.match(PRODUCT_CODE), "non-product code")
        out("- Most affected stock codes:")
        block(cls.value_counts().head(8).rename_axis("stock_code").reset_index(name="extra_lines"))
        rep.head(SAMPLE_N).drop(columns=["K_Desc", "K_Cust", "Occ", "RowId", "Line"]).to_csv(
            outdir / "within_sheet_repeats_sample.csv", index=False)
    out("These cannot be proven to be errors from the data alone (a customer can legitimately order the "
        "same product twice on one invoice). They are therefore FLAGGED, not removed; the revenue bridge "
        "shows the effect of removing them as a sensitivity.")

    # ---------------------------------------------------------------- 5 classes
    code_up = df["StockCode"].str.upper()
    is_product = code_up.str.match(PRODUCT_CODE)
    svc = code_up.map(SERVICE_CODES)
    svc = svc.mask(code_up.str.startswith("GIFT_"), "gift_voucher")
    df["ServiceType"] = svc
    is_c = df["InvoiceNo"].str.startswith("C")
    conds = [df["OverlapCopy"], svc.notna(), ~is_product, is_c,
             df["Quantity"] < 0, df["UnitPrice"] < 0, df["UnitPrice"] == 0,
             (df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["RowClass"] = np.select(conds, CLASS_ORDER[:8], default="other_unclassified")

    out()
    out("## 5. Proposed row categories (each row in exactly one)")
    g = df.groupby("RowClass").agg(rows=("RowId", "size"), units=("Quantity", "sum"),
                                   value=("Line", "sum"), invoices=("InvoiceNo", "nunique"))
    g = g.reindex(CLASS_ORDER).fillna(0)
    g["pct_rows"] = (g["rows"] / len(df) * 100).round(2)
    tbl = g.reset_index()
    tbl["rows"] = tbl["rows"].astype(int)
    tbl["units"] = tbl["units"].astype(int)
    tbl["invoices"] = tbl["invoices"].astype(int)
    tbl["value"] = tbl["value"].map(gbp)
    block(tbl[["RowClass", "rows", "pct_rows", "units", "value", "invoices"]])
    tbl.to_csv(outdir / "class_summary.csv", index=False)
    out("Priority order (first match wins): " + " > ".join(CLASS_ORDER[:8]))
    out()
    out("Definitions and limitations:")
    for k, v in CLASS_DEFS.items():
        out(f"- `{k}`: {v}")

    out()
    out("Service/fee lines by type (evidence for the meaning of each code is in the next table):")
    sv = df[df.RowClass == "service_or_fee"]
    if len(sv):
        t = sv.groupby("ServiceType").agg(rows=("RowId", "size"), value=("Line", "sum")).reset_index()
        t["value"] = t["value"].map(gbp)
        block(t)
        desc = (sv.assign(D=sv.Description.fillna("<missing>").str.strip())
                  .groupby("StockCode").agg(rows=("RowId", "size"), value=("Line", "sum"),
                                            top_description=("D", lambda s: s.value_counts().index[0]))
                  .sort_values("rows", ascending=False).head(25).reset_index())
        desc["value"] = desc["value"].map(gbp)
        block(desc)

    rv = df[df.RowClass == "review_code"]
    out()
    out(f"Codes needing a human decision (review_code): {len(rv):,} rows, "
        f"{rv.StockCode.nunique():,} distinct codes, value {gbp(fsum(rv.Line))}. Top 40 in review_codes.csv.")
    if len(rv):
        r = (rv.assign(D=rv.Description.fillna("<missing>").str.strip())
               .groupby("StockCode").agg(rows=("RowId", "size"), value=("Line", "sum"),
                                         min_price=("UnitPrice", "min"), max_price=("UnitPrice", "max"),
                                         share_negative_qty=("Quantity", lambda s: (s < 0).mean()),
                                         top_description=("D", lambda s: s.value_counts().index[0]))
               .sort_values("rows", ascending=False).head(40).reset_index())
        r.to_csv(outdir / "review_codes.csv", index=False)
        show = r.head(12).copy()
        show["value"] = show["value"].map(gbp)
        show["share_negative_qty"] = show["share_negative_qty"].round(2)
        block(show)

    # ---------------------------------------------------------------- 6 bridge
    out()
    out("## 6. Revenue bridge (nothing hidden)")
    cv = {k: fsum(df.loc[df.RowClass == k, "Line"]) for k in CLASS_ORDER}
    dedup_total = raw_total - copy_value
    out("Formula for every line: `Line = Quantity x UnitPrice`.  Sums use exact float summation (math.fsum).")
    out("```text")
    out(f"A  Raw total, every row of both sheets                 {gbp(raw_total):>18}")
    out(f"B  less: sheet-overlap copies (sheet 2)                {gbp(-copy_value):>18}")
    out(f"C  = Deduplicated total (A + B)                        {gbp(dedup_total):>18}")
    out("   of which, by proposed category:")
    for k in CLASS_ORDER[1:]:
        out(f"     {k:<30} {gbp(cv[k]):>30}")
    classes_sum = math.fsum(cv[k] for k in CLASS_ORDER[1:])
    out(f"   sum of categories                                   {gbp(classes_sum):>18}")
    out("```")
    net_product = cv["normal_sale"] + cv["cancellation"]
    out("Proposed metric definitions (to be confirmed by us, not final):")
    out(f"- **Gross product sales** = sum of `normal_sale` lines = {gbp(cv['normal_sale'])}")
    out(f"- **Cancellation value** = sum of `cancellation` lines (negative) = {gbp(cv['cancellation'])}")
    out(f"- **Net product revenue** = gross product sales + cancellation value = {gbp(net_product)}")
    if cv["normal_sale"]:
        out(f"- Cancellation value as % of gross product sales: {-cv['cancellation'] / cv['normal_sale']:.2%}")
    out("- Not in any of the three: fees/services, review codes, write-offs (negative quantity), "
        "negative-price and zero-price lines. They stay visible in the table above.")
    ns = df[df.RowClass == "normal_sale"]
    if len(ns):
        nsr = ns[~ns.WithinRepeat]
        out(f"- Sensitivity: gross product sales if the flagged within-sheet repeats were also removed = "
            f"{gbp(fsum(nsr.Line))} (difference {gbp(fsum(ns.Line) - fsum(nsr.Line))}).")
        out(f"- `normal_sale` value with NO CustomerID: {gbp(fsum(ns[ns.CustomerID.isna()].Line))} "
            f"({fsum(ns[ns.CustomerID.isna()].Line) / max(fsum(ns.Line), 1):.1%}) - the part customer analytics cannot see.")

    # ---------------------------------------------------------------- 7 other checks
    out()
    out("## 7. Other data-quality checks")
    c_pos = int((is_c & (df.Quantity > 0)).sum())
    nc_neg = int((~is_c & (df.Quantity < 0)).sum())
    out(f"- 'C' invoice lines with Quantity > 0 (unexpected): {c_pos:,}")
    out(f"- Non-'C' lines with Quantity < 0: {nc_neg:,}")
    out(f"- Quantity = 0 lines: {int((df.Quantity == 0).sum()):,}")
    q = df[df.Quantity <= 0].copy()
    q["invoice_type"] = np.where(q.InvoiceNo.str.startswith("C"), "C (credit note)", "non-C")
    q["price"] = np.select([q.UnitPrice > 0, q.UnitPrice == 0], ["price > 0", "price = 0"], "price < 0")
    q["description"] = np.where(q.Description.isna(), "missing", "present")
    out("Rows with Quantity <= 0 broken down:")
    block(q.groupby(["invoice_type", "price", "description"]).size().rename("rows").reset_index())
    md = df[df.Description.isna()]
    out(f"- Missing Description: {len(md):,} rows; of them price = 0: {int((md.UnitPrice == 0).sum()):,}, "
        f"quantity < 0: {int((md.Quantity < 0).sum()):,}, no CustomerID: {int(md.CustomerID.isna().sum()):,}")
    out(f"- Rows with no CustomerID: {int(df.CustomerID.isna().sum()):,} ({df.CustomerID.isna().mean():.1%})")
    g_inv = df.groupby("InvoiceNo")
    out(f"- Invoices with more than one CustomerID: {int((g_inv.CustomerID.nunique() > 1).sum()):,}; "
        f"more than one Country: {int((g_inv.Country.nunique() > 1).sum()):,}; "
        f"more than one InvoiceDate: {int((g_inv.InvoiceDate.nunique() > 1).sum()):,}")
    out(f"- Stock codes with more than one distinct Description: "
        f"{int((df.groupby('StockCode').Description.nunique() > 1).sum()):,}")

    ex = pd.concat([
        ns.nlargest(10, "Line").assign(why="largest normal_sale line value"),
        ns.nlargest(10, "Quantity").assign(why="largest quantity"),
        ns.nlargest(10, "UnitPrice").assign(why="highest unit price"),
    ]) if len(ns) else pd.DataFrame()
    if len(ex):
        ex.drop(columns=["K_Desc", "K_Cust", "Occ", "RowId"]).to_csv(outdir / "extremes_sample.csv", index=False)

    # ---------------------------------------------------------------- 8 monthly
    out()
    out("## 8. Monthly view (partial months and overlap effect)")
    df["Month"] = df.InvoiceDate.dt.strftime("%Y-%m")
    mon = df.groupby("Month").agg(rows=("RowId", "size"), invoices=("InvoiceNo", "nunique"),
                                  first_day=("InvoiceDate", "min"), last_day=("InvoiceDate", "max"),
                                  raw_value=("Line", "sum")).reset_index()
    mon["value_without_overlap_copies"] = mon.Month.map(df[~df.OverlapCopy].groupby("Month").Line.sum())
    mon["gross_product_sales"] = mon.Month.map(df[df.RowClass == "normal_sale"].groupby("Month").Line.sum())
    mon["overlap_inflation_pct"] = ((mon.raw_value / mon.value_without_overlap_copies - 1) * 100).round(2)
    mon.to_csv(outdir / "monthly_summary.csv", index=False)
    show = mon[(mon.overlap_inflation_pct.abs() > 0) | mon.index.isin([0, 1, len(mon) - 2, len(mon) - 1])].copy()
    for c in ["raw_value", "value_without_overlap_copies", "gross_product_sales"]:
        show[c] = show[c].map(gbp)
    block(show)
    out("First and last months are partial: check first_day / last_day before comparing them with full months.")

    # ---------------------------------------------------------------- 9 checks
    hash_after = sha256(wb)
    out()
    out("## 9. Integrity checks")
    checks = [
        ("Workbook unchanged (SHA-256 before == after)", hash_before == hash_after),
        ("Category rows add up to total rows", int(g["rows"].sum()) == len(df)),
        ("Category values add up to raw total (within 0.01)", abs(math.fsum(cv.values()) - raw_total) < 0.01),
        ("Raw total - overlap copies = deduplicated total (within 0.01)", abs((raw_total - copy_value) - dedup_total) < 0.01),
        ("No 'other_unclassified' rows", int(g.loc["other_unclassified", "rows"]) == 0),
        ("Raw total equals provisional baseline", abs(round(raw_total, 2) - PROVISIONAL_BASELINE) < 0.005),
    ]
    for label, ok in checks:
        out(f"- {'PASS' if ok else 'CHECK'}: {label}")
    out(f"- SHA-256 after reading: `{hash_after}`")

    (outdir / "diagnostic_report.md").write_text("\n".join(R), encoding="utf-8")
    summary = {
        "workbook_sha256": hash_before, "rows": len(df), "raw_total": round(raw_total, 2),
        "overlap_copy_rows": n_copy, "overlap_copy_value": round(copy_value, 2),
        "deduplicated_total": round(dedup_total, 2),
        "within_sheet_repeat_rows": int(df.WithinRepeat.sum()),
        "category_rows": {k: int(g.loc[k, "rows"]) for k in CLASS_ORDER},
        "category_value": {k: round(cv[k], 2) for k in CLASS_ORDER},
        "checks": {label: bool(ok) for label, ok in checks},
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Done. Open {outdir / 'diagnostic_report.md'} and share it (plus small CSVs if asked).")


if __name__ == "__main__":
    main()
