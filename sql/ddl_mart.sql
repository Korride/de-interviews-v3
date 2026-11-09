-- =============================================================================
--  Analytical mart + ML tables for the «Smart Logistics» test assignment.
--  Layer: mart (built on top of core).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS mart;

SET search_path TO mart;

-- -----------------------------------------------------------------------------
-- 1. Route card / market corridor mart.
--    grain: month x loading city x unloading city x body_group x weight_category
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS route_card (
    month               date        NOT NULL,
    loading_city_gcid   integer     NOT NULL,
    unloading_city_gcid integer     NOT NULL,
    loading_city_name   varchar(255),
    unloading_city_name varchar(255),
    body_group          varchar(20) NOT NULL,
    weight_category     varchar(4)  NOT NULL,

    -- market corridor, RUB excl. VAT
    p25_trip    double precision,
    median_trip double precision,
    p75_trip    double precision,
    avg_trip    double precision,
    p25_km      double precision,
    median_km   double precision,
    p75_km      double precision,

    -- data trust / evidence base
    trips_count       bigint,
    carriers_count    bigint,
    cv_rate           double precision,
    mom_pct           double precision,
    yoy_pct           double precision,
    reliability_level varchar(16),

    PRIMARY KEY (
        month, loading_city_gcid, unloading_city_gcid, body_group, weight_category
    )
);

CREATE INDEX IF NOT EXISTS route_card_month_idx
    ON route_card (month);

-- -----------------------------------------------------------------------------
-- 2. ML batch-inference predictions (fact vs forecast).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ml_price_predictions (
    price_id            bigint PRIMARY KEY,
    loading_date        date,
    loading_city_gcid   integer,
    unloading_city_gcid integer,
    body_group          varchar(20),
    actual_price_rub    double precision,        -- NULL for future planned deals
    predicted_price_rub double precision,
    abs_error_rub       double precision,        -- NULL for future deals
    ape_pct             double precision,        -- NULL for future deals
    model_name          varchar(64),
    scored_at           timestamp(0) DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ml_predictions_loading_date_idx
    ON ml_price_predictions (loading_date);
