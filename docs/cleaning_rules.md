# Cleaning rules and metric definitions

Status: **approved 2026-10-28**, implemented in `src/` (milestone M1).
Evidence: `docs/diagnostics/diagnostic_report.md`, produced by
`tools/diagnose_workbook.py` on the original workbook (SHA-256 starts
`bcbe73b3`). All figures below come from that report unless marked
*assumption*.

## Principle: label, never delete

Every one of the 1,067,371 original rows is kept in the database
(`fact_lines`) with a category and flags. Excluded rows stay visible, and the
`reconciliation` table walks from the raw total to every headline number. The
build refuses to write the database if rows or pounds do not add up.

## The rules

| # | Rule | Evidence | Limitation |
|---|------|----------|------------|
| 1 | **Remove sheet-overlap copies.** A sheet-2 row with an exact twin (all 8 fields) in sheet 1 is excluded. | Both sheets hold 22,523 rows for 1 Dec 08:26 - 9 Dec 20:01 2010; 100% have a twin; all 1,088 shared invoices are identical; no conflicts. Raw total double-counts £377,488.45; Dec 2010 is inflated by 50.4%. | Only exact twins are removed. A conflicting twin would need a human decision (none exist today). |
| 2 | **Keep and flag repeated identical lines inside a sheet.** | 11,812 extra lines on 4,387 invoices; only 14.3% sit directly below an identical line; 2.7% fall in the overlap window (window = 2.2% of rows), so it is not an overlap effect. Removing them would change gross product sales by £57,092.82 (0.29%). | The data cannot prove they are genuine (*assumption*: a customer can order the same product twice on an invoice). The effect is reported as a sensitivity. |
| 3 | **Services and fees are never product revenue.** They are kept and reported by type: postage/carriage, manual, adjustment, discount, sample, fee, gift voucher, test. | Meaning checked against the most common description per code. `AMAZONFEE` = -£221,520.50 on 36 rows; bad-debt adjustment `B` = -£147,614.08 on 6 rows; postage `DOT` +£309,844.10, `POST` +£110,430.41. These few large lines would distort monthly trends if mixed into sales. | Treating postage as separate from product revenue is a business choice (*assumption*: postage is customer income but not product sales). |
| 4 | **`DCGS*`, `SP<digits>` and `PADS` count as product codes.** Any other non-standard code is `unknown_code` and excluded. | Their descriptions are product names (for example "GIRLS PARTY BAG", "SUNJAR LED NIGHT NIGHT LIGHT") with positive prices. Net effect of this choice: +£1,132.89 (0.006% of sales), so it cannot move results. It moves 181 rows out of the diagnostic's `review_code` group: 143 into normal sales, 29 into non-credit negative quantity, 6 into zero price, 2 into `unknown_code` and 1 credit-note line (-£36.60) into cancellations. | Judgement from descriptions. `C3` and `GIFT` stay `unknown_code` (zero value). |
| 5 | **Stock adjustments are not sales.** Non-credit-note lines with a negative quantity, and lines with a missing description, are excluded from sales and from units sold, but kept. | All 4,382 missing-description rows have price 0 and no customer; 2,689 have a negative quantity. Non-credit negative-quantity rows carry £0 value but -564,030 units, which would distort unit-based metrics. | *Assumption*: these are write-offs or corrections. The business meaning is inferred from the pattern, not documented. |
| 6 | **Cancellations** (product lines on `C` invoices) are kept, reported separately and netted into net product revenue. | 17,974 product rows, -£719,692.94 (3.65% of gross product sales). | Credit notes cannot be linked reliably to the original sale, so cancellation rates are **by period**, not by order. One `C` line has a positive quantity (flagged for review). |
| 7 | **Time.** Each invoice uses its earliest timestamp. The last month of the data is flagged partial if it ends before month end. | 83 invoices carry more than one timestamp. Data ends 9 Dec 2011 (Dec 2011 has 9 days). Dec 2009 and Dec 2010 end on the 23rd and January starts on the 4th (holiday closure, not missing data). | Dec 2011 must not be compared with full months. |

Two further facts that shape analysis, not cleaning:
- **22.8% of rows (243,007) have no Customer ID**, which is 13.1% of product
  sales value (£2,574,858.74). Customer-level analysis covers about 87% of sales
  value and must say so.
- **1,232 stock codes have more than one description.** Product analysis groups
  by `StockCode`. `dim_product` stores the most common description.

## Metric definitions

`Line = Quantity x UnitPrice`, summed with exact float summation.

| Metric | Definition |
|--------|-----------|
| Raw total | Sum of `Line` over every row of both sheets. Reproduced exactly: **£19,287,250.57**. |
| Deduplicated total | Raw total minus overlap copies = **£18,909,762.12**. |
| Gross product sales | Sum of `Line` over `normal_sale` rows. |
| Cancellation value | Sum of `Line` over `cancellation` rows (negative). |
| Net product revenue | Gross product sales + cancellation value. |
| Cancellation rate | -Cancellation value / gross product sales, per period. |

These are **revenue figures, not profit**. The data has no product costs.

The exact final numbers (after rule 4 moves a few hundred pounds of `DCGS*`
rows into normal sales) are produced by the build and stored in the
`reconciliation` table.

## Categories (first match wins)

1. `sheet_overlap_copy` 2. `service_or_fee` 3. `unknown_code`
4. `cancellation` 5. `negative_qty_non_cancel` 6. `negative_price`
7. `zero_price` 8. `normal_sale` (anything else = `other_unclassified`, which
must stay empty or the build fails).

A credit note for postage stays in `service_or_fee`, and a fee line with a
negative quantity stays in `service_or_fee`, because the first matching rule
wins.

## How the rules are checked

- `python -m pytest`: hand-calculated tests for each rule and for the
  reconciliation. The tests were checked by deliberately breaking the code in
  eight ways; each break is caught.
- `python -m src.build_db`: on the real workbook it also compares rows, raw
  total, overlap rows and value, deduplicated total and the within-sheet repeat
  count with the diagnostic baseline, and writes nothing on any mismatch.
