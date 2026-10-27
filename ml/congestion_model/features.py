"""Feature engineering shared by training and inference.

Training data: Kaggle "Traffic Prediction Dataset" (TrafficTwoMonth.csv / Traffic.csv)
    columns: Time, Date, Day of the week, CarCount, BikeCount, BusCount, TruckCount,
             Total, Traffic Situation  (low | normal | heavy | high)

We map the four dataset labels onto EcoPath's three classes:
    low -> Low, normal -> Moderate, heavy/high -> High
"""
from __future__ import annotations

import datetime as dt
import numpy as np
import pandas as pd

LABELS = ["Low", "Moderate", "High"]
LABEL_TO_ID = {l: i for i, l in enumerate(LABELS)}
DATASET_LABEL_MAP = {"low": "Low", "normal": "Moderate", "heavy": "High", "high": "High"}

FEATURE_COLUMNS = [
    "car_count", "bike_count", "bus_count", "truck_count", "total",
    "heavy_ratio", "two_wheeler_ratio",
    "hour", "hour_sin", "hour_cos", "is_weekend", "is_peak",
]

PEAK_HOURS = set(range(8, 11)) | set(range(17, 21))


def _time_feats(hour: np.ndarray, weekday: np.ndarray) -> pd.DataFrame:
    hour = np.asarray(hour, dtype=float)
    weekday = np.asarray(weekday, dtype=int)
    return pd.DataFrame({
        "hour": hour,
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "is_weekend": (weekday >= 5).astype(int),
        "is_peak": np.isin(hour.astype(int), list(PEAK_HOURS)).astype(int),
    })


def build_features(car, bike, bus, truck, hour, weekday) -> pd.DataFrame:
    car, bike, bus, truck = (np.asarray(x, dtype=float) for x in (car, bike, bus, truck))
    total = car + bike + bus + truck
    safe = np.where(total == 0, 1.0, total)
    df = pd.DataFrame({
        "car_count": car, "bike_count": bike, "bus_count": bus, "truck_count": truck,
        "total": total,
        "heavy_ratio": (bus + truck) / safe,
        "two_wheeler_ratio": bike / safe,
    })
    return pd.concat([df, _time_feats(hour, weekday)], axis=1)[FEATURE_COLUMNS]


def load_kaggle_csv(path: str) -> tuple[pd.DataFrame, np.ndarray]:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    t = pd.to_datetime(raw["Time"], format="%I:%M:%S %p", errors="coerce")
    hour = t.dt.hour.fillna(0).to_numpy()
    day_map = {d: i for i, d in enumerate(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])}
    weekday = raw["Day of the week"].map(day_map).fillna(0).to_numpy()
    X = build_features(raw["CarCount"], raw["BikeCount"], raw["BusCount"], raw["TruckCount"], hour, weekday)
    y = raw["Traffic Situation"].str.strip().str.lower().map(DATASET_LABEL_MAP).map(LABEL_TO_ID).to_numpy()
    return X, y


def make_synthetic(n: int = 6000, seed: int = 7) -> tuple[pd.DataFrame, np.ndarray]:
    """Synthetic data mirroring the Kaggle schema/statistics. For dev/CI only."""
    rng = np.random.default_rng(seed)
    hour = rng.integers(0, 24, n)
    weekday = rng.integers(0, 7, n)
    base = 20 + 60 * np.isin(hour, list(PEAK_HOURS)) + 25 * ((hour >= 11) & (hour <= 16))
    base = base * np.where(weekday >= 5, 0.6, 1.0)
    car = rng.poisson(base)
    bike = rng.poisson(base * 0.25)
    bus = rng.poisson(base * 0.1)
    truck = rng.poisson(base * 0.12)
    total = car + bike + bus + truck
    noise = rng.normal(0, 12, n)
    score = total + noise
    y = np.where(score < 45, 0, np.where(score < 110, 1, 2))
    return build_features(car, bike, bus, truck, hour, weekday), y


def video_stats_to_features(stats: dict, when: dt.datetime | None = None,
                            window_minutes: int = 15) -> pd.DataFrame:
    """Convert detector output (per-frame averages) to the dataset's per-15-min counts.

    The Kaggle dataset counts vehicles passing a point in 15 minutes. A single frame shows
    vehicles *present*, so we scale by an assumed turnover: vehicles/frame * (window / dwell).
    dwell ~ 20 s is a reasonable default for an urban camera view.
    """
    when = when or dt.datetime.now()
    cbc = stats.get("counts_by_class", {})
    dwell_s = 20.0
    scale = (window_minutes * 60) / dwell_s
    car = cbc.get("car", 0.0) * scale
    bike = cbc.get("motorcycle", 0.0) * scale
    bus = cbc.get("bus", 0.0) * scale
    truck = cbc.get("truck", 0.0) * scale
    return build_features([car], [bike], [bus], [truck], [when.hour], [when.weekday()])
