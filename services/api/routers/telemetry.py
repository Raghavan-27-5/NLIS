"""Telemetry API router."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from ml.telemetry.ingest import fetch_telemetry

router = APIRouter()


@router.get("/preview")
def preview() -> dict[str, object]:
    snapshot = fetch_telemetry()
    return asdict(snapshot)
