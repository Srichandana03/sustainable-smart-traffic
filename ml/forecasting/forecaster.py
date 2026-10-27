"""Congestion forecasting (Phase 4).

v1 = STUB: seasonal-naive baseline over the location's history (hour-of-day averages).
TODO Phase 4: replace with an LSTM (PyTorch) trained on per-location 15-min sequences.
Keep the function signature so the API/UI need no change when the LSTM lands.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

LEVEL_TO_SCORE = {"Low": 0.0, "Moderate": 0.5, "High": 1.0}


def _score_to_level(s: float) -> str:
    return "Low" if s < 0.3 else "Moderate" if s < 0.7 else "High"


def forecast_congestion(history: list[dict], horizon_hours: int = 6,
                        now: dt.datetime | None = None) -> list[dict]:
    """history: [{created_at: datetime, congestion_level: str}, ...] for one location."""
    now = now or dt.datetime.now()
    by_hour: dict[int, list[float]] = defaultdict(list)
    for h in history:
        by_hour[h["created_at"].hour].append(LEVEL_TO_SCORE.get(h["congestion_level"], 0.5))
    overall = sum(sum(v) for v in by_hour.values()) / max(1, sum(len(v) for v in by_hour.values()))

    out = []
    for k in range(1, horizon_hours + 1):
        t = now + dt.timedelta(hours=k)
        vals = by_hour.get(t.hour)
        score = sum(vals) / len(vals) if vals else overall
        out.append({"time": t.isoformat(timespec="minutes"), "score": round(score, 3),
                    "level": _score_to_level(score), "method": "seasonal_naive_stub"})
    return out
