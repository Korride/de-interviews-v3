# -*- coding: utf-8 -*-
"""Entry point for the ML pipeline (Question 3): features -> train -> score."""
import argparse
import logging

from sqlalchemy import create_engine

from etl.config import config
from ml.features import (
    AS_OF,
    FEATURE_COLUMNS,
    TEST_END,
    TEST_START,
    TRAIN_START,
    build_features,
)
from ml.score import save_predictions
from ml.train import run_experiment

MODEL_NAME = "CatBoostRegressor"


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    engine = create_engine(config.sqlalchemy_url)
    S = config.schema_quoted

    df = build_features(engine, S)
    logging.info("Features built for %d core facts", len(df))

    # Strict time-based split population (factual completed direct deals, clean).
    base = df[
        df["is_fact"]
        & ~df["complex"]
        & (df["price_rub"] > 0)
        & (df["distance"] > 0)
        & ~df["outlier_mark"]
    ]
    train = base[(base["loading_date"] >= TRAIN_START) & (base["loading_date"] < TEST_START)]
    test = base[(base["loading_date"] >= TEST_START) & (base["loading_date"] <= TEST_END)]
    logging.info("train=%d  test=%d  (split [%s, %s) / [%s, %s])",
                 len(train), len(test), TRAIN_START.date(), TEST_START.date(),
                 TEST_START.date(), TEST_END.date())

    result = run_experiment(train, test)
    metrics = result["metrics"]

    print("=" * 66)
    print(" ML metrics on the held-out test period (loading_date)")
    print(f"   train = [{TRAIN_START.date()}, {TEST_START.date()})  ({len(train)} rows)")
    print(f"   test  = [{TEST_START.date()}, {TEST_END.date()}]  ({len(test)} rows)")
    print("-" * 66)
    print(f" {'model':<14} {'R2':>8} {'MAPE,%':>8} {'RMSE,RUB':>10} {'MAE,RUB':>10}")
    print("-" * 66)
    for name, m in metrics.items():
        print(f" {name:<14} {m['r2']:>8.4f} {m['mape']:>8.2f} "
              f"{m['rmse']:>10.2f} {m['mae']:>10.2f}")
    print("=" * 66)

    # Batch inference: held-out test period + future planned deals.
    future = df[
        (df["loading_date"] > AS_OF)
        & df["is_fact"]
        & ~df["complex"]
        & (df["distance"] > 0)
        & (df["total_weight"] >= 0)
        & (df["total_volume"] >= 0)
    ]
    logging.info("Future planned deals to score: %d", len(future))

    future_pred = result["model"].predict(future[FEATURE_COLUMNS])
    n = save_predictions(engine, S, test, result["y_pred"], future, future_pred, MODEL_NAME)
    print(f" Saved {n} predictions -> ml_price_predictions "
          f"({len(test)} test + {len(future)} future)")
    engine.dispose()


if __name__ == "__main__":
    main()
