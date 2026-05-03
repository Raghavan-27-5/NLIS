"""PV residual correction for the hybrid DRE model."""

from __future__ import annotations

from typing import Iterable, List, Mapping

import numpy as np


def _as_float_array(values: Iterable[float]) -> np.ndarray:
    return np.asarray(list(values), dtype=float)


def apply_residual_correction(
    physics_pred: Iterable[float],
    features: Mapping[str, Iterable[float]],
) -> List[float]:
    """Apply a deterministic, bounded correction to physics PV output.

    The correction uses weather features to slightly adjust the physics-based
    PV prediction while keeping the result non-negative and within a modest
    uplift/downward adjustment band.
    """
    physics = _as_float_array(physics_pred)
    if physics.ndim != 1:
        raise ValueError("expected a 1D sequence")

    ghi = _as_float_array(features.get("ghi_wm2", []))
    t_amb = _as_float_array(features.get("t_amb_c", []))
    humidity = _as_float_array(features.get("humidity_pct", []))
    rain = _as_float_array(features.get("last_rain_days", []))

    if not (len(physics) == len(ghi) == len(t_amb) == len(humidity) == len(rain)):
        raise ValueError("all sequences must have the same length")

    ghi_signal = np.clip(ghi / 900.0, 0.0, 1.0)
    temp_signal = np.clip((t_amb - 25.0) / 20.0, -1.0, 1.0)
    humidity_signal = np.clip((45.0 - humidity) / 45.0, -1.0, 1.0)
    rain_signal = np.clip(rain / 30.0, 0.0, 1.0)

    score = (
        0.55 * ghi_signal
        + 0.20 * (1.0 - np.abs(temp_signal))
        + 0.15 * humidity_signal
        + 0.10 * rain_signal
    )
    uplift = np.clip(0.92 + 0.12 * score, 0.90, 1.08)

    corrected = np.maximum(0.0, physics * uplift)
    return corrected.tolist()
