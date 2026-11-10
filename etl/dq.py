# -*- coding: utf-8 -*-
"""Data-quality rules and category enrichment (Question 1).

Значения (коды причин, коды валют, границы категорий) вынесены в `constants.py`.
"""
import numpy as np
import pandas as pd

from constants import (
    VOLUME_CATEGORY_DEFAULT,
    VOLUME_CATEGORY_FTL,
    VOLUME_FTL_MAX,
    VOLUME_MIN_EXCLUSIVE,
    WEIGHT_CATEGORY_BOUNDS,
    WEIGHT_CATEGORY_DEFAULT,
    WEIGHT_ROUND_DECIMALS,
)

# Re-export for backwards compatibility with callers/tests.
from constants import (  # noqa: F401
    FOREIGN_CURRENCIES,
    REASON_PRIORITY,
)


def weight_category(total_weight: pd.Series) -> pd.Series:
    """Map weight (tonnes, rounded to 0.1) to a business category.

    Bounds come from WEIGHT_CATEGORY_BOUNDS (checked top-down):
    G20T >= 30; FTL [10,30); 10T [5,10); 5T [2.5,5); L5T [0.5,2.5); else OTH.
    """
    rounded = np.round(total_weight, WEIGHT_ROUND_DECIMALS)
    thresholds = [bound for bound, _ in WEIGHT_CATEGORY_BOUNDS]
    labels = [label for _, label in WEIGHT_CATEGORY_BOUNDS]
    conditions = [rounded >= bound for bound in thresholds]
    return pd.Series(
        np.select(conditions, labels, default=WEIGHT_CATEGORY_DEFAULT),
        index=total_weight.index,
    )


def volume_category(total_volume: pd.Series) -> pd.Series:
    """FTL when 0 < V <= VOLUME_FTL_MAX, otherwise OTH (incl. V = 0)."""
    in_range = (total_volume > VOLUME_MIN_EXCLUSIVE) & (total_volume <= VOLUME_FTL_MAX)
    return pd.Series(
        np.where(in_range, VOLUME_CATEGORY_FTL, VOLUME_CATEGORY_DEFAULT),
        index=total_volume.index,
    )
