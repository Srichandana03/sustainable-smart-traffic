"""Sustainability verdict: compare estimated CO2 against a regulatory carbon limit.

This is deliberately NOT a machine-learning step. The hard part (counting vehicles
and estimating CO2) is already done by the detector + XGBoost + emission model.
Here we simply check the resulting CO2-per-hour against the carbon cap a city /
government sets, and turn it into an easy-to-read "eco-friendly" signal.

Bands (relative to the limit):
    CO2 <= 80% of limit   -> Eco-Friendly   (green)
    80% < CO2 <= 100%     -> Near Limit      (amber)
    CO2 > 100% of limit   -> Over Limit      (red)
"""
from __future__ import annotations

DEFAULT_CARBON_LIMIT_KG_PER_HOUR = 2500.0

# Fraction of the limit below which we call the site comfortably eco-friendly.
_GREEN_FRACTION = 0.8


def assess_sustainability(co2_kg_per_hour: float,
                          limit_kg_per_hour: float = DEFAULT_CARBON_LIMIT_KG_PER_HOUR) -> dict:
    """Return an eco-friendliness verdict for one site's CO2 reading.

    Args:
        co2_kg_per_hour:   estimated tailpipe CO2 for the analysed location (kg/h).
        limit_kg_per_hour: the carbon cap to compare against (kg/h), default 2500.

    Returns a dict the API/UI can render directly.
    """
    co2 = max(0.0, float(co2_kg_per_hour))
    limit = float(limit_kg_per_hour)

    ratio = (co2 / limit) if limit > 0 else 0.0
    percent_of_limit = round(ratio * 100, 1)
    margin = round(limit - co2, 1)  # positive = headroom left, negative = overshoot

    if co2 <= _GREEN_FRACTION * limit:
        status, rating, color = "Eco-Friendly", "good", "green"
    elif co2 <= limit:
        status, rating, color = "Near Limit", "warning", "amber"
    else:
        status, rating, color = "Over Limit", "exceeded", "red"

    within_limit = co2 <= limit
    if within_limit:
        message = (f"Within the carbon limit — using {percent_of_limit}% of the "
                   f"{limit:g} kg/h cap, {margin:g} kg/h to spare.")
    else:
        message = (f"Over the carbon limit by {abs(margin):g} kg/h — "
                   f"{percent_of_limit}% of the {limit:g} kg/h cap.")

    return {
        "co2_kg_per_hour": round(co2, 3),
        "carbon_limit_kg_per_hour": limit,
        "within_limit": within_limit,
        "status": status,            # Eco-Friendly | Near Limit | Over Limit
        "rating": rating,            # good | warning | exceeded
        "color": color,              # green | amber | red
        "percent_of_limit": percent_of_limit,
        "margin_kg_per_hour": margin,
        "message": message,
    }
