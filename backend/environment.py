
from typing import Dict

SUPPORTED_PRODUCE = {
    "apple": {
        "demo_base_days": 7.0,
        "demo_temperature_c": 4.0,
        "demo_humidity_percent": 90.0
    },
    "banana": {
        "demo_base_days": 5.0,
        "demo_temperature_c": 18.0,
        "demo_humidity_percent": 85.0
    },
    "orange": {
        "demo_base_days": 10.0,
        "demo_temperature_c": 5.0,
        "demo_humidity_percent": 90.0
    }
}

def estimate_storage_demo(
    produce_type: str,
    freshness_score: float,
    temperature: float,
    humidity: float,
    storage_days: float
) -> Dict:
    """
    Demonstration-only shelf-life calculation.

    The constants and adjustment factors are illustrative,
    not fitted to measured shelf-life observations.
    Do not interpret the result as validated food safety advice.
    """

    produce_type = produce_type.lower().strip()

    if produce_type not in SUPPORTED_PRODUCE:
        raise ValueError("Unsupported produce type")

    if not 0 <= freshness_score <= 1:
        raise ValueError("Invalid freshness score")

    if not 0 <= humidity <= 100:
        raise ValueError("Invalid humidity")

    if storage_days < 0:
        raise ValueError("Invalid storage duration")

    profile = SUPPORTED_PRODUCE[produce_type]

    temperature_difference = abs(
        temperature - profile["demo_temperature_c"]
    )

    humidity_difference = abs(
        humidity - profile["demo_humidity_percent"]
    )

    temperature_factor = max(
        0.2, 1 - 0.025 * temperature_difference
    )

    humidity_factor = max(
        0.5, 1 - 0.005 * humidity_difference
    )

    illustrative_days = (
        profile["demo_base_days"]
        * freshness_score
        * temperature_factor
        * humidity_factor
        - storage_days
    )

    illustrative_days = round(
        max(0.0, illustrative_days), 1
    )

    return {
        "illustrative_remaining_days": illustrative_days,
        "storage_reference": {
            "temperature_c": profile["demo_temperature_c"],
            "humidity_percent": profile["demo_humidity_percent"]
        },
        "estimation_method": "illustrative_heuristic",
        "validated": False,
        "disclaimer": (
            "Demonstration estimate only. Not validated "
            "against measured remaining shelf-life data. "
            "Do not use for food safety decisions."
        )
    }

def get_storage_recommendations(
    produce_type: str,
    temperature: float,
    humidity: float,
    freshness_status: str
) -> list[str]:
    """Return general storage guidance for supported produce."""

    recommendations = []

    if freshness_status == "rotten":
        recommendations.append(
            "Visible spoilage is suspected. Do not rely on "
            "the shelf-life estimate to assess food safety."
        )

    if produce_type == "apple":
        recommendations.append(
            "Store apples in a refrigerator when possible."
        )
        if temperature > 10:
            recommendations.append(
                "Cooler storage generally slows apple deterioration."
            )

    elif produce_type == "banana":
        recommendations.append(
            "Store unripe bananas at room temperature, "
            "away from direct sunlight."
        )
        if temperature < 12:
            recommendations.append(
                "Low temperatures can cause chilling injury "
                "in bananas."
            )

    elif produce_type == "orange":
        recommendations.append(
            "Store oranges in a cool, ventilated environment."
        )
        if temperature > 15:
            recommendations.append(
                "Refrigeration may help extend orange storage life."
            )

    if humidity < 40:
        recommendations.append(
            "Low humidity may increase moisture loss "
            "in fresh produce."
        )

    recommendations.append(
        "Inspect produce regularly for mold, "
        "unusual odors, and visible deterioration."
    )

    return recommendations
