"""Forecasting pipeline for the minimal hyperlocal MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from ml.telemetry.models import TelemetrySnapshot

import numpy as np

from ml.data.loaders import ForecastBundle
from ml.demand.cooling_load import cooling_load_mw
from ml.dre.pv_physics import FeederSpec, dre_generation
from ml.dre.pv_residual import apply_residual_correction
from ml.weather.features import build_weather_features
from ml.weather.downscale import downscale


@dataclass(frozen=True)
class ForecastSummary:
    avg_net_demand_mw: float
    peak_net_demand_mw: float
    min_net_demand_mw: float


def _as_1d_float_array(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.ndim != 1:
        raise ValueError("expected a 1D sequence")
    return arr


def forecast_substation(
    *,
    feeder: FeederSpec | None = None,
    feeders: Sequence[FeederSpec] | None = None,
    t_amb_c: Sequence[float],
    ghi_wm2: Sequence[float],
    humidity_pct: Sequence[float],
    last_rain_days: Sequence[float],
    base_load_mw: float,
    ac_penetration: float,
    n_connections: int,
    weather_bias_mw: float = 0.0,
    telemetry: TelemetrySnapshot | None = None,
    topo_features: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Return a minimal end-to-end net-demand forecast for one feeder/substation."""
    feeder_specs = _normalize_feeders(feeder=feeder, feeders=feeders)
    t_amb = _as_1d_float_array(t_amb_c)
    ghi = _as_1d_float_array(ghi_wm2)
    rh = _as_1d_float_array(humidity_pct)
    rain = _as_1d_float_array(last_rain_days)

    if not (len(t_amb) == len(ghi) == len(rh) == len(rain)):
        raise ValueError("all weather sequences must have the same length")

    raw_weather = {
        "temp": t_amb.tolist(),
        "ghi": ghi.tolist(),
        "humidity": rh.tolist(),
        "last_rain_days": rain.tolist(),
    }
    downscaled_weather = downscale(raw_weather, topo_features or {})
    downscaled_temp = _as_1d_float_array(downscaled_weather["temp"])
    downscaled_ghi = _as_1d_float_array(downscaled_weather["ghi"])
    downscaled_rh = _as_1d_float_array(downscaled_weather["humidity"])
    weather_features = build_weather_features(
        {
            "temp": downscaled_temp.tolist(),
            "ghi": downscaled_ghi.tolist(),
            "humidity": downscaled_rh.tolist(),
        }
    )

    dre_generation_mw = np.zeros_like(t_amb, dtype=float)
    feeder_breakdown: list[dict[str, object]] = []
    for spec in feeder_specs:
        pv = dre_generation(spec, downscaled_ghi, downscaled_temp, rain)
        physics_pv_mw = np.asarray(pv["output_mw"], dtype=float)
        corrected = np.asarray(
            apply_residual_correction(
                physics_pv_mw,
                {
                    "ghi_wm2": downscaled_ghi.tolist(),
                    "t_amb_c": downscaled_temp.tolist(),
                    "humidity_pct": downscaled_rh.tolist(),
                    "last_rain_days": rain.tolist(),
                },
            ),
            dtype=float,
        )
        dre_generation_mw = dre_generation_mw + corrected
        feeder_breakdown.append(
            {
                "feeder_id": spec.feeder_id,
                "pv_type": spec.pv_type,
                "rated_mw": spec.rated_mw,
                "dre_generation_mw": corrected.tolist(),
            }
        )

    ac_load_mw = cooling_load_mw(
        downscaled_temp,
        downscaled_rh,
        np.asarray([ac_penetration], dtype=float),
        np.asarray([n_connections], dtype=float),
    )[:, 0]

    telemetry_bias_mw = 0.0
    if telemetry is not None:
        telemetry_delta_mw = float(telemetry.load_mw) - float(base_load_mw)
        telemetry_bias_mw = float(np.clip(0.10 * telemetry_delta_mw, -0.05 * base_load_mw, 0.05 * base_load_mw))

    gross_demand_mw = np.asarray(base_load_mw, dtype=float) + ac_load_mw + weather_bias_mw + telemetry_bias_mw
    net_demand_mw = gross_demand_mw - dre_generation_mw

    q_hat = max(2.0, 0.06 * float(np.std(net_demand_mw)) + 0.02 * base_load_mw)
    lower_90_mw = net_demand_mw - q_hat
    upper_90_mw = net_demand_mw + q_hat

    summary = ForecastSummary(
        avg_net_demand_mw=float(np.mean(net_demand_mw)),
        peak_net_demand_mw=float(np.max(net_demand_mw)),
        min_net_demand_mw=float(np.min(net_demand_mw)),
    )

    return {
        "feeder_id": feeder_specs[0].feeder_id,
        "feeders": feeder_breakdown,
        "gross_demand_mw": gross_demand_mw.tolist(),
        "dre_generation_mw": dre_generation_mw.tolist(),
        "net_demand_mw": net_demand_mw.tolist(),
        "lower_90_mw": lower_90_mw.tolist(),
        "upper_90_mw": upper_90_mw.tolist(),
        "weather_features": weather_features,
        "downscaled_weather": {
            "temp": downscaled_temp.tolist(),
            "ghi": downscaled_ghi.tolist(),
            "humidity": downscaled_rh.tolist(),
            "last_rain_days": rain.tolist(),
        },
        "summary": summary.__dict__,
    }


def forecast_from_bundle(bundle: ForecastBundle) -> dict[str, object]:
    """Forecast directly from a structured bundle loaded from real data files."""
    result = forecast_substation(
        feeders=bundle.feeders,
        t_amb_c=[p.t_amb_c for p in bundle.weather],
        ghi_wm2=[p.ghi_wm2 for p in bundle.weather],
        humidity_pct=[p.humidity_pct for p in bundle.weather],
        last_rain_days=[p.last_rain_days for p in bundle.weather],
        base_load_mw=bundle.base_load_mw,
        ac_penetration=bundle.ac_penetration,
        n_connections=bundle.n_connections,
        topo_features=bundle.topo_features,
    )
    return {"substation_id": bundle.substation_id, **result}


def _normalize_feeders(
    *,
    feeder: FeederSpec | None,
    feeders: Sequence[FeederSpec] | None,
) -> list[FeederSpec]:
    if feeders:
        return list(feeders)
    if feeder is not None:
        return [feeder]
    raise ValueError("forecast requires feeder or feeders")
