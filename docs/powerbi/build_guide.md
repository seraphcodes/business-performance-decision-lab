# Power BI build guide (about 3 to 5 hours)

Power BI Desktop is free and Windows-only. The CSV files hold one row per sales line, so they stay on your computer (the folder is git-ignored). Only screenshots, the PDF and the `.pbix` go into the repo.

## 1. Make the CSV files
```
.\.venv\Scripts\python.exe -m src.build_db
.\.venv\Scripts\python.exe -m src.export_powerbi
```
Files appear in `data\processed\powerbi\`. If the export says "STOPPED", the totals did not tie to the bridge: do not build a report from it.

## 2. Load the data
1. Power BI Desktop > **Get data > Text/CSV**. Load all six files: `fact_sales`, `dim_date`, `dim_product`, `dim_country`, `dim_customer`, `cohort_activity`.
2. In **Transform data**, set these types: `fact_sales[date]` and `dim_date[date]` = **Date**; `customer_id` columns = **Whole number**. Close and apply.

## 3. Relationships (Model view)
All many-to-one, single direction, from the fact table to the dimension:
- `fact_sales[date]` > `dim_date[date]`
- `fact_sales[stock_code]` > `dim_product[stock_code]`
- `fact_sales[country]` > `dim_country[country]`
- `fact_sales[customer_id]` > `dim_customer[customer_id]` (guest orders have no ID and show as blank; cancellation lines also have a blank customer, because credit notes are not matched to customers)

`cohort_activity` has no relationship. In `dim_date`, sort `month_name` by `month_no`.

## 4. Measures
Paste each measure from `docs/powerbi/measures.dax` (Table tools > New measure / New column). Format money as Currency and rates as Percentage.

## 5. Check the numbers before designing anything
Put these in a card visual with no filters. They must equal the website's real figures:
- Gross Sales £19,700,954.46
- Cancellations -£719,692.94
- Net Revenue £18,981,261.52

If any differs by even one penny, stop and tell me. Do not fix it in the report.

## 6. Pages
1. **Overview:** KPI cards (Net Revenue, Gross Sales, Cancellations with rate, Sales Invoices, Average Order Value (gross)); monthly column chart of Net Revenue (full months); top products and countries bar charts.
2. **Customers:** a scope note (Known-Customer Share of Gross and Known Customers); cohort matrix (rows `cohort_month`, columns `months_since`, values Cohort Retention %, with a note about Dec 2009); segment table (Segment Customers %, Segment Gross Share); Top 10% Share and Top 20% Share.
3. **Methodology:** short text boxes: revenue not profit, gross vs net, what the data cannot tell you, link to the website and the GitHub repo.

Keep the same honesty as the website: label what is gross, what is whole period and what is partial.

## 7. Export for the repo
- Screenshots of each page > `docs/powerbi/`.
- File > Export > PDF > `docs/powerbi/report.pdf`.
- Save the report as `docs/powerbi/decision_lab.pbix`.
- Optional: if your uni account allows it, publish to Power BI Service and check whether "Publish to web" is available.
