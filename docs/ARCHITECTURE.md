# Architecture

## Overview
This repository hosts a FastAPI service and a deterministic, file-backed hyperlocal forecasting stack.

## Hardened MVP
- `ml/weather`: validated weather ingestion, cache-first ERA5 fetch with remote fallback, feature building, and deterministic downscaling hooks.
- `ml/telemetry`: validated telemetry snapshots plus cache-first ingestion with remote fallback.
- `ml/dre`: PV physics plus bounded hybrid residual correction.
- `ml/demand`: cooling-load estimation driven by weather, AC penetration, and connection counts.
- `ml/data`: file-based adapters for weather CSVs and structured forecast bundles.
- `ml/forecasting`: end-to-end gross → DRE → net-demand forecast composition with local weather downscaling, multi-feeder DRE aggregation, and optional bounded telemetry bias.
- `services/api`: FastAPI service exposing health, bundle, weather, telemetry preview, and forecast endpoints.

## API
- `GET /v1/health`: Basic health check.
- `POST /v1/forecast`: Backward-compatible forecast response with gross demand, DRE, net demand, intervals, per-feeder DRE breakdown, effective downscaled weather, and summary diagnostics. Accepts either `feeder` or `feeders`, optional topography, and an optional telemetry snapshot payload after identity checks.
- `GET /v1/bundle/preview?path=...`: Forecast from a JSON bundle inside `sample_data`.
- `GET /v1/bundle/raw?path=...`: Return the structured bundle payload from `sample_data`.
- `GET /v1/weather/preview?path=...`: Validate and preview a weather CSV from `sample_data` with derived features.
- `GET /v1/telemetry/preview`: Preview the validated telemetry snapshot from cache-first ingestion with remote fallback.
