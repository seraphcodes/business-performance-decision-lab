# Business Performance & Decision Lab

A business-intelligence project on two years of real retail transactions
(Online Retail II). The focus is **numbers you can trust**: a reproducible
pipeline that reconciles to the penny, documented cleaning rules, SQL metric
views, and a dashboard that states what the data can and cannot say.

Stack: Python, pandas, SQLite, Streamlit, Plotly, pytest.

**Status:** core release done: data pipeline, metric views, Overview,
Methodology and a narrow What-If Simulator. Planned next: customer analytics
(cohorts, RFM).

## What it does

1. **Builds a database from the raw Excel workbook** (`python -m src.build_db`).
   Every one of the 1,067,371 original rows is kept and labelled; none are deleted.
2. **Reconciles** from the raw total (£19,287,250.57) to net product revenue
   (£18,981,261.52). The build refuses to write the database if rows or pounds
   do not add up or do not match the diagnostic baseline.
3. **Defines metrics in SQL views** (`sql/views.sql`), checked against the
   reconciliation at build time.
4. **Shows them in a Streamlit app**: Overview (trends, cancellations, products,
   countries), Methodology (the reconciliation chart, rules, limits) and a
   What-If Simulator.
5. **What-If Simulator**: a scenario calculator on a real 12-month baseline. Price
   change, volume change and cost share are the user's inputs. It shows revenue
   effect, break-even volume and a sensitivity grid. It is arithmetic, not a
   forecast: the data has no product costs, so profit exists only through the cost
   share the user enters, and it does not model how volume reacts to price.

## Web frontend (static site)

`web/` is a separate, dependency-free website (HTML, CSS, JavaScript; Chart.js is
included in `web/vendor/`). It has the same three pages as the Streamlit app, a
light/dark theme and a phone layout. It only displays `web/data/metrics.js`, an
export of the reconciled SQL views, so its numbers are the numbers the build
already checked.

- Refresh the data after a build: `.\.venv\Scripts\python.exe -m src.export_web`
  (refuses to write if the views no longer tie to the reconciliation bridge).
- View it: open `web/index.html` in a browser (no server needed).
- The what-if arithmetic in `web/js/scenario.js` is a port of `src/scenario.py`;
  `tests/test_web_scenario.py` runs both on 140 combinations and requires identical results
  (needs Node.js; skipped if it is not installed).
- Publish free on GitHub Pages: copy `docs/deploy/pages.yml` to `.github/workflows/pages.yml`,
  push, then set repository Settings > Pages > Source to **GitHub Actions**.

## Screenshots

**Overview: net revenue by month** (incomplete Dec 2011 hidden by default)

![Net product revenue by month](docs/screenshots/overview-monthly.png)

**Overview: top products (net) and countries**

![Top products and countries](docs/screenshots/overview-products-countries.png)

**Methodology: from raw rows to net revenue**

![Reconciliation chart](docs/screenshots/methodology-bridge.png)

## Findings

- **The raw total double-counts £377,488.45.** The workbook's two sheets overlap
  for 1-9 Dec 2010; all 22,523 rows in that window appear twice. Removing the
  copies gives £18,909,762.12.
- **Net product revenue is £18,981,261.52** (gross sales £19,700,954.46 minus
  cancellations £719,692.94). Postage, fees and adjustments are kept apart from
  product revenue.
- **November is the peak** in both years (about £1.40M in 2010 and £1.43M in 2011).
- **Cancellation spikes come from a few huge orders** that were sold and cancelled
  (for example stock code 23843, about £168k, in Dec 2011), so products are ranked
  by net sales, not gross.
- **The UK is the large majority of revenue** (about £16.2M net of £19.0M).

## Limitations (read before quoting a number)

- Revenue, **not profit**: the data has no product costs.
- 22.8% of rows have no Customer ID (13.1% of sales value), so customer-level
  analysis covers about 87% of sales.
- Credit notes cannot be linked to the original sale, so cancellation rates are
  by month, not by order.
- December 2011 contains only 9 days and is hidden from trend charts by default.
- Some cleaning choices are judgement calls (stock adjustments, repeated identical
  lines, postage as separate income). Each is listed with evidence in
  `docs/cleaning_rules.md`.

## How to run

Run every command from the project folder, using the project's own virtual
environment (Windows PowerShell shown).

1. Install the pinned dependencies once:
   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
2. Put the UCI workbook at `data/raw/online_retail_II.xlsx` (it is not committed).
3. Run the tests (they need no data): `.\.venv\Scripts\python.exe -m pytest`
4. Build the database (a few minutes, needs roughly 1 GB free disk):
   `.\.venv\Scripts\python.exe -m src.build_db`
5. Optional text report of the headline numbers:
   `.\.venv\Scripts\python.exe -m src.metrics`
6. Start the app: `.\.venv\Scripts\python.exe -m streamlit run app.py`

## Project layout

- `src/` pipeline: `load`, `classify`, `reconcile`, `build_db`, `metrics`, `scenario`
- `sql/views.sql` metric definitions
- `pages/` Streamlit pages; `app.py` landing page
- `web/` static website; `src/export_web.py` creates its data file
- `tests/` hand-calculated fixtures; the rules were also checked by deliberately
  breaking the code (all breaks caught)
- `docs/` cleaning rules, metric definitions, diagnostic evidence

## Dataset and attribution

Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5CG6D. Licence: CC BY 4.0
(https://archive.ics.uci.edu/dataset/502/online+retail+ii).

Changes made: cleaned, labelled and loaded into SQLite (see the Methodology page
and `docs/cleaning_rules.md`). This project is not affiliated with or endorsed by
the dataset's authors.
