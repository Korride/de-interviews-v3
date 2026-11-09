-- =============================================================================
--  Row counts across the raw, core and mart layers.
-- =============================================================================

SELECT 'raw.prices'            AS table_name, count(*) AS row_count FROM raw.prices
UNION ALL
SELECT 'raw.cities',            count(*) FROM raw.cities
UNION ALL
SELECT 'raw.body_types',        count(*) FROM raw.body_types
UNION ALL
SELECT 'raw.price_body_types',  count(*) FROM raw.price_body_types
UNION ALL
SELECT 'raw.price_dates',       count(*) FROM raw.price_dates
UNION ALL
SELECT 'raw.exchange_rates',    count(*) FROM raw.exchange_rates
UNION ALL
SELECT 'raw.price_group_stats', count(*) FROM raw.price_group_stats
UNION ALL
SELECT 'raw.price_participants', count(*) FROM raw.price_participants
UNION ALL
SELECT 'core.dim_city',         count(*) FROM core.dim_city
ORDER BY table_name;
