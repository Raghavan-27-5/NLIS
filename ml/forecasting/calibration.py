"""Deterministic forecast calibration helpers."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def _as_1d_float_array(values: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.ndim != 1:
        raise ValueError("expected a 1D sequence")
    return arr


def calibrate_forecast(
    forecast: Sequence[float],
    observed: Sequence[float],
    *,
    max_bias_fraction: float = 0.05,
) -> dict[str, object]:
    """Apply a bounded additive bias from observed minus forecast residuals.

    The applied bias is the mean residual clipped to a conservative fraction
    of the forecast mean magnitude so the adjustment stays small and stable.
    """

    forecast_arr = _as_1d_float_array(forecast)
    observed_arr = _as_1d_float_array(observed)

    if len(forecast_arr) != len(observed_arr):
        raise ValueError("forecast and observed series must have the same length")
    if len(forecast_arr) == 0:
        raise ValueError("forecast and observed series must not be empty")
    if max_bias_fraction < 0:
        raise ValueError("max_bias_fraction must be non-negative")

    residuals = observed_arr - forecast_arr
    raw_bias = float(np.mean(residuals))
    bias_limit = float(abs(np.mean(forecast_arr)) * max_bias_fraction)
    bias = float(np.clip(raw_bias, -bias_limit, bias_limit))
    calibrated = forecast_arr + bias

    return {
        "raw_bias": raw_bias,
        "bias_limit": bias_limit,
        "bias": bias,
        "calibrated_forecast": calibrated.tolist(),
        "n_points": int(len(forecast_arr)),
    }
