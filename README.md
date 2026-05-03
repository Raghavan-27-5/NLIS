# Hyperlocal Forecast MVP

## Quick start

### 1) Run the API locally

```bash
python3 -m uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Open the dashboard

- Dashboard: `http://127.0.0.1:8000/`
- Static files: `http://127.0.0.1:8000/ui/`

### 3) Preview a real-data style weather CSV

```bash
curl "http://127.0.0.1:8000/v1/weather/preview?path=weather_sample.csv"
```

### 4) Forecast from a JSON bundle

```bash
curl "http://127.0.0.1:8000/v1/bundle/preview?path=forecast_bundle.json"
```

### 5) Send a forecast request directly

```bash
curl -X POST "http://127.0.0.1:8000/v1/forecast" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "substation_id": "Jaipur South 220kV",
  "feeders": [
    {
      "feeder_id": "RJ-RT-001",
      "pv_type": "rooftop",
      "rated_mw": 0.8,
      "tilt_deg": 20.0,
      "azimuth_deg": 180.0,
      "lat": 26.9,
      "lon": 75.8
    },
    {
      "feeder_id": "RJ-KUSUM-001",
      "pv_type": "kusum_c",
      "rated_mw": 2.0,
      "tilt_deg": 18.0,
      "azimuth_deg": 180.0,
      "lat": 26.9,
      "lon": 75.8
    }
  ],
  "weather": [
    {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
    {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0}
  ],
  "base_load_mw": 435.0,
  "ac_penetration": 0.58,
  "n_connections": 20000,
  "topo_features": {
    "elevation_m": 1200.0,
    "slope_deg": 10.0,
    "aspect_deg": 180.0
  }
}
JSON
```

## What this MVP shows
- Weather CSV ingestion with previewable derived features
- Structured forecast bundle ingestion for file-backed demos and tests
- Cache-first ERA5 ingestion with remote fallback via `HYPERLOCAL_ERA5_CACHE` and `HYPERLOCAL_ERA5_URL`
- Cache-first live telemetry ingestion with remote fallback via `HYPERLOCAL_TELEMETRY_CACHE` and `HYPERLOCAL_TELEMETRY_URL`
- Operator preview endpoints for weather, bundle, and telemetry snapshots
- Deterministic microclimate downscaling that influences both PV and demand when local topographic context is provided
- Physics-based PV DRE generation with bounded hybrid residual correction and per-feeder aggregation
- Substation forecast response with gross demand, DRE, net demand, and uncertainty bands
- Cooling-load estimation driven by weather, AC penetration, and connection counts
- Optional telemetry biasing in the forecast pipeline, bounded so it only gently nudges the load baseline and validated against the requested asset IDs
- Dashboard integration with the same API contract used by the tests

## Pipeline summary
1. Weather is loaded from a local CSV, bundle-backed payload, or ERA5 cache/remote source.
2. Telemetry can be previewed from cache or remote JSON and, when supplied on a forecast request, is converted into a bounded load bias.
3. Optional downscaling adjusts temperature, GHI, and humidity when topo context is available.
4. Weather features are built from the effective local weather, including heat index and cooling signals.
5. Cooling demand is estimated from weather, AC penetration, and connection counts.
6. PV output is computed per feeder with a physics model and a bounded residual layer.
7. Net demand is computed as gross demand minus aggregated corrected DRE generation.

## Operational notes
- ERA5 ingestion is cache-first and falls back to the configured remote JSON endpoint.
- Telemetry ingestion is cache-first and falls back to the configured remote JSON endpoint.
- The public API preview endpoints remain deterministic for demos and tests, with weather/bundle previews restricted to `sample_data` and telemetry preview served via cache-first ingestion.
- Forecast requests can include an optional telemetry snapshot; the resulting baseline adjustment is intentionally bounded.
- No topology store yet
- No persistent database yet
- No model training loop yet
