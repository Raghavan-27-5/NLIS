"""Validated telemetry snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


_REQUIRED_FIELDS = (
    "substation_id",
    "feeder_id",
    "timestamp",
    "load_mw",
    "voltage_kv",
    "frequency_hz",
    "power_factor",
)


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    substation_id: str
    feeder_id: str
    timestamp: datetime
    load_mw: float
    voltage_kv: float
    frequency_hz: float
    power_factor: float
    transformer_loading_pct: float | None = None
    feeder_loading_pct: float | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], source: str = "payload") -> "TelemetrySnapshot":
        if not isinstance(payload, Mapping):
            raise RuntimeError(f"telemetry {source} must be a JSON object")

        missing = [field for field in _REQUIRED_FIELDS if field not in payload]
        if missing:
            missing_fields = ", ".join(missing)
            raise RuntimeError(f"telemetry {source} is missing required field(s): {missing_fields}")

        substation_id = payload["substation_id"]
        feeder_id = payload["feeder_id"]
        timestamp = payload["timestamp"]
        load_mw = payload["load_mw"]
        voltage_kv = payload["voltage_kv"]
        frequency_hz = payload["frequency_hz"]
        power_factor = payload["power_factor"]

        if not isinstance(substation_id, str) or not substation_id.strip():
            raise RuntimeError(f"telemetry {source} field must be a non-empty string: substation_id")
        if not isinstance(feeder_id, str) or not feeder_id.strip():
            raise RuntimeError(f"telemetry {source} field must be a non-empty string: feeder_id")

        parsed_timestamp = _parse_timestamp(timestamp, source)

        transformer_loading_pct = _optional_float(payload.get("transformer_loading_pct"), "transformer_loading_pct", source)
        feeder_loading_pct = _optional_float(payload.get("feeder_loading_pct"), "feeder_loading_pct", source)

        return cls(
            substation_id=substation_id,
            feeder_id=feeder_id,
            timestamp=parsed_timestamp,
            load_mw=_required_float(load_mw, "load_mw", source),
            voltage_kv=_required_float(voltage_kv, "voltage_kv", source),
            frequency_hz=_required_float(frequency_hz, "frequency_hz", source),
            power_factor=_required_float(power_factor, "power_factor", source),
            transformer_loading_pct=transformer_loading_pct,
            feeder_loading_pct=feeder_loading_pct,
        )


def _required_float(value: Any, field: str, source: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"telemetry {source} field must be numeric: {field}") from exc
    if not _is_finite(number):
        raise RuntimeError(f"telemetry {source} field must be finite: {field}")
    return number


def _optional_float(value: Any, field: str, source: str) -> float | None:
    if value is None:
        return None
    return _required_float(value, field, source)


def _parse_timestamp(value: Any, source: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"telemetry {source} field must be an ISO 8601 string: timestamp")

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RuntimeError(f"telemetry {source} field must be ISO 8601: timestamp") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_finite(number: float) -> bool:
    return number == number and number not in (float("inf"), float("-inf"))
