# Online Retail II - workbook diagnostic report

## 1. Provenance
- File: `online_retail_II.xlsx`  (45,622,278 bytes)
- SHA-256 before reading: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`
- Run at: 2026-10-28T11:59:08
- Python 3.13.5, pandas 3.0.6, numpy 2.5.4
- Sheets found: ['Year 2009-2010', 'Year 2010-2011']

## 2. Per-sheet profile
```text
         sheet   rows          first_date           last_date  invoices  extra_exact_copies_in_sheet    raw_value
Year 2009-2010 525461 2009-12-01 07:45:00 2010-12-09 20:01:00     28816                         6865 9,539,484.63
Year 2010-2011 541910 2010-12-01 08:26:00 2011-12-09 12:50:00     25900                         5268 9,747,765.93
```
Total rows: 1,067,371.  Raw total (Quantity x UnitPrice, every row): **19,287,250.57**
Provisional baseline 19,287,250.57: **reproduced exactly**

Invoice prefixes (first character not a digit):
```text
InvoiceNo
C    19494
A        6
```

## 3. Sheet overlap (is any transaction exported twice?)
Date window where both sheets have data: 2010-12-01 08:26:00  ->  2010-12-09 20:01:00
Rows inside that window, per sheet:
```text
         Sheet  rows  invoices      value
Year 2009-2010 22523      1088 377,488.45
Year 2010-2011 22523      1088 377,488.45
```
Rows in sheet 2 that have an exact twin in sheet 1: **22,523** (value 377,488.45) = the amount the raw total double-counts.
- Dates of those rows: 2010-12-01 08:26:00 -> 2010-12-09 20:01:00
- Matched rows outside the shared window (should be 0): 0
- Sheet-2 window rows with a twin: 22,523 of 22,523 (100.0%)
- Sheet-1 window rows with a twin: 22,523 of 22,523 (100.0%)

Invoice numbers present in BOTH sheets: **1,088**. How their lines compare:
```text
         category  invoices
identical_in_both      1088
```

**How duplicates are told apart.** A row is called a *sheet-overlap copy* only if the same invoice line (all 8 fields) exists in sheet 1 AND sheet 2, matched occurrence by occurrence. A line that merely repeats inside one sheet is NOT treated as overlap; it is analysed in section 4.

## 4. Repeated identical lines inside one sheet (after removing overlap copies)
- Extra identical lines: **11,812** on 4,387 invoices; value of the extra copies 54,228.42
- Directly below an identical line in the file: 1,685 (14.3%). Back-to-back copies hint at double entry; scattered ones are more often genuine repeat lines.
- Share of these repeats inside the overlap window: 2.7% (window holds 2.2% of all rows). Similar shares = not an overlap effect.
- Most affected stock codes:
```text
stock_code  extra_lines
     21034          144
    85123A           58
     21212           51
     20751           48
     21232           43
     20727           43
     21755           42
     21754           42
```
These cannot be proven to be errors from the data alone (a customer can legitimately order the same product twice on one invoice). They are therefore FLAGGED, not removed; the revenue bridge shows the effect of removing them as a sensitivity.

## 5. Proposed row categories (each row in exactly one)
```text
               RowClass    rows  pct_rows    units         value  invoices
     sheet_overlap_copy   22523      2.11   166648    377,488.45      1088
         service_or_fee    5811      0.54    15429    -71,499.40      5465
            review_code     181      0.02    -4794      1,132.89       153
           cancellation   17973      1.68  -469881   -719,656.34      7405
negative_qty_non_cancel    3362      0.31  -564030          0.00      3362
         negative_price       0      0.00        0          0.00         0
             zero_price    2576      0.24   243450          0.00      1933
            normal_sale 1014945     95.09 11221670 19,699,784.97     39516
     other_unclassified       0      0.00        0          0.00         0
```
Priority order (first match wins): sheet_overlap_copy > service_or_fee > review_code > cancellation > negative_qty_non_cancel > negative_price > zero_price > normal_sale

Definitions and limitations:
- `sheet_overlap_copy`: Sheet-2 row with an exact twin (all 8 fields) in sheet 1. Proposed: exclude (same transaction exported twice).
- `service_or_fee`: StockCode is in SERVICE_CODES (postage, fees, manual, discount...). Proposed: keep, report separately, never count as product revenue.
- `review_code`: StockCode is not 5 digits(+letters) and not in SERVICE_CODES. Needs a human decision (see review_codes.csv).
- `cancellation`: Product line on an invoice starting with 'C' (credit note). Proposed: keep, report separately as cancellations/returns.
- `negative_qty_non_cancel`: Quantity < 0 on a non-'C' invoice (write-offs, damages, corrections?). Proposed: keep, report separately, not sales.
- `negative_price`: UnitPrice < 0 (bad-debt adjustments?). Proposed: not sales, report separately.
- `zero_price`: UnitPrice = 0 and Quantity > 0 (free items, samples, lost stock?). Value is 0. Proposed: not sales, count separately.
- `normal_sale`: Quantity > 0, UnitPrice > 0, product-style code, non-'C' invoice. Basis for gross product sales.
- `other_unclassified`: Anything else. Should be empty.

Service/fee lines by type (evidence for the meaning of each code is in the next table):
```text
     ServiceType  rows       value
      adjustment    76 -140,047.79
        discount   173  -12,879.63
             fee   152 -264,936.18
    gift_voucher   100    1,686.61
          manual  1403  -82,935.57
postage_carriage  3788  433,410.51
          sample   102   -6,000.85
            test    17      203.50
```
```text
   StockCode  rows       value                     top_description
        POST  2086  110,430.41                             POSTAGE
         DOT  1425  309,844.10                      DOTCOM POSTAGE
           M  1398  -82,950.62                              Manual
          C2   277   13,136.00                            CARRIAGE
           D   173  -12,879.63                            Discount
           S   102   -6,000.85                             SAMPLES
BANK CHARGES   100  -35,482.25                        Bank Charges
      ADJUST    67    6,835.24 Adjustment by john on 26/01/2010 16
   AMAZONFEE    36 -221,520.50                          AMAZON FEE
gift_0001_20    29      471.06  Dotcomgiftshop Gift Voucher £20.00
gift_0001_30    29      610.09  Dotcomgiftshop Gift Voucher £30.00
        CRUK    16   -7,933.43                     CRUK Commission
gift_0001_10    16      126.21  Dotcomgiftshop Gift Voucher £10.00
     TEST001    15      202.50             This is a test product.
gift_0001_50     8      253.59  Dotcomgiftshop Gift Voucher £50.00
gift_0001_40     7      166.09  Dotcomgiftshop Gift Voucher £40.00
           B     6 -147,614.08                     Adjust bad debt
           m     5       15.05                              Manual
gift_0001_80     4        0.00                           <missing>
     ADJUST2     3      731.05  Adjustment by Peter on Jun 25 2010
gift_0001_70     3       59.57                           <missing>
     TEST002     2        1.00             This is a test product.
gift_0001_60     2        0.00                           <missing>
gift_0001_90     2        0.00                           <missing>
```

Codes needing a human decision (review_code): 181 rows, 38 distinct codes, value 1,132.89. Top 40 in review_codes.csv.
```text
StockCode  rows  value  min_price  max_price  share_negative_qty              top_description
 DCGS0058    31  34.82       0.00       0.95                0.00             MISO PRETTY  GUM
DCGSSGIRL    25 295.63       0.00       3.36                0.04              GIRLS PARTY BAG
 DCGSSBOY    23 251.35       0.00       3.36                0.04               BOYS PARTY BAG
     PADS    19 -36.58       0.00      36.60                0.05   PADS TO MATCH ALL CUSHIONS
 DCGS0003    14  32.59       0.00       2.57                0.07          BOXED GLASS ASHTRAY
 DCGS0076    14 275.96      16.13      16.48                0.00 SUNJAR LED NIGHT NIGHT LIGHT
 DCGS0069     6  80.31       0.00      16.13                0.17        OOH LA LA DOGS COLLAR
 DCGS0004     5  67.94       0.00      17.35                0.20   HAYNES CAMPER SHOULDER BAG
 DCGS0072     4  20.68       0.00       5.17                0.25       CAT CAMOUFLAGUE COLLAR
DCGS0066N     4  17.30       0.00       8.65                0.00      NAVY CUDDLES DOG HOODIE
 DCGS0068     3  17.12       0.00       8.65                0.33            DOGS NIGHT COLLAR
 DCGS0070     3  25.44       0.00      12.72                0.33        CAMOUFLAGE DOG COLLAR
```

## 6. Revenue bridge (nothing hidden)
Formula for every line: `Line = Quantity x UnitPrice`.  Sums use exact float summation (math.fsum).
```text
A  Raw total, every row of both sheets                      19,287,250.57
B  less: sheet-overlap copies (sheet 2)                       -377,488.45
C  = Deduplicated total (A + B)                             18,909,762.12
   of which, by proposed category:
     service_or_fee                                     -71,499.40
     review_code                                          1,132.89
     cancellation                                      -719,656.34
     negative_qty_non_cancel                                  0.00
     negative_price                                           0.00
     zero_price                                               0.00
     normal_sale                                     19,699,784.97
     other_unclassified                                       0.00
   sum of categories                                        18,909,762.12
```
Proposed metric definitions (to be confirmed by us, not final):
- **Gross product sales** = sum of `normal_sale` lines = 19,699,784.97
- **Cancellation value** = sum of `cancellation` lines (negative) = -719,656.34
- **Net product revenue** = gross product sales + cancellation value = 18,980,128.63
- Cancellation value as % of gross product sales: 3.65%
- Not in any of the three: fees/services, review codes, write-offs (negative quantity), negative-price and zero-price lines. They stay visible in the table above.
- Sensitivity: gross product sales if the flagged within-sheet repeats were also removed = 19,642,692.15 (difference 57,092.82).
- `normal_sale` value with NO CustomerID: 2,574,858.74 (13.1%) - the part customer analytics cannot see.

## 7. Other data-quality checks
- 'C' invoice lines with Quantity > 0 (unexpected): 1
- Non-'C' lines with Quantity < 0: 3,457
- Quantity = 0 lines: 0
Rows with Quantity <= 0 broken down:
```text
   invoice_type     price description  rows
C (credit note) price > 0     present 19493
          non-C price = 0     missing  2689
          non-C price = 0     present   768
```
- Missing Description: 4,382 rows; of them price = 0: 4,382, quantity < 0: 2,689, no CustomerID: 4,382
- Rows with no CustomerID: 243,007 (22.8%)
- Invoices with more than one CustomerID: 0; more than one Country: 0; more than one InvoiceDate: 83
- Stock codes with more than one distinct Description: 1,232

## 8. Monthly view (partial months and overlap effect)
```text
  Month  rows  invoices           first_day            last_day    raw_value value_without_overlap_copies gross_product_sales  overlap_inflation_pct
2009-12 45228      2330 2009-12-01 07:45:00 2009-12-23 16:58:00   799,847.11                   799,847.11          800,939.83                    0.0
2010-01 31555      1633 2010-01-04 09:24:00 2010-01-31 16:02:00   624,032.89                   624,032.89          613,824.59                    0.0
2010-12 65004      2025 2010-12-01 08:26:00 2010-12-23 17:41:00 1,126,445.47                   748,957.02          777,865.64                   50.4
2011-11 84711      3462 2011-11-01 08:16:00 2011-11-30 17:42:00 1,461,756.25                 1,461,756.25        1,457,742.24                    0.0
2011-12 25526      1015 2011-12-01 08:12:00 2011-12-09 12:50:00   433,686.01                   433,686.01          615,489.98                    0.0
```
First and last months are partial: check first_day / last_day before comparing them with full months.

## 9. Integrity checks
- PASS: Workbook unchanged (SHA-256 before == after)
- PASS: Category rows add up to total rows
- PASS: Category values add up to raw total (within 0.01)
- PASS: Raw total - overlap copies = deduplicated total (within 0.01)
- PASS: No 'other_unclassified' rows
- PASS: Raw total equals provisional baseline
- SHA-256 after reading: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`