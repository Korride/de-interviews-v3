-- =============================================================================
--  Additional mart checks: month bounds, MoM/YoY/CV, no leaked bad prices.
-- =============================================================================

SET search_path TO "TEST_V3";

\echo '=== month bounds (no future months) ==='
SELECT
    min(month) AS min_month,
    max(month) AS max_month
FROM mart_route_card;

\echo '=== sample with non-null mom/yoy/cv ==='
SELECT
    month,
    loading_city_name,
    unloading_city_name,
    body_group,
    weight_category,
    trips_count,
    median_trip,
    mom_pct,
    yoy_pct,
    cv_rate,
    reliability_level
FROM mart_route_card
WHERE mom_pct IS NOT NULL OR yoy_pct IS NOT NULL
ORDER BY trips_count DESC
LIMIT 8;

\echo '=== sanity: no negative/zero price leaked into mart ==='
SELECT
    count(*) AS bad_median
FROM mart_route_card
WHERE median_trip <= 0 OR median_km <= 0;
