"""A simple, no-learning baseline classifier for the "before XGBoost" comparison.

It decides Low / Moderate / High purely from the TOTAL number of vehicles, using two
cut-off values taken from the training data (the 33rd and 66th percentiles of total
count). This is the kind of hand-written rule a planner might use in a spreadsheet
before any machine learning — so comparing it against the trained XGBoost model gives
an honest "before vs after" picture. XGBoost, by contrast, learns from all 12 features
(per-class counts, ratios, hour of day, weekend, peak-hour), not just the raw total.
"""
from __future__ import annotations

import numpy as np


def fit_count_thresholds(X_train) -> tuple[float, float]:
    """Pick two thresholds on the 'total' column from the training data's terciles."""
    totals = np.asarray(X_train["total"], dtype=float)
    t1, t2 = np.quantile(totals, [1 / 3, 2 / 3])
    return float(t1), float(t2)


def predict_by_count(X, thresholds: tuple[float, float]) -> np.ndarray:
    """Return class ids (0=Low, 1=Moderate, 2=High) using the count thresholds."""
    t1, t2 = thresholds
    total = np.asarray(X["total"], dtype=float)
    return np.where(total <= t1, 0, np.where(total <= t2, 1, 2)).astype(int)
