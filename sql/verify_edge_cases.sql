-- =============================================================================
--  Quick sanity check of the edge cases embedded in the source data.
-- =============================================================================

SELECT 'currency 643'               AS metric, count(*) AS n FROM raw.prices WHERE currency_code = '643'
UNION ALL
SELECT 'currency 840 (USD)',        count(*) FROM raw.prices WHERE currency_code = '840'
UNION ALL
SELECT 'currency 978 (EUR)',        count(*) FROM raw.prices WHERE currency_code = '978'
UNION ALL
SELECT 'outlier_mark = true',       count(*) FROM raw.prices WHERE outlier_mark
UNION ALL
SELECT 'complex = true',            count(*) FROM raw.prices WHERE complex
UNION ALL
SELECT 'price <= 0',                count(*) FROM raw.prices WHERE price <= 0
UNION ALL
SELECT 'RUB price <= 1000',         count(*) FROM raw.prices
                                    WHERE currency_code = '643' AND price <= 1000
UNION ALL
SELECT 'is_fact = true',            count(*) FROM raw.prices WHERE is_fact
UNION ALL
SELECT 'body_type IS NULL',         count(*) FROM raw.prices WHERE body_type IS NULL
UNION ALL
SELECT 'nearest_rate_date IS NULL', count(*) FROM raw.prices WHERE nearest_rate_date IS NULL
UNION ALL
SELECT 'future loading_date',       count(*) FROM raw.prices WHERE loading_date > DATE '2026-10-26'
ORDER BY metric;
