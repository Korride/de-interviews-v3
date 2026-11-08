# -*- coding: utf-8 -*-
"""Idempotent batch loading into Core DWH (no row-by-row inserts).

Uses psycopg2.extras.execute_values with page_size batching, which internally
runs a single multi-row statement per page. Every load is an UPSERT:
  * core_fact_prices      -> ON CONFLICT (price_id) DO UPDATE
  * dq_quarantine_prices  -> ON CONFLICT (price_id, reason_code) DO NOTHING
"""
import datetime
import logging
import math

import numpy as np
import pandas as pd
from sqlalchemy.engine import Connection

logger = logging.getLogger("etl.load")


def _clean(value):
    """Convert numpy/pandas scalars to Python-native types (including NaN/NaT -> None)."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, np.datetime64) and np.isnat(value):
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    return value


def _tuples(df: pd.DataFrame, columns: list[str]):
    """Yield rows as tuples of Python-native values."""
    for row in df[columns].itertuples(index=False, name=None):
        yield tuple(_clean(v) for v in row)


def batch_execute_values(conn, sql: str, rows) -> int:
    from psycopg2.extras import execute_values

    rows = list(rows)
    if not rows:
        return 0
    raw = conn.connection
    with raw.cursor() as cur:
        execute_values(cur, sql, rows, page_size=10000)
    return len(rows)


def upsert_fact_prices(conn: Connection, schema: str, good_df: pd.DataFrame) -> int:
    """Upsert cleaned facts into {schema}.core_fact_prices."""
    columns = [
        "price_id", "loading_date", "end_loading_date",
        "loading_city_gcid", "unloading_city_gcid",
        "loading_city_id", "unloading_city_id",
        "distance", "total_weight", "total_volume", "body_type",
        "currency_code", "price_original", "exchange_rate", "price_rub",
        "price_type", "is_fact", "complex", "organization_id",
        "subscriber_id", "outlier_mark", "weight_category",
        "volume_category", "source",
    ]
    col_list = ", ".join(columns)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "price_id")
    sql = (
        f"INSERT INTO {schema}.core_fact_prices ({col_list}) VALUES %s "
        f"ON CONFLICT (price_id) DO UPDATE SET {update_set}"
    )
    n = batch_execute_values(conn, sql, _tuples(good_df, columns))
    logger.info("Upserted %d rows into core_fact_prices", n)
    return n


def upsert_quarantine(conn: Connection, schema: str, dq_df: pd.DataFrame) -> int:
    """Insert rejected rows into {schema}.dq_quarantine_prices (idempotent)."""
    sql = (
        f"INSERT INTO {schema}.dq_quarantine_prices (price_id, reason_code, description) "
        f"VALUES %s ON CONFLICT (price_id, reason_code) DO NOTHING"
    )
    rows = [(row.price_id, row.reason_code, None) for row in dq_df.itertuples(index=False)]
    n = batch_execute_values(conn, sql, rows)
    logger.info("Inserted %d rows into dq_quarantine_prices", n)
    return n


def log_batch(conn: Connection, schema: str, start, end, status,
              rows_read, rows_loaded, rows_quarantined):
    sql = (
        f"INSERT INTO {schema}.etl_batch_log "
        f"(batch_start, batch_end, status, rows_read, rows_loaded, rows_quarantined, finished_at) "
        f"VALUES (%s, %s, %s, %s, %s, %s, now())"
    )
    with conn.connection.cursor() as cur:
        cur.execute(sql, (start, end, status, rows_read, rows_loaded, rows_quarantined))
