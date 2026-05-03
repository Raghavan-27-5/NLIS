"""Minimal hyperlocal forecast API router."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from ml.data.loaders import ForecastBundle, load_forecast_bundle_json, load_weather_csv
from ml.dre.pv_physics import FeederSpec
from ml.forecasting.pipeline import forecast_from_bundle, forecast_substation
from ml.telemetry.models import TelemetrySnapshot
from ml.weather.features import build_weather_features

router = APIRouter()

PVType = Literal["rooftop", "kusum_c", "kusum_a"]


class FeederPayload(BaseModel):
    feeder_id: str
    pv_type: PVType
    rated_mw: float = Field(gt=0)
    tilt_deg: float
    azimuth_deg: float
    lat: float
    lon: float


class WeatherPoint(BaseModel):
    t_amb_c: float
    ghi_wm2: float
    humidity_pct: float
    last_rain_days: float = Field(ge=0)


class TelemetryPayload(BaseModel):
    substation_id: str
    feeder_id: str
    timestamp: str
    load_mw: float
    voltage_kv: float
    frequency_hz: float
    power_factor: float
    transformer_loading_pct: float | None = None
    feeder_loading_pct: float | None = None


class TopographyPayload(BaseModel):
    elevation_m: float | None = None
    slope_deg: float | None = None
    aspect_deg: float | None = None


class ForecastRequest(BaseModel):
    substation_id: str
    feeder: FeederPayload | None = None
    feeders: List[FeederPayload] | None = None
    weather: List[WeatherPoint]
    base_load_mw: float = Field(gt=0)
    ac_penetration: float = Field(ge=0, le=1)
    n_connections: int = Field(gt=0)
    horizon: str | None = None
    telemetry: TelemetryPayload | None = None
    topo_features: TopographyPayload | None = None

    @model_validator(mode="after")
    def validate_feeders(self) -> "ForecastRequest":
        if self.feeder is None and not self.feeders:
            raise ValueError("feeder or feeders must be provided")
        return self


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/forecast")
def forecast(request: ForecastRequest) -> dict[str, Any]:
    if not request.weather:
        raise HTTPException(status_code=400, detail="weather must not be empty")

    feeder_payloads = request.feeders or ([request.feeder] if request.feeder is not None else [])
    feeders = [FeederSpec(**payload.model_dump()) for payload in feeder_payloads]

    telemetry = TelemetrySnapshot.from_dict(request.telemetry.model_dump(), source="request") if request.telemetry else None
    if telemetry is not None:
        feeder_ids = {item.feeder_id for item in feeders}
        if telemetry.substation_id != request.substation_id:
            raise HTTPException(status_code=400, detail="telemetry substation_id must match request substation_id")
        if telemetry.feeder_id not in feeder_ids:
            raise HTTPException(status_code=400, detail="telemetry feeder_id must match one of the requested feeders")

    result = forecast_substation(
        feeders=feeders,
        t_amb_c=[point.t_amb_c for point in request.weather],
        ghi_wm2=[point.ghi_wm2 for point in request.weather],
        humidity_pct=[point.humidity_pct for point in request.weather],
        last_rain_days=[point.last_rain_days for point in request.weather],
        base_load_mw=request.base_load_mw,
        ac_penetration=request.ac_penetration,
        n_connections=request.n_connections,
        telemetry=telemetry,
        topo_features=request.topo_features.model_dump(exclude_none=True) if request.topo_features else None,
    )
    return {
        "substation_id": request.substation_id,
        "feeder_id": feeders[0].feeder_id,
        "horizon": request.horizon,
        **result,
    }


@router.get("/bundle/raw")
def bundle_raw(path: str = Query(..., description="Path to a JSON forecast bundle")) -> dict[str, Any]:
    bundle: ForecastBundle = load_forecast_bundle_json(_resolve_demo_path(path))
    return {"path": path, **asdict(bundle)}


@router.get("/bundle/preview")
def bundle_preview(path: str = Query(..., description="Path to a JSON forecast bundle")) -> dict[str, Any]:
    bundle = load_forecast_bundle_json(_resolve_demo_path(path))
    result = forecast_from_bundle(bundle)
    return {"substation_id": bundle.substation_id, "feeder_id": bundle.feeder.feeder_id, **result}


@router.get("/weather/preview")
def weather_preview(path: str = Query(..., description="Path to a weather CSV file")) -> dict[str, Any]:
    weather = load_weather_csv(_resolve_demo_path(path))
    features = build_weather_features(
        {"temp": weather["temp"], "ghi": weather["ghi"], "humidity": weather["humidity"]}
    )
    return {
        "rows": len(weather["temp"]),
        "columns": sorted(weather.keys()),
        "weather": weather,
        "features": features,
    }


def _resolve_demo_path(path: str) -> Path:
    base_dir = Path(__file__).resolve().parents[3] / "sample_data"
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate

    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="path must stay within sample_data") from exc
    return resolved
