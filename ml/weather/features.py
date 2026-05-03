"""Weather feature construction helpers for the minimal MVP."""

from __future__ import annotations

from typing import Dict, List


def _heat_index_c(temp_c: float, humidity_pct: float) -> float:
    temp_f = temp_c * 9.0 / 5.0 + 32.0
    rh = humidity_pct
    hi_f = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh
        - 0.22475541 * temp_f * rh
        - 0.00683783 * temp_f * temp_f
        - 0.05481717 * rh * rh
        + 0.00122874 * temp_f * temp_f * rh
        + 0.00085282 * temp_f * rh * rh
        - 0.00000199 * temp_f * temp_f * rh * rh
    )
    return (hi_f - 32.0) * 5.0 / 9.0


def build_weather_features(weather_data: Dict[str, List[float]]) -> Dict[str, List[float]]:
    """Build weather features from raw weather data."""
    temp = list(weather_data.get("temp", []))
    ghi = list(weather_data.get("ghi", []))
    humidity = list(weather_data.get("humidity", []))

    n = min(len(temp), len(ghi), len(humidity))
    temp = temp[:n]
    ghi = ghi[:n]
    humidity = humidity[:n]

    heat_index = [_heat_index_c(float(t), float(rh)) for t, rh in zip(temp, humidity)]
    cooling_degree_hours = [max(0.0, float(t) - 24.0) for t in temp]
    cloud_factor = [max(0.0, 1.0 - float(g) / 1000.0) for g in ghi]

    return {
        "temp": temp,
        "ghi": ghi,
        "humidity": humidity,
        "heat_index": heat_index,
        "cooling_degree_hours": cooling_degree_hours,
        "cloud_factor": cloud_factor,
    }
