"""Deterministic forecast scoring helpers."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def _as_1d_float_array(values: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.ndim != 1:
        raise ValueError("expected a 1D sequence")
    return arr


def score_forecast(
    forecast: Sequence[float],
    observed: Sequence[float],
    *,
    lower: Sequence[float] | None = None,
    upper: Sequence[float] | None = None,
) -> dict[str, object]:
    """Return core deterministic forecast error metrics."""

    forecast_arr = _as_1d_float_array(forecast)
    observed_arr = _as_1d_float_array(observed)

    if len(forecast_arr) != len(observed_arr):
        raise ValueError("forecast and observed series must have the same length")
    if len(forecast_arr) == 0:
        raise ValueError("forecast and observed series must not be empty")

    errors = forecast_arr - observed_arr
    abs_errors = np.abs(errors)

    result: dict[str, object] = {
        "n_points": int(len(forecast_arr)),
        "bias": float(np.mean(errors)),
        "mae": float(np.mean(abs_errors)),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
    }

    denom = np.abs(observed_arr)
    nonzero = denom != 0
    if np.any(nonzero):
        result["mape"] = float(np.mean(np.abs(errors[nonzero] / observed_arr[nonzero])) * 100.0)
    else:
        result["mape"] = float("nan")

    if lower is not None or upper is not None:
        if lower is None or upper is None:
            raise ValueError("lower and upper must both be provided")
        lower_arr = _as_1d_float_array(lower)
        upper_arr = _as_1d_float_array(upper)
        if not (len(lower_arr) == len(upper_arr) == len(forecast_arr)):
            raise ValueError("forecast, observed, lower, and upper must have the same length")
        interval_mask = (observed_arr >= lower_arr) & (observed_arr <= upper_arr)
        result["interval_coverage"] = float(np.mean(interval_mask))
        result["interval_width"] = float(np.mean(upper_arr - lower_arr))

    return result
