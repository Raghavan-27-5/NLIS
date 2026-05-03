"""Telemetry ingestion package."""

from ml.telemetry.ingest import fetch_telemetry
from ml.telemetry.models import TelemetrySnapshot

__all__ = ["TelemetrySnapshot", "fetch_telemetry"]
