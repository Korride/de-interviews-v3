# -*- coding: utf-8 -*-
"""Unit tests for the central constants module (guards against typos/regressions)."""
import constants as c


def test_weight_category_bounds_are_descending_and_labelled():
    thresholds = [bound for bound, _ in c.WEIGHT_CATEGORY_BOUNDS]
    labels = [label for _, label in c.WEIGHT_CATEGORY_BOUNDS]
    assert thresholds == sorted(thresholds, reverse=True), "bounds must be descending"
    assert len(set(labels)) == len(labels), "labels must be unique"
    assert c.WEIGHT_CATEGORY_DEFAULT not in labels


def test_currency_codes():
    assert c.CURRENCY_RUB == "643"
    assert c.FOREIGN_CURRENCIES == frozenset({c.CURRENCY_USD, c.CURRENCY_EUR})
    assert c.CURRENCY_RUB not in c.FOREIGN_CURRENCIES
    assert c.RUB_RATE == 1.0


def test_reason_priority_is_stable():
    assert isinstance(c.REASON_PRIORITY, tuple)
    assert c.REASON_PRIORITY[0] == c.REASON_INVALID_PRICE
    assert c.REASON_PRIORITY[-1] == c.REASON_MISSING_RATE
    assert len(set(c.REASON_PRIORITY)) == len(c.REASON_PRIORITY)


def test_body_group_mapping():
    assert c.BODY_GROUP_BY_STD_ID == {
        56: "Тент", 4: "Рефрижератор", 2: "Изотерм", 15: "Борт",
    }
    assert c.BODY_GROUP_OTHER not in c.BODY_GROUP_BY_STD_ID.values()
    assert c.BODY_GROUP_UNKNOWN not in c.BODY_GROUP_BY_STD_ID.values()


def test_column_lists_have_no_duplicates_and_valid_keys():
    for name, cols in (
        ("CORE_FACT_COLUMNS", c.CORE_FACT_COLUMNS),
        ("PREDICTION_COLUMNS", c.PREDICTION_COLUMNS),
        ("QUARANTINE_COLUMNS", c.QUARANTINE_COLUMNS),
    ):
        assert len(set(cols)) == len(cols), f"{name} contains duplicates"
    assert c.CORE_FACT_COLUMNS[0] == "price_id"
    assert c.PREDICTION_COLUMNS[0] == "price_id"       # upsert conflict key
    assert "reason_code" in c.QUARANTINE_COLUMNS


def test_feature_columns_are_numeric_plus_categorical():
    assert c.FEATURE_COLUMNS == c.NUMERIC_FEATURES + c.CATEGORICAL_FEATURES
    assert c.TARGET not in c.FEATURE_COLUMNS
    assert "outlier_mark" not in c.FEATURE_COLUMNS


def test_etl_param_keys_match_sql_contract():
    # These keys must exist in core.etl_params (see sql/ddl_core.sql).
    keys = {
        c.PARAM_AS_OF_DATE, c.PARAM_FRESHNESS_DAYS,
        c.PARAM_RELIABILITY_HIGH_TRIPS, c.PARAM_RELIABILITY_HIGH_CARRIERS,
        c.PARAM_RELIABILITY_MEDIUM_TRIPS,
        c.PARAM_RELIABILITY_HIGH, c.PARAM_RELIABILITY_MEDIUM, c.PARAM_RELIABILITY_LOW,
        c.PARAM_RUB_MIN_PRICE, c.PARAM_VOLUME_FTL_MAX,
        c.PARAM_BODY_GROUP_OTHER, c.PARAM_BODY_GROUP_UNKNOWN,
    }
    assert len(keys) == 12
    assert c.PARAM_AS_OF_DATE == "as_of_date"
