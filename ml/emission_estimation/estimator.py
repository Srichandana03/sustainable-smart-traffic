"""CO2 estimation from vehicle counts + congestion level.

Emission = Σ_class (vehicles_class × distance_km × EF_class × congestion_multiplier)

Emission factors are tailpipe CO2 per vehicle-km for the Indian fleet mix, order-of-magnitude
values commonly cited in ARAI / CPCB / TERI inventories. Tune per deployment city.
"""
from __future__ import annotations

EMISSION_FACTORS_G_PER_KM: dict[str, float] = {
    "car": 150.0,        # petrol/diesel passenger car average
    "motorcycle": 40.0,  # two-wheeler
    "bus": 800.0,        # diesel city bus
    "truck": 600.0,      # LCV/HCV average
}

# Stop-and-go traffic burns more fuel per km than free flow
CONGESTION_MULTIPLIER = {"Low": 1.0, "Moderate": 1.3, "High": 1.8}

DWELL_SECONDS = 20.0  # assumed time a vehicle spends inside the camera view


def estimate_emissions(stats: dict, congestion_level: str, road_segment_km: float = 0.5,
                       window_minutes: int = 15) -> dict:
    """Return CO2 (kg) for the analysed window plus a per-hour projection."""
    cbc = stats.get("counts_by_class", {})
    scale = (window_minutes * 60) / DWELL_SECONDS  # frame presence -> vehicles passing per window
    mult = CONGESTION_MULTIPLIER.get(congestion_level, 1.0)
    per_class_kg: dict[str, float] = {}
    vehicles_window: dict[str, float] = {}
    for cls, ef in EMISSION_FACTORS_G_PER_KM.items():
        n = float(cbc.get(cls, 0.0)) * scale
        vehicles_window[cls] = round(n, 1)
        per_class_kg[cls] = n * road_segment_km * ef * mult / 1000.0
    total_kg = sum(per_class_kg.values())
    return {
        "window_minutes": window_minutes,
        "road_segment_km": road_segment_km,
        "congestion_multiplier": mult,
        "vehicles_in_window": vehicles_window,
        "co2_kg_by_class": {k: round(v, 3) for k, v in per_class_kg.items()},
        "co2_kg": round(total_kg, 3),
        "co2_kg_per_hour": round(total_kg * 60 / window_minutes, 3),
        "co2_kg_per_hour_free_flow": round(total_kg * 60 / window_minutes / mult, 3),
        "excess_due_to_congestion_kg_per_hour": round(total_kg * 60 / window_minutes * (1 - 1 / mult), 3),
    }
