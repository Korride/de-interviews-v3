-- =============================================================================
--  Populate the deduplicated city dimension: keep min(cities.id) per gc_id.
-- =============================================================================

SET search_path TO core;

-- Idempotent rebuild: the dimension is fully derived from raw.cities.
BEGIN;

TRUNCATE dim_city;

INSERT INTO dim_city (
    city_id,
    gc_id,
    name,
    city_name,
    region,
    full_name_local,
    latitude,
    longitude
)
SELECT DISTINCT ON (gc_id)
    id,
    gc_id,
    name,
    name,
    trim(split_part(full_name_local, ',', 2)) AS region,
    full_name_local,
    latitude,
    longitude
FROM raw.cities
ORDER BY gc_id, id;

COMMIT;

-- -----------------------------------------------------------------------------
-- Smoke check: expect 40 unique gc_id out of 42 source rows.
-- -----------------------------------------------------------------------------
SELECT
    count(*)                    AS cities_total,
    count(DISTINCT gc_id)       AS distinct_gc_id
FROM dim_city;
