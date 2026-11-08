# -*- coding: utf-8 -*-
"""Unit tests for DQ rules and category enrichment (etl.dq)."""
import pandas as pd

from etl.dq import REASON_PRIORITY, volume_category, weight_category


def test_weight_category_boundaries():
    weights = pd.Series([35.0, 30.0, 20.0, 10.0, 7.0, 5.0, 3.0, 2.5, 1.0, 0.5, 0.4])
    expected = ["G20T", "G20T", "FTL", "FTL", "10T", "10T", "5T", "5T", "L5T", "L5T", "OTH"]
    assert list(weight_category(weights)) == expected


def test_weight_category_rounding():
    # weights are rounded to 0.1 before the category is assigned
    s = pd.Series([9.96, 9.94])
    assert list(weight_category(s)) == ["FTL", "10T"]


def test_volume_category():
    volumes = pd.Series([0.0, 120.0, 120.1, 50.0, -1.0])
    expected = ["OTH", "FTL", "OTH", "FTL", "OTH"]
    assert list(volume_category(volumes)) == expected


def test_reason_priority_order():
    assert REASON_PRIORITY[0] == "INVALID_PRICE"
    assert REASON_PRIORITY[-1] == "MISSING_RATE"
    assert "RUB_PRICE_TOO_LOW" in REASON_PRIORITY
    assert "UNKNOWN_CITY" in REASON_PRIORITY
