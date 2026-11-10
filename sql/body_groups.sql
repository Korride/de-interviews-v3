-- =============================================================================
--  Question 2: body-type unification.
--  Maps many-to-many raw.price_body_types -> business groups via the
--  reference table core.ref_body_group (std_id -> group name), with fallback
--  to raw.prices.body_type and finally to the 'unknown' group.
--  All group names / fallbacks come from core.ref_body_group + core.etl_params,
--  so this file contains no magic literals.
--  Idempotent: TRUNCATE + INSERT inside one transaction.
-- =============================================================================

SET search_path TO core;

BEGIN;

TRUNCATE price_body_group;

INSERT INTO price_body_group (price_id, body_group, body_type_std_id)

-- 1) primary path: raw.price_body_types -> raw.body_types -> std_id -> group
SELECT
    pbt.price_id,
    COALESCE(rbg.body_group, other.body_group_other) AS body_group,
    bt.std_id                                        AS body_type_std_id
FROM raw.price_body_types pbt
JOIN raw.body_types bt
    ON bt.id = pbt.body_type_id
LEFT JOIN core.ref_body_group rbg
    ON rbg.std_id = bt.std_id
CROSS JOIN (
    SELECT value AS body_group_other
    FROM core.etl_params
    WHERE param = 'body_group_other'
) other

UNION   -- UNION dedups identical (price_id, body_group, std_id): prevents
        -- double-counting one price inside one group (e.g. Тент 56 + Тент 61).

-- 2) fallback: prices with body_type but no price_body_types rows
SELECT
    p.id,
    COALESCE(rbg.body_group, other.body_group_other) AS body_group,
    p.body_type                                      AS body_type_std_id
FROM raw.prices p
LEFT JOIN core.ref_body_group rbg
    ON rbg.std_id = p.body_type
CROSS JOIN (
    SELECT value AS body_group_other
    FROM core.etl_params
    WHERE param = 'body_group_other'
) other
WHERE p.body_type IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM raw.price_body_types pb
        WHERE pb.price_id = p.id
  )

UNION

-- 3) fallback: NULL body_type and no price_body_types -> 'unknown' group
SELECT
    p.id,
    unknown.body_group_unknown AS body_group,
    NULL::integer              AS body_type_std_id
FROM raw.prices p
CROSS JOIN (
    SELECT value AS body_group_unknown
    FROM core.etl_params
    WHERE param = 'body_group_unknown'
) unknown
WHERE p.body_type IS NULL
  AND NOT EXISTS (
        SELECT 1
        FROM raw.price_body_types pb
        WHERE pb.price_id = p.id
  );

COMMIT;

-- -----------------------------------------------------------------------------
-- Smoke check: distribution by business group.
-- -----------------------------------------------------------------------------
SELECT
    body_group,
    count(*)                    AS prices,
    count(DISTINCT price_id)    AS distinct_prices
FROM price_body_group
GROUP BY body_group
ORDER BY body_group;
