-- =============================================================================
--  Verification of the Question 1 ETL results.
-- =============================================================================

SET search_path TO "TEST_V3";

\echo '=== core_fact_prices ==='
SELECT
    count(*)                                   AS total,
    count(*) FILTER (WHERE price_rub IS NULL)  AS null_price_rub,
    round(sum(price_rub)::numeric, 2)          AS sum_price_rub
FROM core_fact_prices;

\echo '=== dq_quarantine_prices (by reason) ==='
SELECT
    reason_code,
    count(*) AS n
FROM dq_quarantine_prices
GROUP BY reason_code
ORDER BY reason_code;

\echo '=== etl_batch_log ==='
SELECT
    id,
    batch_start,
    batch_end,
    status,
    rows_read,
    rows_loaded,
    rows_quarantined,
    finished_at
FROM etl_batch_log
ORDER BY id;

\echo '=== currencies in core (sanity) ==='
SELECT
    currency_code,
    count(*)                                 AS n,
    round(avg(exchange_rate)::numeric, 4)    AS avg_rate
FROM core_fact_prices
GROUP BY currency_code
ORDER BY currency_code;
