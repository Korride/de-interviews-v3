-- =============================================================================
--  Verification of the Question 2 mart (mart_route_card).
-- =============================================================================

SET search_path TO "TEST_V3";

-- === reliability_level distribution ===
SELECT
    reliability_level,
    count(*) AS n
FROM mart_route_card
GROUP BY reliability_level
ORDER BY reliability_level;

-- === top-10 cells by trips ===
SELECT
    month,
    loading_city_name,
    unloading_city_name,
    body_group,
    weight_category,
    trips_count,
    carriers_count,
    median_trip,
    median_km,
    reliability_level
FROM mart_route_card
ORDER BY trips_count DESC
LIMIT 10;

-- === grain uniqueness check (should be equal) ===
SELECT
    count(*)                                                                  AS total,
    count(DISTINCT (month, loading_city_gcid, unloading_city_gcid,
                    body_group, weight_category))                             AS distinct_grain
FROM mart_route_card;

-- === cross-check one cell: Москва->Казань, Тент, FTL, Oct 2026 ===
WITH manual AS (
    SELECT
        date_trunc('month', pd.price_date)::date                          AS month,
        count(DISTINCT f.price_id)                                        AS n,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY f.price_rub)         AS med,
        avg(f.price_rub)                                                  AS avg_price
    FROM core_fact_prices f
    JOIN core_price_body_group g
        ON g.price_id = f.price_id
    JOIN price_dates pd
        ON pd.price_id = f.price_id
    WHERE f.is_fact
      AND NOT f.complex
      AND f.price_rub > 0
      AND f.distance > 0
      AND NOT f.outlier_mark
      AND pd.price_date <= DATE '2026-10-26'
      AND f.loading_city_gcid   = 1001
      AND f.unloading_city_gcid = 1003
      AND g.body_group     = 'Тент'
      AND f.weight_category = 'FTL'
    GROUP BY 1
)
SELECT
    month,
    n                             AS manual_trips,
    round(med::numeric, 2)        AS manual_median,
    round(avg_price::numeric, 2)  AS manual_avg
FROM manual
ORDER BY month DESC
LIMIT 3;

SELECT
    month,
    trips_count,
    round(median_trip::numeric, 2) AS mart_median,
    round(avg_trip::numeric, 2)    AS mart_avg
FROM mart_route_card
WHERE loading_city_gcid   = 1001
  AND unloading_city_gcid = 1003
  AND body_group     = 'Тент'
  AND weight_category = 'FTL'
ORDER BY month DESC
LIMIT 3;
