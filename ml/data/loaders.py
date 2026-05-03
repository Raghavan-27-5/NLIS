"""File-based data loaders for the hyperlocal forecast MVP."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml.dre.pv_physics import FeederSpec


@dataclass(frozen=True)
class WeatherPointBundle:
    t_amb_c: float
    ghi_wm2: float
    humidity_pct: float
    last_rain_days: float


@dataclass(frozen=True)
class ForecastBundle:
    substation_id: str
    feeders: list[FeederSpec]
    weather: list[WeatherPointBundle]
    base_load_mw: float
    ac_penetration: float
    n_connections: int
    topo_features: dict[str, float] | None = None

    @property
    def feeder(self) -> FeederSpec:
        """Backward-compatible access to the primary feeder."""
        return self.feeders[0]


def load_weather_csv(path: str | Path) -> dict[str, list[float]]:
    """Load weather time-series from a CSV with real-world style columns."""
    path = Path(path)
    temp: list[float] = []
    ghi: list[float] = []
    humidity: list[float] = []
    last_rain_days: list[float] = []

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"temp_c", "ghi_wm2", "humidity_pct", "last_rain_days"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for row in reader:
            temp.append(float(row["temp_c"]))
            ghi.append(float(row["ghi_wm2"]))
            humidity.append(float(row["humidity_pct"]))
            last_rain_days.append(float(row["last_rain_days"]))

    return {"temp": temp, "ghi": ghi, "humidity": humidity, "last_rain_days": last_rain_days}


def load_forecast_bundle_json(path: str | Path) -> ForecastBundle:
    """Load a minimal forecast bundle from JSON."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    feeders_payload = payload.get("feeders")
    if feeders_payload is None:
        feeder_payload = payload.get("feeder")
        if feeder_payload is None:
            raise ValueError("bundle must include feeder or feeders")
        feeders_payload = [feeder_payload]

    feeders = [FeederSpec(**item) for item in feeders_payload]
    weather = [WeatherPointBundle(**item) for item in payload["weather"]]
    topo_features = _coerce_topo_features(payload.get("topo_features"))

    return ForecastBundle(
        substation_id=str(payload["substation_id"]),
        feeders=feeders,
        weather=weather,
        base_load_mw=float(payload["base_load_mw"]),
        ac_penetration=float(payload["ac_penetration"]),
        n_connections=int(payload["n_connections"]),
        topo_features=topo_features,
    )


def _coerce_topo_features(payload: object) -> dict[str, float] | None:
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise ValueError("topo_features must be a JSON object")
    return {str(key): float(value) for key, value in payload.items()}
