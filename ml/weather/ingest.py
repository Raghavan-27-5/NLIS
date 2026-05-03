"""Weather data ingestion helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError
from urllib.request import urlopen


_REQUIRED_KEYS = ("temp", "ghi", "humidity")


def _validate_weather_payload(payload: object, source: str) -> Dict[str, List[float]]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"ERA5 {source} must contain a JSON object")

    data: Dict[str, List[float]] = {}
    for key in _REQUIRED_KEYS:
        values = payload.get(key)
        if values is None:
            raise RuntimeError(f"ERA5 {source} is missing required key: {key}")
        if not isinstance(values, list):
            raise RuntimeError(f"ERA5 {source} key must be a JSON list: {key}")
        try:
            data[key] = [float(value) for value in values]
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"ERA5 {source} key contains non-numeric values: {key}") from exc

    return data


def _load_cache(cache_path: str) -> Dict[str, List[float]]:
    path = Path(cache_path)
    if not path.is_file():
        raise RuntimeError(f"ERA5 cache file does not exist: {path}")

    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid ERA5 cache JSON: {path}") from exc

    return _validate_weather_payload(payload, "cache")


def _load_remote(url: str, lat: float, lon: float, start: str, end: str) -> Dict[str, List[float]]:
    request_url = (
        f"{url}?lat={lat}&lon={lon}&start={start}&end={end}"
        if "?" not in url
        else f"{url}&lat={lat}&lon={lon}&start={start}&end={end}"
    )

    try:
        with urlopen(request_url, timeout=10) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        raise RuntimeError(f"ERA5 remote fetch failed: {url}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid ERA5 remote JSON: {url}") from exc

    return _validate_weather_payload(payload, "remote")


def fetch_era5(lat: float, lon: float, start: str, end: str) -> Dict[str, List[float]]:
    """Fetch ERA5 data using local cache first, then remote fallback."""
    _ = (lat, lon, start, end)

    cache_path = os.getenv("HYPERLOCAL_ERA5_CACHE")
    if cache_path:
        try:
            return _load_cache(cache_path)
        except RuntimeError:
            pass

    remote_url = os.getenv("HYPERLOCAL_ERA5_URL")
    if remote_url:
        return _load_remote(remote_url, lat, lon, start, end)

    if cache_path:
        raise RuntimeError(
            "ERA5 cache data is unavailable and HYPERLOCAL_ERA5_URL is not configured"
        )

    raise RuntimeError("HYPERLOCAL_ERA5_URL must point to a JSON endpoint")
