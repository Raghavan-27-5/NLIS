"""Live telemetry ingestion helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from ml.telemetry.models import TelemetrySnapshot


def _read_json_file(path: Path, source: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"telemetry {source} file is unavailable: {path}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid telemetry {source} JSON: {path}") from exc


def _fetch_remote(url: str) -> object:
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        raise RuntimeError(f"telemetry remote fetch failed: {url}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid telemetry remote JSON: {url}") from exc


def fetch_telemetry() -> TelemetrySnapshot:
    """Fetch a telemetry snapshot from cache first, then remote fallback."""

    cache_path = os.getenv("HYPERLOCAL_TELEMETRY_CACHE")
    if cache_path:
        payload = _read_json_file(Path(cache_path), "cache")
        return TelemetrySnapshot.from_dict(payload, source="cache")

    remote_url = os.getenv("HYPERLOCAL_TELEMETRY_URL")
    if remote_url:
        payload = _fetch_remote(remote_url)
        return TelemetrySnapshot.from_dict(payload, source="remote")

    raise RuntimeError(
        "HYPERLOCAL_TELEMETRY_CACHE or HYPERLOCAL_TELEMETRY_URL must be configured"
    )
