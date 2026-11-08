-- =============================================================================
--  Row counts across the source and analytical tables.
-- =============================================================================

SET search_path TO "TEST_V3";

SELECT 'prices'              AS table_name, count(*) AS row_count FROM prices
UNION ALL
SELECT 'cities',             count(*) FROM cities
UNION ALL
SELECT 'body_types',         count(*) FROM body_types
UNION ALL
SELECT 'price_body_types',   count(*) FROM price_body_types
UNION ALL
SELECT 'price_dates',        count(*) FROM price_dates
UNION ALL
SELECT 'exchange_rates',     count(*) FROM exchange_rates
UNION ALL
SELECT 'price_group_stats',  count(*) FROM price_group_stats
UNION ALL
SELECT 'price_participants', count(*) FROM price_participants
UNION ALL
SELECT 'core_dim_city',      count(*) FROM core_dim_city
ORDER BY table_name;
