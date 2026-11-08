-- =============================================================================
--  Idempotency check: after a repeated run, counts must not double.
-- =============================================================================

SET search_path TO "TEST_V3";

SELECT
    (SELECT count(*)                FROM core_fact_prices)      AS core_rows,
    (SELECT count(DISTINCT price_id) FROM core_fact_prices)      AS core_distinct,
    (SELECT count(*)                FROM dq_quarantine_prices)   AS dq_rows,
    (SELECT count(*)                FROM etl_batch_log)          AS batch_log_rows;
