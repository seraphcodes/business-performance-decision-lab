-- Metric views on top of fact_lines. Created at build time by src/build_db.py.
--
-- Population rules (see docs/cleaning_rules.md and docs/metrics.md):
--   * "sales population" = rows in category normal_sale or cancellation.
--   * sheet-overlap copies, services/fees, stock adjustments, zero/negative
--     price and unknown codes are never in these views (they stay in fact_lines
--     and in the reconciliation table).
--   * months come from the invoice's first timestamp (year_month column).
--   * money columns are NOT rounded here: round only when displaying, so the
--     build can reconcile the views to the bridge to the penny.

-- One row per month: the headline monthly table.
CREATE VIEW v_monthly_revenue AS
SELECT
    year_month,
    MAX(is_partial_month) AS is_partial_month,
    SUM(CASE WHEN row_class = 'normal_sale'  THEN line_value ELSE 0 END) AS gross_product_sales,
    SUM(CASE WHEN row_class = 'cancellation' THEN line_value ELSE 0 END) AS cancellation_value,
    SUM(line_value)                                                      AS net_product_revenue,
    SUM(CASE WHEN row_class = 'normal_sale' THEN quantity ELSE 0 END)    AS units_sold,
    COUNT(DISTINCT CASE WHEN row_class = 'normal_sale'  THEN invoice_no END)  AS sales_invoices,
    COUNT(DISTINCT CASE WHEN row_class = 'cancellation' THEN invoice_no END)  AS credit_notes,
    COUNT(DISTINCT CASE WHEN row_class = 'normal_sale'  THEN customer_id END) AS known_customers,
    ROUND(100.0 * -SUM(CASE WHEN row_class = 'cancellation' THEN line_value ELSE 0 END)
          / NULLIF(SUM(CASE WHEN row_class = 'normal_sale' THEN line_value ELSE 0 END), 0), 2)
          AS cancellation_rate_pct,
    ROUND(SUM(CASE WHEN row_class = 'normal_sale' THEN line_value ELSE 0 END)
          / NULLIF(COUNT(DISTINCT CASE WHEN row_class = 'normal_sale' THEN invoice_no END), 0), 2)
          AS avg_order_value
FROM fact_lines
WHERE row_class IN ('normal_sale', 'cancellation')
GROUP BY year_month;

-- Postage, fees, manual entries, adjustments... by month, kept apart from product revenue.
CREATE VIEW v_monthly_service_lines AS
SELECT
    year_month,
    service_type,
    COUNT(*)        AS line_count,
    SUM(line_value) AS value
FROM fact_lines
WHERE row_class = 'service_or_fee'
GROUP BY year_month, service_type;

-- Products ranked by NET sales (gross sales + cancellations). Grouped by stock_code,
-- never by description. Ranking by gross would reward orders that were sold and
-- then cancelled (the real data has two such 75,000+ unit orders).
CREATE VIEW v_top_products AS
WITH per_product AS (
    SELECT
        stock_code,
        SUM(CASE WHEN row_class = 'normal_sale'  THEN line_value ELSE 0 END) AS gross_sales,
        SUM(CASE WHEN row_class = 'cancellation' THEN line_value ELSE 0 END) AS cancelled_value,
        SUM(line_value)                                                      AS net_sales,
        SUM(CASE WHEN row_class = 'normal_sale'  THEN quantity ELSE 0 END)   AS units_sold,
        SUM(CASE WHEN row_class = 'cancellation' THEN -quantity ELSE 0 END)  AS units_cancelled,
        COUNT(DISTINCT CASE WHEN row_class = 'normal_sale' THEN invoice_no END) AS invoices
    FROM fact_lines
    WHERE row_class IN ('normal_sale', 'cancellation')
    GROUP BY stock_code
)
SELECT
    RANK() OVER (ORDER BY p.net_sales DESC)             AS sales_rank,
    p.stock_code,
    d.canonical_description                             AS description,
    p.gross_sales,
    p.cancelled_value,
    p.net_sales,
    p.units_sold,
    p.units_cancelled,
    p.invoices,
    100.0 * p.net_sales / SUM(p.net_sales) OVER ()      AS share_of_net_pct
FROM per_product p
LEFT JOIN dim_product d ON d.stock_code = p.stock_code;

-- Revenue by country.
CREATE VIEW v_country_revenue AS
SELECT
    country,
    SUM(CASE WHEN row_class = 'normal_sale'  THEN line_value ELSE 0 END) AS gross_product_sales,
    SUM(CASE WHEN row_class = 'cancellation' THEN line_value ELSE 0 END) AS cancellation_value,
    SUM(line_value)                                                      AS net_product_revenue,
    COUNT(DISTINCT CASE WHEN row_class = 'normal_sale' THEN invoice_no END)  AS sales_invoices,
    COUNT(DISTINCT CASE WHEN row_class = 'normal_sale' THEN customer_id END) AS known_customers
FROM fact_lines
WHERE row_class IN ('normal_sale', 'cancellation')
GROUP BY country;

-- One row per invoice with sales (an invoice is an order). Basis for order-value analysis.
CREATE VIEW v_invoice_summary AS
SELECT
    invoice_no,
    MIN(invoice_day)  AS invoice_day,
    MIN(year_month)   AS year_month,
    MAX(customer_id)  AS customer_id,   -- an invoice never has two customers in this data
    MIN(country)      AS country,
    COUNT(*)          AS line_count,
    SUM(quantity)     AS units,
    SUM(line_value)   AS gross_value
FROM fact_lines
WHERE row_class = 'normal_sale'
GROUP BY invoice_no;

-- How much of each month's gross sales can be tied to a known customer.
CREATE VIEW v_customer_coverage AS
SELECT
    year_month,
    SUM(CASE WHEN missing_customer = 0 THEN line_value ELSE 0 END) AS gross_with_customer,
    SUM(CASE WHEN missing_customer = 1 THEN line_value ELSE 0 END) AS gross_without_customer,
    ROUND(100.0 * SUM(CASE WHEN missing_customer = 0 THEN line_value ELSE 0 END)
          / NULLIF(SUM(line_value), 0), 2) AS pct_with_customer
FROM fact_lines
WHERE row_class = 'normal_sale'
GROUP BY year_month;

-- ---------------------------------------------------------------------------
-- Customer analytics (Phase 2). Only invoices with a known customer ID can be
-- used (about 87% of gross sales value; the rest is guest checkout / unknown).
-- Values here are GROSS product sales (no credit-note netting), the same basis
-- as the average order value. Rules are in docs/customer_analytics.md.
-- ---------------------------------------------------------------------------

-- One row per known customer. Built from the lines (not from v_invoice_summary), so it
-- ties to v_customer_coverage by construction, even if an invoice mixed known and
-- unknown customer rows.
CREATE VIEW v_customer_value AS
SELECT
    customer_id,
    COUNT(DISTINCT invoice_no) AS orders,
    SUM(line_value)   AS gross_value,
    MIN(invoice_day)  AS first_day,
    MAX(invoice_day)  AS last_day,
    MIN(year_month)   AS first_month
FROM fact_lines
WHERE row_class = 'normal_sale' AND customer_id IS NOT NULL
GROUP BY customer_id;

-- Cohort retention: customers grouped by the month of their first order, and how
-- many of them ordered again N months later. FULL months only (the partial last
-- month is left out). The first month of the data is flagged: customers already
-- active before the data starts are not really "new", so that cohort is left-censored.
CREATE VIEW v_cohort_activity AS
WITH months AS (
    SELECT customer_id, year_month
    FROM fact_lines
    WHERE row_class = 'normal_sale' AND customer_id IS NOT NULL
      AND year_month NOT IN (SELECT year_month FROM v_monthly_revenue WHERE is_partial_month = 1)
    GROUP BY customer_id, year_month
),
cohort_size AS (
    SELECT first_month AS cohort_month, COUNT(*) AS cohort_customers
    FROM v_customer_value
    WHERE first_month NOT IN (SELECT year_month FROM v_monthly_revenue WHERE is_partial_month = 1)
    GROUP BY first_month
)
SELECT
    c.first_month AS cohort_month,
    m.year_month  AS activity_month,
    (CAST(substr(m.year_month, 1, 4) AS INTEGER) * 12 + CAST(substr(m.year_month, 6, 2) AS INTEGER))
  - (CAST(substr(c.first_month, 1, 4) AS INTEGER) * 12 + CAST(substr(c.first_month, 6, 2) AS INTEGER))
                  AS months_since,
    COUNT(*)      AS active_customers,
    s.cohort_customers,
    ROUND(100.0 * COUNT(*) / s.cohort_customers, 2) AS retention_pct,
    CASE WHEN c.first_month = (SELECT MIN(year_month) FROM v_monthly_revenue) THEN 1 ELSE 0 END
                  AS is_left_censored
FROM months m
JOIN v_customer_value c ON c.customer_id = m.customer_id
JOIN cohort_size s      ON s.cohort_month = c.first_month
GROUP BY c.first_month, m.year_month;

-- RFM: Recency (days since last order), Frequency (orders), Monetary (gross sales).
-- Snapshot = the day after the last invoice day in the data. Each score is 1-5
-- (5 = best) from the cumulative share of customers, so customers with the same
-- value always get the same score (no arbitrary split of ties). Because many customers
-- share the lowest frequency (one order), that group can score 2, not 1. The monetary
-- score is reported but not used in the segment rules. Segment names only describe
-- the recency and frequency scores; they do not predict behaviour.
CREATE VIEW v_customer_rfm AS
WITH base AS (
    SELECT
        customer_id, orders AS frequency, gross_value AS monetary, last_day,
        CAST(julianday((SELECT date(MAX(invoice_day), '+1 day') FROM fact_lines WHERE row_class = 'normal_sale'))
             - julianday(last_day) AS INTEGER) AS recency_days
    FROM v_customer_value
),
ranked AS (
    SELECT *,
        CUME_DIST() OVER (ORDER BY recency_days DESC) AS r_cd,
        CUME_DIST() OVER (ORDER BY frequency)         AS f_cd,
        CUME_DIST() OVER (ORDER BY monetary)          AS m_cd
    FROM base
),
scored AS (
    SELECT customer_id, recency_days, frequency, monetary, last_day,
        1 + CAST(r_cd * 5 - 1e-9 AS INTEGER) AS r_score,
        1 + CAST(f_cd * 5 - 1e-9 AS INTEGER) AS f_score,
        1 + CAST(m_cd * 5 - 1e-9 AS INTEGER) AS m_score
    FROM ranked
)
SELECT *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Recent & frequent'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Repeat buyers'
        WHEN r_score >= 4                  THEN 'Recent, low frequency'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'Repeat, not recent'
        WHEN r_score <= 2                  THEN 'Not recent, low frequency'
        ELSE 'Mid recency, low frequency'
    END AS segment
FROM scored;
