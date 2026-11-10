# -*- coding: utf-8 -*-
"""Question 1 ETL pipeline: extract -> validate/cleanse -> convert -> load Core DWH.

Источник читается **потоково батчами** (server-side cursor через pandas
`chunksize`), поэтому потребление памяти ограничено размером чанка
(`ETL_READ_CHUNK_ROWS`), а не объёмом таблицы. Запись — пачками
`execute_values` (`BATCH_PAGE_SIZE`). Итоговое потребление: O(chunk).
"""
import logging
from collections import Counter

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from constants import (
    CORE_FACT_COLUMNS,
    CURRENCY_RUB,
    DISTANCE_MIN_EXCLUSIVE,
    FOREIGN_CURRENCIES,
    PRICE_MIN_EXCLUSIVE,
    PRICE_RUB_DECIMALS,
    REASON_INVALID_DISTANCE,
    REASON_INVALID_PRICE,
    REASON_INVALID_WEIGHT_VOLUME,
    REASON_MISSING_RATE,
    REASON_PRIORITY,
    REASON_RUB_PRICE_TOO_LOW,
    REASON_UNKNOWN_CITY,
    RUB_MIN_PRICE,
    RUB_RATE,
    TABLE_DIM_CITY,
    TABLE_EXCHANGE_RATES,
    TABLE_PRICES,
    VOLUME_MIN,
    WEIGHT_MIN,
)
from etl.config import config
from etl.dq import volume_category, weight_category
from etl.load import log_batch, upsert_fact_prices, upsert_quarantine

logger = logging.getLogger("etl.pipeline")

RAW = config.raw      # raw layer, e.g. raw
CORE = config.core    # core layer, e.g. core

#: Columns read from the source `prices` table.
PRICES_SOURCE_COLUMNS = (
    "id", "loading_date", "end_loading_date",
    "loading_city_gcid", "unloading_city_gcid",
    "distance", "total_weight", "total_volume", "body_type",
    "price", "currency_code", "complex", "price_type", "is_fact",
    "nearest_rate_date", "organization_id", "subscriber_id",
    "outlier_mark", "weight_category", "volume_category", "source",
)


def _iter_price_chunks(engine, start_date=None, end_date=None):
    """Stream source rows in bounded chunks (server-side cursor).

    Memory footprint is O(ETL_READ_CHUNK_ROWS), independent of table size.
    """
    select_list = ", ".join(PRICES_SOURCE_COLUMNS)
    sql = f"SELECT {select_list} FROM {RAW}.{TABLE_PRICES}"
    where, params = [], {}
    if start_date:
        where.append("loading_date >= %(start)s")
        params["start"] = start_date
    if end_date:
        where.append("loading_date <= %(end)s")
        params["end"] = end_date
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"          # deterministic order, uses the PK index

    yield from pd.read_sql(
        sql, engine, params=params, chunksize=config.ETL_READ_CHUNK_ROWS
    )


def _read_rates(engine) -> pd.DataFrame:
    return pd.read_sql(
        f"SELECT num_code, setting_date, value FROM {RAW}.{TABLE_EXCHANGE_RATES}", engine
    )


def _read_city_keys(engine) -> pd.DataFrame:
    return pd.read_sql(f"SELECT gc_id, city_id FROM {CORE}.{TABLE_DIM_CITY}", engine)


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
    df["exchange_rate"] = np.where(df["currency_code"] == CURRENCY_RUB, RUB_RATE, df["value"])

    # --- City validation + deduplicated city keys ---
    city_map = city_keys.set_index("gc_id")["city_id"].to_dict()
    valid_gcids = set(city_map.keys())
    df["loading_city_id"] = df["loading_city_gcid"].map(city_map)
    df["unloading_city_id"] = df["unloading_city_gcid"].map(city_map)

    # --- DQ flags (reason codes are constants) ---
    foreign = df["currency_code"].isin(FOREIGN_CURRENCIES)
    flags = {
        REASON_INVALID_PRICE: df["price"] <= PRICE_MIN_EXCLUSIVE,
        REASON_RUB_PRICE_TOO_LOW: (
            (df["currency_code"] == CURRENCY_RUB)
            & (df["price"] <= RUB_MIN_PRICE)
            & (df["price"] > PRICE_MIN_EXCLUSIVE)
        ),
        REASON_INVALID_DISTANCE: df["distance"] <= DISTANCE_MIN_EXCLUSIVE,
        REASON_INVALID_WEIGHT_VOLUME: (df["total_weight"] < WEIGHT_MIN)
                                      | (df["total_volume"] < VOLUME_MIN),
        REASON_UNKNOWN_CITY: ~df["loading_city_gcid"].isin(valid_gcids)
                             | ~df["unloading_city_gcid"].isin(valid_gcids),
        REASON_MISSING_RATE: foreign & df["exchange_rate"].isna(),
    }

    # Single reason per row (priority order, first match wins).
    df["_reason"] = None
    for reason in REASON_PRIORITY:
        df.loc[flags[reason] & df["_reason"].isna(), "_reason"] = reason

    bad_mask = df["_reason"].notna()

    # --- price_rub (only for clean rows; RUB without VAT) ---
    df["price_rub"] = np.round(df["price"] * df["exchange_rate"], PRICE_RUB_DECIMALS)
    df.loc[bad_mask, "price_rub"] = np.nan

    return df, bad_mask


def _peak_rss_mb():
    """Peak resident set size of this process, MB (Linux containers)."""
    try:
        import resource

        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except Exception:  # pragma: no cover - non-Unix platforms
        return None


def run_pipeline(start_date=None, end_date=None):
    engine = create_engine(config.sqlalchemy_url)

    # Dimensions are tiny (40 cities, ~2.7k rates) and are cached in memory.
    rates = _read_rates(engine)
    city_keys = _read_city_keys(engine)

    total_read = total_loaded = total_bad = 0
    reason_counts = Counter()

    # One transaction for the whole run; reads stream on a separate connection.
    with engine.begin() as conn:
        for chunk in _iter_price_chunks(engine, start_date, end_date):
            total_read += len(chunk)

            df, bad_mask = _transform(chunk, rates, city_keys)
            good = df[~bad_mask]
            bad = df[bad_mask]

            if not bad.empty:
                quarantine_df = bad[["price_id", "_reason"]].rename(
                    columns={"_reason": "reason_code"}
                )
                upsert_quarantine(conn, CORE, quarantine_df)
                reason_counts.update(bad["_reason"].value_counts().to_dict())

            if not good.empty:
                good = good.assign(price_original=good["price"])
                upsert_fact_prices(conn, CORE, good[list(CORE_FACT_COLUMNS)])

            total_loaded += len(good)
            total_bad += len(bad)

        if total_read == 0:
            logger.warning("Nothing to process; exiting")
            return {"read": 0, "loaded": 0, "quarantined": 0}

        log_batch(conn, CORE, start_date, end_date, "success",
                  total_read, total_loaded, total_bad)

    # Output summary
    peak_mb = _peak_rss_mb()
    print("=" * 60)
    print("ETL run summary (Question 1)")
    print("=" * 60)
    print(f"window           : {start_date or 'min'} .. {end_date or 'max'}")
    print(f"rows read        : {total_read}")
    print(f"rows loaded      : {total_loaded}")
    print(f"rows quarantined : {total_bad}")
    for reason in REASON_PRIORITY:
        n = reason_counts.get(reason, 0)
        if n:
            print(f"  - {reason:<20} {n}")
    if peak_mb is not None:
        print(f"peak RSS         : {peak_mb} MB")
    print("=" * 60)

    engine.dispose()
    return {"read": total_read, "loaded": total_loaded, "quarantined": total_bad}
