# Live Telemetry Ingestion Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a production-grade live telemetry ingestion path for DISCOM-style SCADA/AMI data so the platform can preview and optionally calibrate forecasts using current substation and feeder measurements.

**Architecture:** Keep the existing weather and forecast pipeline intact, but add a parallel telemetry ingestion layer that can read deterministic local cache files or fetch a live JSON snapshot from a configured endpoint. Model telemetry as a validated snapshot with explicit measurements such as substation load, feeder load, voltage, frequency, and power factor. Expose a `/v1/telemetry/preview` endpoint for operators and optionally accept telemetry on the forecast request to gently bias the forecast baseline without breaking the current API contract.

**Tech Stack:** Python stdlib, FastAPI, pytest, file-backed adapters, urllib/json, existing NumPy forecast stack

---

### Task 1: Create the telemetry model and ingestion adapter

**Objective:** Add a validated telemetry snapshot model plus cache-first and remote-fallback ingestion functions.

**Files:**
- Create: `ml/telemetry/__init__.py`
- Create: `ml/telemetry/ingest.py`
- Create: `ml/telemetry/models.py`
- Add: `tests/test_telemetry_ingest.py`

**Step 1: Write failing test**
- Add tests that verify:
  - `fetch_telemetry()` reads a local cache file when `HYPERLOCAL_TELEMETRY_CACHE` is set.
  - `fetch_telemetry()` falls back to `HYPERLOCAL_TELEMETRY_URL` when no cache is present.
  - Returned snapshots validate required keys and preserve the expected field types.
  - Missing configuration or invalid payloads raise clear `RuntimeError`s.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_telemetry_ingest.py -v`
- Expected: FAIL because the telemetry module does not exist yet.

**Step 3: Write minimal implementation**
- Implement a compact telemetry snapshot model.
- Support cache-first JSON ingestion and remote JSON fallback with stdlib HTTP.
- Validate schema and provide clear error messages.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_telemetry_ingest.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ml/telemetry tests/test_telemetry_ingest.py
git commit -m "feat: add live telemetry ingestion adapter"
```

### Task 2: Expose telemetry preview and wire optional calibration into forecasting

**Objective:** Add an operator-facing preview endpoint and use telemetry gently to calibrate the forecast baseline when present on the forecast request.

**Files:**
- Create: `services/api/routers/telemetry.py`
- Modify: `services/api/main.py`
- Modify: `services/api/routers/forecast.py`
- Modify: `ml/forecasting/pipeline.py`
- Add: `tests/test_telemetry_api.py`
- Update: `tests/test_api.py`
- Update: `tests/test_forecast_pipeline.py`

**Step 1: Write failing test**
- Add API tests that assert `GET /v1/telemetry/preview` returns the validated snapshot shape from a configured source.
- Add forecast tests that prove telemetry can optionally nudge the load baseline without changing array lengths or breaking the existing forecast contract.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_telemetry_api.py tests/test_api.py tests/test_forecast_pipeline.py -v`
- Expected: FAIL until the new router and calibration behavior are implemented.

**Step 3: Write minimal implementation**
- Mount the telemetry router in the FastAPI app.
- Add an optional telemetry payload to the forecast request.
- Compute a bounded calibration term from the provided telemetry snapshot and pass it into the forecast pipeline.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_telemetry_api.py tests/test_api.py tests/test_forecast_pipeline.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add services/api/main.py services/api/routers/telemetry.py services/api/routers/forecast.py ml/forecasting/pipeline.py tests/test_telemetry_api.py tests/test_api.py tests/test_forecast_pipeline.py
git commit -m "feat: wire telemetry preview into forecast stack"
```

### Task 3: Update documentation and run full regression verification

**Objective:** Document the telemetry path clearly and verify the entire stack remains green.

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/plans/2026-05-03-live-telemetry-ingestion.md` if the implementation changes the plan assumptions

**Step 1: Write failing test**
- No new behavior is expected here; use the current API and integration tests to detect stale assumptions if any doc-aligned contract changed.

**Step 2: Run test to verify failure**
- Run: `pytest -q`
- Expected: PASS or a small number of failures that reveal stale documentation or contract assumptions.

**Step 3: Write minimal implementation**
- Update docs to describe telemetry cache/remote ingestion and optional forecast calibration.
- Keep the contract stable for existing consumers.

**Step 4: Run test to verify pass**
- Run: `pytest -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add README.md docs/ARCHITECTURE.md docs/plans/2026-05-03-live-telemetry-ingestion.md
git commit -m "docs: add live telemetry ingestion coverage"
```
