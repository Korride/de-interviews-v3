-- =============================================================================
--  Populate the deduplicated city dimension: keep min(cities.id) per gc_id.
-- =============================================================================

SET search_path TO "TEST_V3";

INSERT INTO core_dim_city (
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
FROM cities
ORDER BY gc_id, id;

-- -----------------------------------------------------------------------------
-- Smoke check: expect 40 unique gc_id out of 42 source rows.
-- -----------------------------------------------------------------------------
SELECT
    count(*)                    AS cities_total,
    count(DISTINCT gc_id)       AS distinct_gc_id
FROM core_dim_city;
