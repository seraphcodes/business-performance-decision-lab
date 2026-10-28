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
