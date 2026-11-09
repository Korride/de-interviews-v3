-- =============================================================================
--  Verification of the Question 3 ML predictions (mart.ml_price_predictions).
-- =============================================================================

-- === prediction table breakdown ===
SELECT
    count(*)                                            AS total,
    count(*) FILTER (WHERE actual_price_rub IS NOT NULL) AS test_rows,
    count(*) FILTER (WHERE actual_price_rub IS NULL)      AS future_rows
FROM mart.ml_price_predictions;

-- === future rows must have NULL actual/error/ape ===
SELECT
    count(*) AS future_with_null_err
FROM mart.ml_price_predictions
WHERE actual_price_rub IS NULL
  AND abs_error_rub IS NULL
  AND ape_pct IS NULL;

SELECT
    count(*) AS future_with_filled_err
FROM mart.ml_price_predictions
WHERE actual_price_rub IS NULL
  AND (abs_error_rub IS NOT NULL OR ape_pct IS NOT NULL);

-- === fact vs forecast sample (test period) ===
SELECT
    price_id,
    loading_date,
    loading_city_gcid                      AS lc,
    unloading_city_gcid                    AS uc,
    body_group,
    round(actual_price_rub::numeric)       AS actual,
    round(predicted_price_rub::numeric)    AS predicted,
    round(ape_pct::numeric, 1)             AS ape_pct
FROM mart.ml_price_predictions
WHERE actual_price_rub IS NOT NULL
ORDER BY price_id
LIMIT 8;

-- === aggregate error (cross-check with model metrics) ===
SELECT
    round(avg(ape_pct)::numeric, 2)        AS mean_ape_pct,
    round(avg(abs_error_rub)::numeric, 2)  AS mean_abs_error
FROM mart.ml_price_predictions
WHERE actual_price_rub IS NOT NULL;

-- === idempotency: distinct price_ids ===
SELECT
    count(*)                 AS total_rows,
    count(DISTINCT price_id) AS distinct_ids
FROM mart.ml_price_predictions;
