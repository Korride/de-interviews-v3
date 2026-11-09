-- =============================================================================
--  Verification of the Question 1 ETL results.
-- =============================================================================

-- === core.fact_prices ===
SELECT
    count(*)                                   AS total,
    count(*) FILTER (WHERE price_rub IS NULL)  AS null_price_rub,
    round(sum(price_rub)::numeric, 2)          AS sum_price_rub
FROM core.fact_prices;

-- === core.dq_quarantine_prices (by reason) ===
SELECT
    reason_code,
    count(*) AS n
FROM core.dq_quarantine_prices
GROUP BY reason_code
ORDER BY reason_code;

-- === core.etl_batch_log ===
SELECT
    id,
    batch_start,
    batch_end,
    status,
    rows_read,
    rows_loaded,
    rows_quarantined,
    finished_at
FROM core.etl_batch_log
ORDER BY id;

-- === currencies in core (sanity) ===
SELECT
    currency_code,
    count(*)                                 AS n,
    round(avg(exchange_rate)::numeric, 4)    AS avg_rate
FROM core.fact_prices
GROUP BY currency_code
ORDER BY currency_code;
