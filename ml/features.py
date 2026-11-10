# -*- coding: utf-8 -*-
"""Feature engineering for the tariff-prediction model (Question 3).

Leakage-free by construction:
  * reads only core.fact_prices (already cleaned, no price_group_stats);
  * uses outlier_mark ONLY to clean the target in main.py, never as a feature;
  * derives no per-deal rates (price/distance, price/weight) as features.

Все константы (даты, группы кузова, периоды, списки колонок) — в `constants.py`.
"""
import numpy as np
import pandas as pd

from constants import (
    AS_OF_DATE,
    BODY_GROUP_BY_STD_ID,
    BODY_GROUP_OTHER,
    BODY_GROUP_UNKNOWN,
    CATEGORICAL_FEATURES as _CATEGORICAL_FEATURES,
    FEATURE_COLUMNS as _FEATURE_COLUMNS,
    ML_CITY_COLUMNS,
    ML_FACT_COLUMNS,
    NUMERIC_FEATURES as _NUMERIC_FEATURES,
    PERIOD_MONTHS,
    PERIOD_WEEKDAYS,
    PERIOD_YEAR_DAYS,
    TABLE_DIM_CITY,
    TABLE_FACT_PRICES,
    TARGET as _TARGET,
    TEST_END as _TEST_END,
    TEST_START as _TEST_START,
    TRAIN_START as _TRAIN_START,
)
from etl.config import config

# --- Time split: expose as pandas Timestamps (assignment snapshot, NOT now()). ---
AS_OF = pd.Timestamp(AS_OF_DATE)
TRAIN_START = pd.Timestamp(_TRAIN_START)     # inclusive
TEST_START = pd.Timestamp(_TEST_START)       # inclusive (belongs to test)
TEST_END = pd.Timestamp(_TEST_END)           # inclusive

# --- Feature groups (re-exported for callers/tests). ---
NUMERIC_FEATURES = list(_NUMERIC_FEATURES)
CATEGORICAL_FEATURES = list(_CATEGORICAL_FEATURES)
FEATURE_COLUMNS = list(_FEATURE_COLUMNS)
TARGET = _TARGET

# --- Body-type (std_id) -> business group. ---
BODY_GROUP = dict(BODY_GROUP_BY_STD_ID)


def _cyclic(t: pd.Series, period: float):
    t = np.asarray(t, dtype=float)
    return np.sin(2 * np.pi * t / period), np.cos(2 * np.pi * t / period)


def _body_group(s: pd.Series) -> pd.Series:
    def f(x):
        if pd.isna(x):
            return BODY_GROUP_UNKNOWN
        return BODY_GROUP.get(int(x), BODY_GROUP_OTHER)
    return s.map(f)


def build_features(engine) -> pd.DataFrame:
    """Read enriched facts + dimensions from core and compute the feature set."""
    facts = pd.read_sql(
        f"""
        SELECT {", ".join(ML_FACT_COLUMNS)}
        FROM {config.core}.{TABLE_FACT_PRICES}
        ORDER BY price_id          -- deterministic row order (reproducible training)
        """,
        engine,
    )
    cities = pd.read_sql(
        f"""
        SELECT {", ".join(ML_CITY_COLUMNS)}
        FROM {config.core}.{TABLE_DIM_CITY}
        ORDER BY gc_id
        """,
        engine,
    )
    c = cities.set_index("gc_id")

    facts["loading_date"] = pd.to_datetime(facts["loading_date"])

    facts["origin_region"] = facts["loading_city_gcid"].map(c["region"])
    facts["dest_region"] = facts["unloading_city_gcid"].map(c["region"])
    facts["origin_lat"] = facts["loading_city_gcid"].map(c["latitude"])
    facts["origin_lon"] = facts["loading_city_gcid"].map(c["longitude"])
    facts["dest_lat"] = facts["unloading_city_gcid"].map(c["latitude"])
    facts["dest_lon"] = facts["unloading_city_gcid"].map(c["longitude"])

    facts["body_group"] = _body_group(facts["body_type"])

    dt = facts["loading_date"]
    facts["year"] = dt.dt.year
    facts["month_sin"], facts["month_cos"] = _cyclic(dt.dt.month, PERIOD_MONTHS)
    facts["dow_sin"], facts["dow_cos"] = _cyclic(dt.dt.dayofweek, PERIOD_WEEKDAYS)
    facts["doy_sin"], facts["doy_cos"] = _cyclic(dt.dt.dayofyear, PERIOD_YEAR_DAYS)

    return facts
