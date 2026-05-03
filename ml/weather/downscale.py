"""Weather downscaling helpers for the minimal MVP."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _adjust_series(values: Any, adjustment: float = 0.0, scale: float = 1.0) -> Any:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return values
    return [(_as_float(value) * scale) + adjustment for value in values]


def downscale(grid_data: Any, topo_features: Any) -> Any:
    """Downscale grid-level data using topographic features.

    With no topographic context the function preserves the original object.
    When elevation/slope/aspect are provided, it applies deterministic local
    adjustments while keeping the sequence lengths unchanged.
    """
    if not topo_features:
        return grid_data
    if not isinstance(grid_data, Mapping):
        return grid_data

    elevation_m = _as_float(topo_features.get("elevation_m") or topo_features.get("elevation"))
    slope_deg = _as_float(topo_features.get("slope_deg") or topo_features.get("slope"))
    aspect_deg = _as_float(topo_features.get("aspect_deg") or topo_features.get("aspect"))

    temp_offset = -(elevation_m / 150.0)
    humidity_offset = elevation_m / 200.0
    ghi_scale = max(0.0, 1.0 - (elevation_m / 40000.0) - (slope_deg / 1000.0))
    ghi_offset = aspect_deg / 4000.0

    downscaled = dict(grid_data)
    if "temp" in downscaled:
        downscaled["temp"] = _adjust_series(downscaled["temp"], adjustment=temp_offset)
    if "ghi" in downscaled:
        downscaled["ghi"] = [(_as_float(value) * ghi_scale) - ghi_offset for value in downscaled["ghi"]]
    if "humidity" in downscaled:
        downscaled["humidity"] = _adjust_series(downscaled["humidity"], adjustment=humidity_offset)
    return downscaled
