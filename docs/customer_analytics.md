# Customer analytics rules

Views: `v_customer_value`, `v_cohort_activity`, `v_customer_rfm` in `sql/views.sql`. Shown on the website's Customers page.

## Who is included
- Only normal-sale lines with a customer ID. About 13% of gross sales value has no ID (guest checkouts) and cannot be followed over time.
- Values are **gross** product sales, the same basis as average order value. Credit notes are not matched to customers.
- Built from the order lines, so known + unknown customers add up to the bridge's gross sales. The build stops if they do not.

## Cohort retention
- Cohort = month of the customer's first order. Cell = share of that cohort that ordered in the month N months later.
- Full months only: the partial last month is neither a cohort nor an activity month. Customers whose first order falls in that partial month (28 in this data) are in no cohort, so the cohort sizes add up to 28 fewer than the known customers.
- Percent = customers from the cohort who ordered in that month / customers in the cohort (the cohort size). The counts are shown next to the percentages. Cells beyond the end of the data are blank: recent cohorts have fewer months to observe.
- The first month of the data (Dec 2009) is marked left-censored: it contains customers who were already buying before the data starts, so it is not a "new customer" cohort.

## RFM
- Recency = days from the last order to the day after the last invoice in the data. Frequency = number of orders. Monetary = gross sales.
- Scores 1-5 (5 = best) from the cumulative share of customers, so equal values always get equal scores. Fewer days since the last order scores higher; more orders and more sales score higher.
- Because more than 20% of customers have exactly one order, that group scores F = 2 and no customer scores F = 1. In this data F = 3 is 2-3 orders, F = 4 is 4-7 and F = 5 is 8 or more.
- The monetary score is calculated and exported but is not used in the segment rules.
- Segments (first match wins): Recent & frequent (R>=4, F>=4), Repeat buyers (R>=3, F>=3; includes customers with 2 orders), Recent, low frequency (R>=4), Repeat, not recent (R<=2, F>=3), Not recent, low frequency (R<=2), Mid recency, low frequency (the rest).
- Segment names describe the recency and frequency scores. They do not predict behaviour: "not recent" means no order for a long time before the end of the data, not "churned".

## Concentration
- Top p% = the largest ceil(p x customers) customers by gross value (ties broken by customer ID).
- Many large accounts are probably businesses buying wholesale.
