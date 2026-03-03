-- ═══════════════════════════════════════════════════════════════════════════
-- E-COMMERCE CLV ANALYSIS — SQL QUERIES
-- These queries show the SQL logic behind what Python is doing.
-- In interviews, you can reference these to show your SQL skills.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── QUERY 1: Basic RFM Metrics ────────────────────────────────────────────
-- For each customer, calculate the 3 raw RFM values

SELECT 
    customer_id,
    
    -- Recency: days since last order
    DATEDIFF('2024-01-01', MAX(order_date))     AS recency_days,
    
    -- Frequency: total number of orders
    COUNT(DISTINCT order_id)                     AS frequency,
    
    -- Monetary: total amount spent
    SUM(order_value)                             AS monetary_value,
    
    -- Also useful: Average Order Value
    AVG(order_value)                             AS avg_order_value

FROM orders
WHERE is_returned = 0
GROUP BY customer_id
ORDER BY monetary_value DESC;


-- ── QUERY 2: RFM Scoring with NTILE ──────────────────────────────────────
-- Assign 1-5 scores using window functions (NTILE divides into equal buckets)

WITH rfm_metrics AS (
    SELECT 
        customer_id,
        DATEDIFF('2024-01-01', MAX(order_date)) AS recency,
        COUNT(DISTINCT order_id)                 AS frequency,
        SUM(order_value)                         AS monetary
    FROM orders
    WHERE is_returned = 0
    GROUP BY customer_id
),

rfm_scores AS (
    SELECT
        customer_id,
        recency,
        frequency,
        monetary,
        
        -- NTILE(5) splits customers into 5 equal groups
        -- Recency reversed: lower days = score 5 (more recent = better)
        6 - NTILE(5) OVER (ORDER BY recency ASC)    AS r_score,
        NTILE(5)     OVER (ORDER BY frequency ASC)  AS f_score,
        NTILE(5)     OVER (ORDER BY monetary ASC)   AS m_score
    FROM rfm_metrics
)

SELECT
    *,
    CONCAT(r_score, f_score, m_score) AS rfm_combined,
    (r_score + f_score + m_score) / 3.0 AS rfm_avg

FROM rfm_scores
ORDER BY rfm_avg DESC;


-- ── QUERY 3: Customer Segmentation ───────────────────────────────────────
-- Apply segment labels based on RFM scores

WITH rfm_metrics AS (
    SELECT 
        customer_id,
        DATEDIFF('2024-01-01', MAX(order_date)) AS recency,
        COUNT(DISTINCT order_id)                 AS frequency,
        SUM(order_value)                         AS monetary
    FROM orders WHERE is_returned = 0
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT *,
        6 - NTILE(5) OVER (ORDER BY recency ASC)    AS r_score,
        NTILE(5)     OVER (ORDER BY frequency ASC)  AS f_score,
        NTILE(5)     OVER (ORDER BY monetary ASC)   AS m_score
    FROM rfm_metrics
)

SELECT
    customer_id,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champion'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customer'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customer'
        WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
        ELSE 'Others'
    END AS segment
FROM rfm_scores;


-- ── QUERY 4: Cohort Retention Analysis ───────────────────────────────────
-- Classic cohort query: tracks how many customers return each month

WITH first_purchase AS (
    -- Get each customer's first purchase month (their cohort)
    SELECT
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m')   AS cohort_month,
        MIN(order_date)                          AS first_order_date
    FROM orders
    WHERE is_returned = 0
    GROUP BY customer_id
),

monthly_activity AS (
    -- Get every month each customer was active
    SELECT DISTINCT
        o.customer_id,
        DATE_FORMAT(o.order_date, '%Y-%m')      AS activity_month
    FROM orders o
    WHERE is_returned = 0
),

cohort_activity AS (
    -- Join to find month number (0, 1, 2...) relative to cohort start
    SELECT
        fp.cohort_month,
        ma.activity_month,
        COUNT(DISTINCT ma.customer_id)           AS active_customers,
        
        -- Month number = months elapsed since cohort started
        TIMESTAMPDIFF(
            MONTH,
            STR_TO_DATE(CONCAT(fp.cohort_month, '-01'), '%Y-%m-%d'),
            STR_TO_DATE(CONCAT(ma.activity_month, '-01'), '%Y-%m-%d')
        ) AS month_number
    FROM first_purchase fp
    JOIN monthly_activity ma ON fp.customer_id = ma.customer_id
    GROUP BY fp.cohort_month, ma.activity_month
)

SELECT
    cohort_month,
    month_number,
    active_customers,
    
    -- Retention rate = active / cohort_size
    ROUND(
        active_customers * 100.0 / 
        MAX(active_customers) OVER (PARTITION BY cohort_month),
        1
    ) AS retention_rate_pct

FROM cohort_activity
ORDER BY cohort_month, month_number;


-- ── QUERY 5: Pareto — Top 20% customers by revenue ───────────────────────

WITH customer_revenue AS (
    SELECT
        customer_id,
        SUM(order_value)  AS total_revenue,
        COUNT(order_id)   AS total_orders
    FROM orders
    WHERE is_returned = 0
    GROUP BY customer_id
),
ranked AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY total_revenue DESC) AS revenue_quintile
    FROM customer_revenue
)

SELECT
    revenue_quintile,
    COUNT(*)                    AS customer_count,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(SUM(total_revenue) * 100.0 / SUM(SUM(total_revenue)) OVER (), 1) AS revenue_pct
FROM ranked
GROUP BY revenue_quintile
ORDER BY revenue_quintile;


-- ── QUERY 6: Monthly Revenue Trend ───────────────────────────────────────

SELECT
    DATE_FORMAT(order_date, '%Y-%m')    AS month,
    COUNT(DISTINCT customer_id)          AS unique_customers,
    COUNT(order_id)                      AS total_orders,
    ROUND(SUM(order_value), 2)           AS total_revenue,
    ROUND(AVG(order_value), 2)           AS avg_order_value,
    
    -- Month-over-month revenue growth
    ROUND(
        (SUM(order_value) - LAG(SUM(order_value)) OVER (ORDER BY DATE_FORMAT(order_date, '%Y-%m'))) 
        * 100.0 
        / LAG(SUM(order_value)) OVER (ORDER BY DATE_FORMAT(order_date, '%Y-%m')),
        1
    ) AS mom_growth_pct

FROM orders
WHERE is_returned = 0
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month;
