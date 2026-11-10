-- =============================================================================
--  Analytical layer DDL — «Smart Logistics» test assignment.
--  Layers: raw (source) -> core (cleaned facts) -> mart (analytics + ML).
--  PostgreSQL 17+.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS core;

SET search_path TO core;

-- -----------------------------------------------------------------------------
-- 1. DQ quarantine — every rejected record is saved with a reason code.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dq_quarantine_prices (
    id             bigserial    PRIMARY KEY,
    price_id       bigint       NOT NULL,
    reason_code    varchar(40)  NOT NULL,
    description    text,
    quarantined_at timestamp(0) NOT NULL DEFAULT now(),
    UNIQUE (price_id, reason_code)
);

CREATE INDEX IF NOT EXISTS dq_quarantine_reason_idx
    ON dq_quarantine_prices (reason_code);

-- -----------------------------------------------------------------------------
-- 2. Deduplicated city dimension (source raw.cities.gc_id is NOT unique).
--    Keeps the row with minimal cities.id per gc_id.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_city (
    city_id         bigint PRIMARY KEY,          -- = minimal cities.id for the gc_id
    gc_id           integer      NOT NULL UNIQUE,
    name            varchar(255),
    city_name       varchar(255),               -- name before the first comma
    region          varchar(255),               -- region after the first comma
    full_name_local varchar(255),
    latitude        double precision,
    longitude       double precision
);

-- -----------------------------------------------------------------------------
-- 3. Cleaned & enriched fact table (one row = one deal; price_rub converted).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_prices (
    price_id            bigint PRIMARY KEY,
    loading_date        date,
    end_loading_date    date,
    loading_city_gcid   integer,
    unloading_city_gcid integer,
    loading_city_id     bigint,                  -- deduplicated city key
    unloading_city_id   bigint,
    distance            double precision,
    total_weight        double precision,
    total_volume        double precision,
    body_type           integer,
    currency_code       varchar(3),
    price_original      double precision,        -- price in the source currency
    exchange_rate       double precision,        -- applied CBR rate (1.0 for RUB)
    price_rub           double precision,        -- price in RUB, excl. VAT
    price_type          smallint,
    is_fact             boolean,
    complex             boolean,
    organization_id     integer,
    subscriber_id       integer,
    outlier_mark        boolean,
    weight_category     varchar(4),
    volume_category     varchar(4),
    source              varchar(255),
    loaded_at           timestamp(0) NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fact_prices_loading_date_idx
    ON fact_prices (loading_date);

CREATE INDEX IF NOT EXISTS fact_prices_route_idx
    ON fact_prices (loading_city_gcid, unloading_city_gcid);

CREATE INDEX IF NOT EXISTS fact_prices_outlier_idx
    ON fact_prices (outlier_mark);

-- -----------------------------------------------------------------------------
-- 4. Body-group resolution bridge. One price may fan out into several
--    standardized business groups; unique per group per price.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_body_group (
    price_id         bigint      NOT NULL,
    body_group       varchar(20) NOT NULL,        -- Тент / Рефрижератор / Изотерм / Борт / Прочие / Не указан
    body_type_std_id integer,
    PRIMARY KEY (price_id, body_group)
);

-- -----------------------------------------------------------------------------
-- 5. ETL batch log — idempotency + structured logging of every run.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_batch_log (
    id               bigserial PRIMARY KEY,
    batch_start      date,
    batch_end        date,
    status           varchar(16),                 -- running / success / failed
    rows_read        bigint,
    rows_loaded      bigint,
    rows_quarantined bigint,
    started_at       timestamp(0) DEFAULT now(),
    finished_at      timestamp(0)
);

-- -----------------------------------------------------------------------------
-- 6. Reference: body-type std_id -> business group.
--    Single source of truth for SQL marts (no CASE literals in queries).
--    Kept in sync with constants.py (BODY_GROUP_BY_STD_ID).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ref_body_group (
    std_id     integer     PRIMARY KEY,
    body_group varchar(20) NOT NULL
);

INSERT INTO ref_body_group (std_id, body_group) VALUES
    (56, 'Тент'),
    (4,  'Рефрижератор'),
    (2,  'Изотерм'),
    (15, 'Борт')
ON CONFLICT (std_id) DO UPDATE SET body_group = EXCLUDED.body_group;

-- -----------------------------------------------------------------------------
-- 7. Reference: business parameters (as_of, thresholds, labels).
--    Single source of truth for SQL marts (no magic numbers in queries).
--    Keys match constants.py (PARAM_*).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_params (
    param varchar(40) PRIMARY KEY,
    value text        NOT NULL
);

INSERT INTO etl_params (param, value) VALUES
    ('as_of_date',                  '2026-10-26'),
    ('freshness_days',              '30'),
    ('reliability_high_trips',      '30'),
    ('reliability_high_carriers',   '5'),
    ('reliability_medium_trips',    '10'),
    ('reliability_level_high',      'HIGH'),
    ('reliability_level_medium',    'MEDIUM'),
    ('reliability_level_low',       'LOW_DATA'),
    ('rub_min_price',               '1000'),
    ('volume_ftl_max',              '120'),
    ('body_group_other',            'Прочие'),
    ('body_group_unknown',          'Не указан')
ON CONFLICT (param) DO UPDATE SET value = EXCLUDED.value;
