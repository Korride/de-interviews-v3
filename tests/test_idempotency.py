# -*- coding: utf-8 -*-
"""Integration (DB-backed) smoke tests: idempotency & data integrity.

Run with a live PostgreSQL (set via .env or env vars). Skip via:
    pytest -m "not integration"
"""
import pytest
from sqlalchemy import create_engine, text

from etl.config import config
from etl.dq import REASON_PRIORITY

S = config.schema_quoted


def _scalar(engine, sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(config.sqlalchemy_url)
    yield eng
    eng.dispose()


@pytest.mark.integration
def test_core_fact_prices_no_duplicates(engine):
    total = _scalar(engine, f"SELECT count(*) FROM {S}.core_fact_prices")
    distinct = _scalar(engine, f"SELECT count(DISTINCT price_id) FROM {S}.core_fact_prices")
    assert total == distinct
    assert total > 0


@pytest.mark.integration
def test_quarantine_reason_codes_valid(engine):
    codes = set()
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT DISTINCT reason_code FROM {S}.dq_quarantine_prices"))
        codes = {r[0] for r in rows}
    assert codes <= set(REASON_PRIORITY)
    assert codes  # not empty


@pytest.mark.integration
def test_mart_route_card_grain_unique(engine):
    total = _scalar(engine, f"SELECT count(*) FROM {S}.mart_route_card")
    distinct = _scalar(
        engine,
        f"""
        SELECT count(*) FROM (
            SELECT DISTINCT month, loading_city_gcid, unloading_city_gcid,
                            body_group, weight_category
            FROM {S}.mart_route_card
        ) t
        """,
    )
    assert total == distinct


@pytest.mark.integration
def test_ml_predictions_no_duplicates(engine):
    total = _scalar(engine, f"SELECT count(*) FROM {S}.ml_price_predictions")
    distinct = _scalar(engine, f"SELECT count(DISTINCT price_id) FROM {S}.ml_price_predictions")
    assert total == distinct


@pytest.mark.integration
def test_future_predictions_have_null_errors(engine):
    bad = _scalar(
        engine,
        f"""
        SELECT count(*) FROM {S}.ml_price_predictions
        WHERE actual_price_rub IS NULL
          AND (abs_error_rub IS NOT NULL OR ape_pct IS NOT NULL)
        """,
    )
    assert bad == 0
