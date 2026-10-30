# Metric views (milestone M2)

All dashboard numbers come from SQL views defined in `sql/views.sql`, created by
`python -m src.build_db` and read through `src/metrics.py` (read-only connection).

| View | One row per | Use |
|------|-------------|-----|
| `v_monthly_revenue` | month | gross, cancellations, net, units, invoices, known customers, cancellation rate, average order value, partial-month flag |
| `v_monthly_service_lines` | month x service type | postage, fees, adjustments - shown apart from product revenue |
| `v_top_products` | stock code | rank by **net** sales (gross + cancelled), units, share of net (grouped by code, not description) |
| `v_country_revenue` | country | gross, cancellations, net, invoices, customers |
| `v_invoice_summary` | invoice with sales | order value basis |
| `v_customer_coverage` | month | share of gross sales tied to a known customer (about 87% overall) |

## Rules every view follows
- Sales population = `normal_sale` + `cancellation` rows only. Overlap copies, services, adjustments, zero/negative price and unknown codes are excluded (they remain in `fact_lines` and the reconciliation).
- Money is not rounded in views, so totals tie to the bridge to the penny.
- Cancellation rate = cancellations / gross sales **in the same month** (credit notes cannot be linked to the original sale).
- The final month (Dec 2011, 9 days) is flagged partial; `metrics.monthly_revenue()` leaves it out by default.
- Average order value = gross product sales / invoices with sales. Revenue, not profit. It is a *gross* figure: it includes orders that were cancelled later, so a net-based average would be lower.

## How they are checked
- The build compares view totals with the pandas bridge (tolerance 0.005) and refuses to write the database on mismatch.
- `tests/test_metrics.py`: hand-calculated values, plus a randomized SQL-vs-pandas cross-check.
- Mutation checks: five deliberate view bugs; all caught after two tests were added.

## Known data quirk: sold-then-cancelled bulk orders
The real data holds orders of 75,000+ units that were cancelled the same day
(for example stock code 23843 in Dec 2011, about £168k, and a ceramic storage
jar order in Jan 2011). They inflate gross sales and the cancellation rate of
those months (Jan 2011: 13.6%, Dec 2011: 28.3%) while net revenue is
unaffected. Product rankings therefore use **net** sales. Month-level
cancellation rates should be read with this in mind.
