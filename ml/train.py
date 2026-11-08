# -*- coding: utf-8 -*-
"""Model training and evaluation (Question 3)."""
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, TARGET

SEED = 42


def compute_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }


def _ordinal_encode(train_df, eval_df, cat_cols):
    """Fit a categorical->int mapping on train only (no leakage)."""
    enc_t, enc_e = train_df.copy(), eval_df.copy()
    for col in cat_cols:
        cats = {v: i for i, v in enumerate(pd.unique(train_df[col]))}
        enc_t[col] = enc_t[col].map(cats).fillna(-1).astype(int)
        enc_e[col] = enc_e[col].map(cats).fillna(-1).astype(int)
    return enc_t, enc_e


def train_catboost(train_df) -> CatBoostRegressor:
    model = CatBoostRegressor(
        iterations=1500,
        learning_rate=0.08,
        depth=8,
        l2_leaf_reg=3.0,
        loss_function="RMSE",
        random_seed=SEED,
        verbose=False,
    )
    model.fit(
        train_df[FEATURE_COLUMNS],
        train_df[TARGET],
        cat_features=CATEGORICAL_FEATURES,
    )
    return model


def run_experiment(train_df, test_df) -> dict:
    """Train CatBoost + baselines, return (model, predictions, metrics)."""
    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET]

    # Primary model: CatBoost.
    cat = train_catboost(train_df)
    y_cat = cat.predict(X_test)

    # Baselines for comparison (sklearn, ordinal-encoded categoricals).
    tr_ord, te_ord = _ordinal_encode(train_df, test_df, CATEGORICAL_FEATURES)
    X_tr_ord = tr_ord[FEATURE_COLUMNS]
    X_te_ord = te_ord[FEATURE_COLUMNS]

    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=SEED))
    ridge.fit(X_tr_ord, y_train)
    y_ridge = ridge.predict(X_te_ord)

    # DecisionTree baseline (comparable to the reference report).
    dt = DecisionTreeRegressor(max_depth=10, min_samples_leaf=10, random_state=SEED)
    dt.fit(X_tr_ord, y_train)
    y_dt = dt.predict(X_te_ord)

    metrics = {
        "CatBoost": compute_metrics(y_test, y_cat),
        "Ridge": compute_metrics(y_test, y_ridge),
        "DecisionTree": compute_metrics(y_test, y_dt),
    }

    return {"model": cat, "y_pred": y_cat, "metrics": metrics}
