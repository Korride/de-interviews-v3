# -*- coding: utf-8 -*-
"""Unit tests for ML feature engineering and data-leakage prevention (ml.features)."""
import numpy as np
import pandas as pd

from ml.features import (
    AS_OF,
    BODY_GROUP,
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TEST_END,
    TEST_START,
    TRAIN_START,
    _body_group,
    _cyclic,
)

#: Anything derived from the target (or the target itself) must never be a feature.
FORBIDDEN_FEATURES = {
    "price_rub", "price", "price_original", "price_with_vat",
    "price_km", "price_rub_per_km", "price_per_weight",
    "carrier_cost", "customer_cost", "profit",
    "outlier_mark", "price_group_id",
    "avg_price", "min_km_price", "max_km_price",
}


def test_feature_columns_consistency():
    assert FEATURE_COLUMNS == NUMERIC_FEATURES + CATEGORICAL_FEATURES


def test_no_target_leakage_in_features():
    for forbidden in FORBIDDEN_FEATURES:
        assert forbidden not in FEATURE_COLUMNS, f"leaky feature: {forbidden}"
    # target itself must not be a feature
    assert "price_rub" not in NUMERIC_FEATURES
    # outlier flag is used only for target cleaning, never as a feature
    assert "outlier_mark" not in FEATURE_COLUMNS


def test_time_split_boundaries():
    assert TRAIN_START == pd.Timestamp("2026-07-26")
    assert TEST_START == pd.Timestamp("2026-10-05")
    assert TEST_END == pd.Timestamp("2026-10-26")
    assert AS_OF == pd.Timestamp("2026-10-26")
    # train strictly precedes test; boundary 2026-10-05 belongs to test only
    assert TRAIN_START < TEST_START <= TEST_END


def test_body_group_mapping():
    assert BODY_GROUP[56] == "Тент"
    assert BODY_GROUP[4] == "Рефрижератор"
    assert BODY_GROUP[2] == "Изотерм"
    assert BODY_GROUP[15] == "Борт"

    s = pd.Series([56, 4, 2, 15, 3, 50, 68, None])
    assert list(_body_group(s)) == [
        "Тент", "Рефрижератор", "Изотерм", "Борт", "Прочие", "Прочие", "Прочие", "Не указан",
    ]


def test_cyclic_encoding_range_and_periodicity():
    t = pd.Series([0, 3, 6, 9, 12])  # months, T = 12
    sin, cos = _cyclic(t, 12)
    assert np.all((sin >= -1) & (sin <= 1))
    assert np.all((cos >= -1) & (cos <= 1))
    # periodicity: t=0 and t=12 map to the same angle
    assert abs(sin[0] - sin[4]) < 1e-9
    assert abs(cos[0] - cos[4]) < 1e-9
