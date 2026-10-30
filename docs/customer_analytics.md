# Customer analytics rules

Views: `v_customer_value`, `v_cohort_activity`, `v_customer_rfm` in `sql/views.sql`. Shown on the website's Customers page.

## Who is included
- Only normal-sale lines with a customer ID. About 13% of gross sales value has no ID (guest checkouts) and cannot be followed over time.
- Values are **gross** product sales, the same basis as average order value. Credit notes are not matched to customers.
- Built from the order lines, so known + unknown customers add up to the bridge's gross sales. The build stops if they do not.

## Cohort retention
- Cohort = month of the customer's first order. Cell = share of that cohort that ordered in the month N months later.
- Full months only: the partial last month is neither a cohort nor an activity month.
- The first month of the data (Dec 2009) is marked left-censored: it contains customers who were already buying before the data starts, so it is not a "new customer" cohort.

## RFM
- Recency = days from the last order to the day after the last invoice in the data. Frequency = number of orders. Monetary = gross sales.
- Scores 1-5 (5 = best) from the cumulative share of customers, so equal values always get equal scores.
- Segments (first match wins): Champions (R>=4, F>=4), Loyal (R>=3, F>=3), Recent (R>=4), At risk (R<=2, F>=3), Inactive (R<=2), Needs attention (the rest).
- Segments describe the past. "Inactive" means no order in the data, not "churned".

## Concentration
- Top p% = the largest ceil(p x customers) customers by gross value (ties broken by customer ID).
- Many large accounts are probably businesses buying wholesale.
