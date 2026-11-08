# -*- coding: utf-8 -*-
"""Data-quality rules and category enrichment (Question 1).

Reason codes are listed in priority order: for a row violating several rules,
the FIRST matching reason is kept. Priority goes from the most fundamental
(price <= 0) to the most specific (missing currency rate).
"""
import numpy as np
import pandas as pd

#: Priority order of DQ quarantine reasons (first match wins).
REASON_PRIORITY = [
    "INVALID_PRICE",          # price <= 0
    "RUB_PRICE_TOO_LOW",      # currency 643 and price <= 1000 (source validation)
    "INVALID_DISTANCE",       # distance <= 0
    "INVALID_WEIGHT_VOLUME",  # total_weight < 0 or total_volume < 0
    "UNKNOWN_CITY",           # city absent from the cities reference
    "MISSING_RATE",           # foreign currency without an exact CBR rate
]

#: Foreign currency codes (must be converted to RUB via `nearest_rate_date`).
FOREIGN_CURRENCIES = {"840", "978"}


def weight_category(total_weight: pd.Series) -> pd.Series:
    """G20T >=30; FTL [10,30); 10T [5,10); 5T [2.5,5); L5T [0.5,2.5); else OTH."""
    rw = np.round(total_weight, 1)
    conditions = [rw >= 30, rw >= 10, rw >= 5, rw >= 2.5, rw >= 0.5]
    choices = ["G20T", "FTL", "10T", "5T", "L5T"]
    return pd.Series(np.select(conditions, choices, default="OTH"), index=total_weight.index)


def volume_category(total_volume: pd.Series) -> pd.Series:
    """FTL when 0 < V <= 120 m3, otherwise OTH (incl. V = 0)."""
    return pd.Series(
        np.where((total_volume > 0) & (total_volume <= 120), "FTL", "OTH"),
        index=total_volume.index,
    )
