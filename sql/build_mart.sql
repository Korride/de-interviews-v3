-- =============================================================================
--  Question 2: analytical mart «route card / market corridor» (mart_route_card).
--  grain: month x loading city x unloading city x body_group x weight_category.
--  Month is formed from price_dates.price_date (long deals span several months).
--  Idempotent: TRUNCATE + INSERT inside one transaction.
--
--  Freshness rule (documented): a month cell is «fresh» when
--    (as_of - month_start) <= 30 days  (as_of = 2026-10-26),
--  i.e. only the current month (October 2026) qualifies as fresh.
-- =============================================================================

SET search_path TO "TEST_V3";

BEGIN;

TRUNCATE mart_route_card;

INSERT INTO mart_route_card (
    month,
    loading_city_gcid,
    unloading_city_gcid,
    loading_city_name,
    unloading_city_name,
    body_group,
    weight_category,
    p25_trip,
    median_trip,
    p75_trip,
    avg_trip,
    p25_km,
    median_km,
    p75_km,
    trips_count,
    carriers_count,
    cv_rate,
    mom_pct,
    yoy_pct,
    reliability_level
)
WITH base AS (
    SELECT
        date_trunc('month', pd.price_date)::date   AS month,
        f.loading_city_gcid,
        f.unloading_city_gcid,
        lc.name                                    AS loading_city_name,
        uc.name                                    AS unloading_city_name,
        g.body_group,
        f.weight_category,
        f.price_id,
        f.price_rub,
        f.price_rub / NULLIF(f.distance, 0)        AS price_km,
        f.organization_id,
        f.price_type
    FROM core_fact_prices f
    JOIN core_price_body_group g
        ON g.price_id = f.price_id
    JOIN core_dim_city lc
        ON lc.gc_id = f.loading_city_gcid
    JOIN core_dim_city uc
        ON uc.gc_id = f.unloading_city_gcid
    JOIN price_dates pd
        ON pd.price_id = f.price_id
    WHERE f.is_fact = true
      AND f.complex = false
      AND f.price_rub > 0
      AND f.distance > 0
      AND f.outlier_mark = false
      AND pd.price_date <= DATE '2026-10-26'
),
monthly AS (
    SELECT
        month,
        loading_city_gcid,
        unloading_city_gcid,
        max(loading_city_name)                                             AS loading_city_name,
        max(unloading_city_name)                                            AS unloading_city_name,
        body_group,
        weight_category,

        percentile_cont(0.25) WITHIN GROUP (ORDER BY price_rub)             AS p25_trip,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY price_rub)             AS median_trip,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY price_rub)             AS p75_trip,
        avg(price_rub)                                                      AS avg_trip,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY price_km)              AS p25_km,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY price_km)              AS median_km,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY price_km)              AS p75_km,

        count(DISTINCT price_id)                                            AS trips_count,
        count(DISTINCT organization_id) FILTER (WHERE price_type IN (3, 9)) AS carriers_count,

        CASE
            WHEN count(*) >= 2 AND avg(price_rub) <> 0
                THEN stddev_samp(price_rub) / avg(price_rub)
            ELSE NULL
        END                                                                 AS cv_rate
    FROM base
    GROUP BY month, loading_city_gcid, unloading_city_gcid, body_group, weight_category
)
SELECT
    m.month,
    m.loading_city_gcid,
    m.unloading_city_gcid,
    m.loading_city_name,
    m.unloading_city_name,
    m.body_group,
    m.weight_category,

    round(m.p25_trip::numeric,    2) AS p25_trip,
    round(m.median_trip::numeric,  2) AS median_trip,
    round(m.p75_trip::numeric,     2) AS p75_trip,
    round(m.avg_trip::numeric,     2) AS avg_trip,
    round(m.p25_km::numeric,       2) AS p25_km,
    round(m.median_km::numeric,    2) AS median_km,
    round(m.p75_km::numeric,       2) AS p75_km,

    m.trips_count,
    m.carriers_count,
    round(m.cv_rate::numeric, 4)    AS cv_rate,

    -- MoM: P50 change vs previous calendar month (NULL if cell missing / denominator 0)
    CASE
        WHEN pm.median_trip IS NULL OR pm.median_trip = 0
            THEN NULL
        ELSE round(((m.median_trip - pm.median_trip) / pm.median_trip * 100)::numeric, 2)
    END AS mom_pct,

    -- YoY: P50 change vs same month last year
    CASE
        WHEN py.median_trip IS NULL OR py.median_trip = 0
            THEN NULL
        ELSE round(((m.median_trip - py.median_trip) / py.median_trip * 100)::numeric, 2)
    END AS yoy_pct,

    -- reliability level
    CASE
        WHEN m.trips_count >= 30
         AND m.carriers_count >= 5
         AND (DATE '2026-10-26' - m.month) <= 30
            THEN 'HIGH'
        WHEN m.trips_count >= 10
            THEN 'MEDIUM'
        ELSE 'LOW_DATA'
    END AS reliability_level
FROM monthly m
LEFT JOIN monthly pm
    ON  pm.loading_city_gcid   = m.loading_city_gcid
    AND pm.unloading_city_gcid = m.unloading_city_gcid
    AND pm.body_group          = m.body_group
    AND pm.weight_category     = m.weight_category
    AND pm.month               = m.month - INTERVAL '1 month'
LEFT JOIN monthly py
    ON  py.loading_city_gcid   = m.loading_city_gcid
    AND py.unloading_city_gcid = m.unloading_city_gcid
    AND py.body_group          = m.body_group
    AND py.weight_category     = m.weight_category
    AND py.month               = m.month - INTERVAL '12 months';

COMMIT;

-- -----------------------------------------------------------------------------
-- Smoke check.
-- -----------------------------------------------------------------------------
SELECT
    count(*)                        AS mart_rows,
    count(DISTINCT month)           AS months,
    count(DISTINCT loading_city_gcid)   AS cities,
    count(DISTINCT body_group)      AS body_groups
FROM mart_route_card;
