# -*- coding: utf-8 -*-
"""Feature engineering for the tariff-prediction model (Question 3).

Leakage-free by construction:
  * reads only core_fact_prices (already cleaned, no price_group_stats);
  * uses outlier_mark ONLY to clean the target in main.py, never as a feature;
  * derives no per-deal rates (price/distance, price/weight) as features.
"""
import numpy as np
import pandas as pd

#: Fixed snapshot date of the assignment (NOT the system date).
AS_OF = pd.Timestamp("2026-10-26")

#: Train / test boundaries (strict time-based split).
TRAIN_START = pd.Timestamp("2026-07-26")   # inclusive
TEST_START = pd.Timestamp("2026-10-05")    # inclusive (belongs to test)
TEST_END = AS_OF                            # inclusive

#: Primary body-type (std_id) -> business group.
BODY_GROUP = {56: "Тент", 4: "Рефрижератор", 2: "Изотерм", 15: "Борт"}

NUMERIC_FEATURES = [
    "distance", "total_weight", "total_volume",
    "origin_lat", "origin_lon", "dest_lat", "dest_lon",
    "year",
    "month_sin", "month_cos",
    "dow_sin", "dow_cos",
    "doy_sin", "doy_cos",
]

CATEGORICAL_FEATURES = [
    "body_group", "weight_category", "volume_category",
    "origin_region", "dest_region",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "price_rub"


def _cyclic(t: pd.Series, period: float):
    t = np.asarray(t, dtype=float)
    return np.sin(2 * np.pi * t / period), np.cos(2 * np.pi * t / period)


def _body_group(s: pd.Series) -> pd.Series:
    def f(x):
        if pd.isna(x):
            return "Не указан"
        return BODY_GROUP.get(int(x), "Прочие")
    return s.map(f)


def build_features(engine, schema: str) -> pd.DataFrame:
    """Read enriched facts + dimensions and compute the full feature set."""
    facts = pd.read_sql(
        f"""
        SELECT price_id, loading_date, loading_city_gcid, unloading_city_gcid,
               distance, total_weight, total_volume, body_type,
               weight_category, volume_category, price_rub,
               is_fact, complex, outlier_mark
        FROM {schema}.core_fact_prices
        """,
        engine,
    )
    cities = pd.read_sql(
        f"SELECT gc_id, latitude, longitude, region FROM {schema}.core_dim_city",
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
    facts["month_sin"], facts["month_cos"] = _cyclic(dt.dt.month, 12.0)
    facts["dow_sin"], facts["dow_cos"] = _cyclic(dt.dt.dayofweek, 7.0)
    facts["doy_sin"], facts["doy_cos"] = _cyclic(dt.dt.dayofyear, 365.25)

    return facts
