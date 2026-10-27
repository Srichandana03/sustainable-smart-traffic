"""Train the XGBoost congestion classifier.

Usage:
    python -m ml.congestion_model.train --data data/raw/TrafficTwoMonth.csv
    python -m ml.congestion_model.train --synthetic          # no dataset yet

Dataset: https://www.kaggle.com/datasets/hasibullahaman/traffic-prediction-dataset
Saves:   models/congestion_xgb.json  +  models/congestion_meta.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from .baseline import fit_count_thresholds, predict_by_count
from .features import FEATURE_COLUMNS, LABELS, load_kaggle_csv, make_synthetic

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"


def _score(y_true, y_pred) -> dict:
    """Accuracy, macro precision/recall/F1 and confusion matrix for one set of predictions."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro")),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=range(len(LABELS))).tolist(),
    }


def train(X, y, out_dir: Path = MODEL_DIR, seed: int = 42) -> dict:
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)

    # --- BEFORE: simple vehicle-count rule (no learning) + majority-class reference ---
    thr = fit_count_thresholds(Xtr)
    baseline_metrics = _score(yte, predict_by_count(Xte, thr))
    baseline_metrics["method"] = "vehicle-count thresholds (terciles of total)"
    baseline_metrics["thresholds_on_total"] = [round(thr[0], 1), round(thr[1], 1)]
    majority = DummyClassifier(strategy="most_frequent").fit(Xtr, ytr)
    majority_accuracy = float(accuracy_score(yte, majority.predict(Xte)))

    # --- AFTER: XGBoost trained on all 12 features ---
    clf = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9,
        colsample_bytree=0.9, objective="multi:softprob", num_class=len(LABELS),
        eval_metric="mlogloss", random_state=seed, n_jobs=4,
    )
    clf.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
    pred = clf.predict(Xte)
    metrics = {
        **_score(yte, pred),
        "n_train": int(len(ytr)), "n_test": int(len(yte)),
        "per_class": classification_report(yte, pred, target_names=LABELS,
                                           output_dict=True, zero_division=0),
        "feature_importance": dict(zip(FEATURE_COLUMNS, map(float, clf.feature_importances_))),
    }

    # Side-by-side "before vs after" summary the API/dashboard reads directly.
    comparison = {
        "before": {"name": "Rule-based (vehicle count)", "accuracy": baseline_metrics["accuracy"],
                   "precision_macro": baseline_metrics["precision_macro"],
                   "recall_macro": baseline_metrics["recall_macro"], "f1_macro": baseline_metrics["f1_macro"]},
        "after": {"name": "XGBoost (12 features)", "accuracy": metrics["accuracy"],
                  "precision_macro": metrics["precision_macro"],
                  "recall_macro": metrics["recall_macro"], "f1_macro": metrics["f1_macro"]},
        "majority_class_accuracy": majority_accuracy,
        "accuracy_gain": round(metrics["accuracy"] - baseline_metrics["accuracy"], 4),
        "f1_macro_gain": round(metrics["f1_macro"] - baseline_metrics["f1_macro"], 4),
    }

    print(classification_report(yte, pred, target_names=LABELS))
    print(f"[after ] xgboost acc={metrics['accuracy']:.3f} precision={metrics['precision_macro']:.3f} "
          f"recall={metrics['recall_macro']:.3f} f1={metrics['f1_macro']:.3f}")
    print(f"gain: +{comparison['accuracy_gain']:.3f} accuracy, +{comparison['f1_macro_gain']:.3f} macro-F1")

    out_dir.mkdir(parents=True, exist_ok=True)
    clf.save_model(out_dir / "congestion_xgb.json")
    (out_dir / "congestion_meta.json").write_text(json.dumps({
        "labels": LABELS, "features": FEATURE_COLUMNS,
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "majority_class_accuracy": majority_accuracy,
        "comparison": comparison,
    }, indent=2))
    print(f"saved -> {out_dir / 'congestion_xgb.json'}  acc={metrics['accuracy']:.3f} f1={metrics['f1_macro']:.3f}")
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="Path to Kaggle Traffic.csv / TrafficTwoMonth.csv")
    ap.add_argument("--synthetic", action="store_true", help="Use synthetic data (dev only)")
    ap.add_argument("--out", default=str(MODEL_DIR))
    args = ap.parse_args()
    if args.data:
        X, y = load_kaggle_csv(args.data)
        print(f"loaded {len(X)} rows from {args.data}; label dist={np.bincount(y).tolist()}")
    elif args.synthetic:
        X, y = make_synthetic()
        print("WARNING: training on synthetic data — download the Kaggle dataset for real results")
    else:
        ap.error("pass --data <csv> or --synthetic")
    train(X, y, Path(args.out))


if __name__ == "__main__":
    main()
