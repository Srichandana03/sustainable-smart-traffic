from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
from xgboost import XGBClassifier

from .features import FEATURE_COLUMNS, LABELS, video_stats_to_features

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "models" / "congestion_xgb.json"


class CongestionModel:
    """Loads the trained XGBoost model; falls back to a density-threshold rule if missing."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL):
        self.model_path = Path(model_path)
        self.clf: XGBClassifier | None = None
        self.meta: dict = {}
        if self.model_path.exists():
            self.clf = XGBClassifier()
            self.clf.load_model(self.model_path)
            meta_p = self.model_path.with_name("congestion_meta.json")
            if meta_p.exists():
                self.meta = json.loads(meta_p.read_text())

    @property
    def is_trained(self) -> bool:
        return self.clf is not None

    def predict_from_stats(self, stats: dict, when: dt.datetime | None = None) -> dict:
        X = video_stats_to_features(stats, when)
        if self.clf is not None:
            proba = self.clf.predict_proba(X[FEATURE_COLUMNS])[0]
            idx = int(np.argmax(proba))
            return {
                "level": LABELS[idx],
                "confidence": float(proba[idx]),
                "probabilities": {l: float(p) for l, p in zip(LABELS, proba)},
                "features": {k: float(v) for k, v in X.iloc[0].items()},
                "model": "xgboost",
            }
        # rule-based fallback
        avg = float(stats.get("avg_vehicles_per_frame", 0.0))
        level = "Low" if avg < 5 else "Moderate" if avg < 12 else "High"
        return {"level": level, "confidence": 0.5, "probabilities": {l: (1.0 if l == level else 0.0) for l in LABELS},
                "features": {k: float(v) for k, v in X.iloc[0].items()}, "model": "rule"}
