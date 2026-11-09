# -*- coding: utf-8 -*-
"""Question 1 ETL pipeline: extract -> validate/cleanse -> convert -> load Core DWH."""
import logging

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from etl.config import config
from etl.dq import (
    FOREIGN_CURRENCIES,
    REASON_PRIORITY,
    volume_category,
    weight_category,
)
from etl.load import log_batch, upsert_fact_prices, upsert_quarantine

logger = logging.getLogger("etl.pipeline")

RAW = config.raw      # raw layer, e.g. raw
CORE = config.core    # core layer, e.g. core


def _read_prices(engine, start_date, end_date) -> pd.DataFrame:
    sql = f"""
        SELECT id, loading_date, end_loading_date,
               loading_city_gcid, unloading_city_gcid,
               distance, total_weight, total_volume, body_type,
               price, currency_code, complex, price_type, is_fact,
               nearest_rate_date, organization_id, subscriber_id,
               outlier_mark, weight_category, volume_category, source
        FROM {RAW}.prices
    """
    where, params = [], {}
    if start_date:
        where.append("loading_date >= %(start)s")
        params["start"] = start_date
    if end_date:
        where.append("loading_date <= %(end)s")
        params["end"] = end_date
    if where:
        sql += " WHERE " + " AND ".join(where)
    return pd.read_sql(sql, engine, params=params)


def _read_rates(engine) -> pd.DataFrame:
    return pd.read_sql(
        f"SELECT num_code, setting_date, value FROM {RAW}.exchange_rates", engine
    )


def _read_city_keys(engine) -> pd.DataFrame:
    return pd.read_sql(f"SELECT gc_id, city_id FROM {CORE}.dim_city", engine)


def _transform(raw: pd.DataFrame, rates: pd.DataFrame, city_keys: pd.DataFrame):
    """Return (df, bad_mask). `df` carries enriched columns + `_reason` for bad rows."""
    df = raw.rename(columns={"id": "price_id"})

    # --- Category enrichment (recomputed by business rules) ---
    df["weight_category"] = weight_category(df["total_weight"])
    df["volume_category"] = volume_category(df["total_volume"])

    # --- Currency conversion: exact rate by nearest_rate_date; RUB = 1.0 ---
    r = rates.rename(
        columns={"num_code": "currency_code", "setting_date": "nearest_rate_date"}
    )[["currency_code", "nearest_rate_date", "value"]]
    df = df.merge(r, how="left", on=["currency_code", "nearest_rate_date"])
    df["exchange_rate"] = np.where(df["currency_code"] == "643", 1.0, df["value"])

    # --- City validation + deduplicated city keys ---
    city_map = city_keys.set_index("gc_id")["city_id"].to_dict()
    valid_gcids = set(city_map.keys())
    df["loading_city_id"] = df["loading_city_gcid"].map(city_map)
    df["unloading_city_id"] = df["unloading_city_gcid"].map(city_map)

    # --- DQ flags ---
    foreign = df["currency_code"].isin(FOREIGN_CURRENCIES)
    flags = {
        "INVALID_PRICE": df["price"] <= 0,
        "RUB_PRICE_TOO_LOW": (df["currency_code"] == "643") & (df["price"] <= 1000) & (df["price"] > 0),
        "INVALID_DISTANCE": df["distance"] <= 0,
        "INVALID_WEIGHT_VOLUME": (df["total_weight"] < 0) | (df["total_volume"] < 0),
        "UNKNOWN_CITY": ~df["loading_city_gcid"].isin(valid_gcids)
                        | ~df["unloading_city_gcid"].isin(valid_gcids),
        "MISSING_RATE": foreign & df["exchange_rate"].isna(),
    }

    # Single reason per row (priority order, first match wins).
    df["_reason"] = None
    for reason in REASON_PRIORITY:
        df.loc[flags[reason] & df["_reason"].isna(), "_reason"] = reason

    bad_mask = df["_reason"].notna()

    # --- price_rub (only for clean rows; RUB without VAT) ---
    df["price_rub"] = np.round(df["price"] * df["exchange_rate"], 2)
    df.loc[bad_mask, "price_rub"] = np.nan

    return df, bad_mask


def run_pipeline(start_date=None, end_date=None):
    engine = create_engine(config.sqlalchemy_url)

    raw = _read_prices(engine, start_date, end_date)
    logger.info("Read %d rows from prices (window %s..%s)",
                len(raw), start_date or "min", end_date or "max")

    if raw.empty:
        logger.warning("Nothing to process; exiting")
        return

    rates = _read_rates(engine)
    city_keys = _read_city_keys(engine)
    df, bad_mask = _transform(raw, rates, city_keys)

    good = df[~bad_mask]
    bad = df[bad_mask]

    # Summary per reason
    reason_counts = bad["_reason"].value_counts().to_dict()

    with engine.begin() as conn:
        quarantine_df = bad[["price_id", "_reason"]].rename(
            columns={"_reason": "reason_code"}
        )
        upsert_quarantine(conn, CORE, quarantine_df)

        core_cols = [
            "price_id", "loading_date", "end_loading_date",
            "loading_city_gcid", "unloading_city_gcid",
            "loading_city_id", "unloading_city_id",
            "distance", "total_weight", "total_volume", "body_type",
            "currency_code", "price_original", "exchange_rate", "price_rub",
            "price_type", "is_fact", "complex", "organization_id",
            "subscriber_id", "outlier_mark", "weight_category",
            "volume_category", "source",
        ]
        good = good.assign(price_original=good["price"])
        upsert_fact_prices(conn, CORE, good[core_cols])

        log_batch(conn, CORE, start_date, end_date, "success",
                  len(raw), len(good), len(bad))

    # Output summary
    print("=" * 60)
    print("ETL run summary (Question 1)")
    print("=" * 60)
    print(f"window           : {start_date or 'min'} .. {end_date or 'max'}")
    print(f"rows read        : {len(raw)}")
    print(f"rows loaded      : {len(good)}")
    print(f"rows quarantined : {len(bad)}")
    for reason in REASON_PRIORITY:
        n = reason_counts.get(reason, 0)
        if n:
            print(f"  - {reason:<20} {n}")
    print("=" * 60)

    engine.dispose()
    return {"read": len(raw), "loaded": len(good), "quarantined": len(bad)}
