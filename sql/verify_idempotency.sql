-- =============================================================================
--  Idempotency check: after a repeated run, counts must not double.
-- =============================================================================

SELECT
    (SELECT count(*)                 FROM core.fact_prices)        AS core_rows,
    (SELECT count(DISTINCT price_id) FROM core.fact_prices)        AS core_distinct,
    (SELECT count(*)                 FROM core.dq_quarantine_prices) AS dq_rows,
    (SELECT count(*)                 FROM core.etl_batch_log)      AS batch_log_rows;
