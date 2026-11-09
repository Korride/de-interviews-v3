-- =============================================================================
--  Question 2: body-type unification.
--  Maps many-to-many raw.price_body_types -> business groups (by std_id),
--  with fallback to raw.prices.body_type and finally to 'Не указан'.
--  Idempotent: TRUNCATE + INSERT inside one transaction.
-- =============================================================================

SET search_path TO core;

BEGIN;

TRUNCATE price_body_group;

INSERT INTO price_body_group (price_id, body_group, body_type_std_id)

-- 1) primary path: raw.price_body_types -> raw.body_types -> std_id -> group
SELECT
    pbt.price_id,
    CASE bt.std_id
        WHEN 56 THEN 'Тент'
        WHEN 4  THEN 'Рефрижератор'
        WHEN 2  THEN 'Изотерм'
        WHEN 15 THEN 'Борт'
        ELSE 'Прочие'
    END             AS body_group,
    bt.std_id       AS body_type_std_id
FROM raw.price_body_types pbt
JOIN raw.body_types bt
    ON bt.id = pbt.body_type_id

UNION   -- UNION dedups identical (price_id, body_group, std_id): prevents
        -- double-counting one price inside one group (e.g. Тент 56 + Тент 61).

-- 2) fallback: prices with body_type but no price_body_types rows
SELECT
    p.id,
    CASE p.body_type
        WHEN 56 THEN 'Тент'
        WHEN 4  THEN 'Рефрижератор'
        WHEN 2  THEN 'Изотерм'
        WHEN 15 THEN 'Борт'
        ELSE 'Прочие'
    END         AS body_group,
    p.body_type AS body_type_std_id
FROM raw.prices p
WHERE p.body_type IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM raw.price_body_types pb
        WHERE pb.price_id = p.id
  )

UNION

-- 3) fallback: NULL body_type and no price_body_types -> 'Не указан'
SELECT
    p.id,
    'Не указан'     AS body_group,
    NULL::integer   AS body_type_std_id
FROM raw.prices p
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
