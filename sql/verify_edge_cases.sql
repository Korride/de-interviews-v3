-- =============================================================================
--  Quick sanity check of the edge cases embedded in the source data.
-- =============================================================================

SET search_path TO "TEST_V3";

SELECT 'currency 643'             AS metric, count(*) AS n FROM prices WHERE currency_code = '643'
UNION ALL
SELECT 'currency 840 (USD)',       count(*) FROM prices WHERE currency_code = '840'
UNION ALL
SELECT 'currency 978 (EUR)',       count(*) FROM prices WHERE currency_code = '978'
UNION ALL
SELECT 'outlier_mark = true',      count(*) FROM prices WHERE outlier_mark
UNION ALL
SELECT 'complex = true',           count(*) FROM prices WHERE complex
UNION ALL
SELECT 'price <= 0',               count(*) FROM prices WHERE price <= 0
UNION ALL
SELECT 'RUB price <= 1000',        count(*) FROM prices
                                   WHERE currency_code = '643' AND price <= 1000
UNION ALL
SELECT 'is_fact = true',           count(*) FROM prices WHERE is_fact
UNION ALL
SELECT 'body_type IS NULL',        count(*) FROM prices WHERE body_type IS NULL
UNION ALL
SELECT 'nearest_rate_date IS NULL', count(*) FROM prices WHERE nearest_rate_date IS NULL
UNION ALL
SELECT 'future loading_date',      count(*) FROM prices WHERE loading_date > DATE '2026-10-26'
ORDER BY metric;
