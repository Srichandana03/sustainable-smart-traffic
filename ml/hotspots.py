"""Hotspot identification: rank locations by congestion frequency and emissions.

Input: a list of analysis records (dicts) with keys
    location, latitude, longitude, congestion_level, co2_kg_per_hour, created_at
Output: ranked list of locations with a 0-100 hotspot score.
"""
from __future__ import annotations

from collections import defaultdict

LEVEL_WEIGHT = {"Low": 0.0, "Moderate": 0.5, "High": 1.0}


def rank_hotspots(records: list[dict], top_n: int = 10) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups[r["location"]].append(r)
    if not groups:
        return []

    rows = []
    for loc, rs in groups.items():
        n = len(rs)
        high = sum(1 for r in rs if r["congestion_level"] == "High")
        sev = sum(LEVEL_WEIGHT.get(r["congestion_level"], 0) for r in rs) / n
        co2 = sum(float(r.get("co2_kg_per_hour") or 0) for r in rs) / n
        lat = next((r.get("latitude") for r in rs if r.get("latitude") is not None), None)
        lon = next((r.get("longitude") for r in rs if r.get("longitude") is not None), None)
        rows.append({"location": loc, "latitude": lat, "longitude": lon, "samples": n,
                     "high_frequency": high / n, "severity": sev, "avg_co2_kg_per_hour": co2})

    max_co2 = max(r["avg_co2_kg_per_hour"] for r in rows) or 1.0
    for r in rows:
        # 60% how often/how badly congested, 40% emissions intensity
        r["score"] = round(100 * (0.6 * r["severity"] + 0.4 * r["avg_co2_kg_per_hour"] / max_co2), 1)
        r["high_frequency"] = round(r["high_frequency"], 3)
        r["severity"] = round(r["severity"], 3)
        r["avg_co2_kg_per_hour"] = round(r["avg_co2_kg_per_hour"], 2)
    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows[:top_n]
