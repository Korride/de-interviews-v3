SET search_path TO "TEST_V3";
ALTER TABLE dq_quarantine_prices
    ADD CONSTRAINT dq_quarantine_unique UNIQUE (price_id, reason_code);
