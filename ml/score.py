# -*- coding: utf-8 -*-
"""Batch inference & persistence of predictions (Question 3)."""
import logging

import pandas as pd
from psycopg2.extras import execute_values

logger = logging.getLogger("ml.score")

PREDICTION_COLUMNS = [
    "price_id", "loading_date", "loading_city_gcid", "unloading_city_gcid",
    "body_group", "actual_price_rub", "predicted_price_rub",
    "abs_error_rub", "ape_pct", "model_name",
]


def _to_date(x):
    if x is None:
        return None
    if isinstance(x, pd.Timestamp):
        return x.date()
    return x


def save_predictions(engine, schema, test_df, test_pred, future_df, future_pred,
                     model_name="CatBoostRegressor") -> int:
    rows = []
    for i, r in enumerate(test_df.itertuples(index=False)):
        actual = float(r.price_rub)
        pred = float(test_pred[i])
        rows.append((
            int(r.price_id), _to_date(r.loading_date),
            int(r.loading_city_gcid), int(r.unloading_city_gcid),
            str(r.body_group), actual, pred,
            float(abs(actual - pred)), float(abs(actual - pred) / actual * 100.0),
            model_name,
        ))
    for i, r in enumerate(future_df.itertuples(index=False)):
        pred = float(future_pred[i])
        # For future planned deals actual / error / ape are NULL.
        rows.append((
            int(r.price_id), _to_date(r.loading_date),
            int(r.loading_city_gcid), int(r.unloading_city_gcid),
            str(r.body_group), None, pred, None, None,
            model_name,
        ))

    col_list = ", ".join(PREDICTION_COLUMNS)
    upd = ", ".join(f"{c} = EXCLUDED.{c}" for c in PREDICTION_COLUMNS if c != "price_id")
    sql = (
        f"INSERT INTO {schema}.ml_price_predictions ({col_list}) VALUES %s "
        f"ON CONFLICT (price_id) DO UPDATE SET {upd}, scored_at = now()"
    )

    with engine.begin() as conn:
        raw = conn.connection
        with raw.cursor() as cur:
            execute_values(cur, sql, rows, page_size=10000)

    logger.info("Saved %d predictions into ml_price_predictions", len(rows))
    return len(rows)
