# Hyperlocal Forecast Platform Hardening Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the remaining stubbed forecast components with production-grade, test-covered weather ingestion, microclimate downscaling, and hybrid physical/ML residual correction so the platform can support hyperlocal DRE and net-demand forecasting more realistically.

**Architecture:** Keep the existing FastAPI contract and dashboard stable, but harden the modeling stack underneath it. Add a validated weather ingestion adapter with explicit cache/remote modes, introduce a deterministic microclimate downscaler that can adjust temperature/GHI/humidity by topographic context, and apply a bounded residual correction layer to physics-based PV output before net demand is computed. Preserve current endpoints and result keys, but add internal diagnostics and regression tests for every new behavior.

**Tech Stack:** Python, FastAPI, NumPy, pytest, file-backed adapters, deterministic model corrections

---

### Task 1: Replace the weather ingestion and downscaling stubs

**Objective:** Turn weather ingestion into a real validated adapter and make microclimate downscaling apply measurable adjustments when topographic context is provided.

**Files:**
- Modify: `ml/weather/ingest.py`
- Modify: `ml/weather/downscale.py`
- Add: `tests/test_weather_ingest.py`
- Add: `tests/test_weather_downscale.py`

**Step 1: Write failing tests**
- Add a weather-ingest test that loads cached ERA5-style JSON/CSV payloads from a temp file and asserts the returned series contain `temp`, `ghi`, and `humidity`.
- Add a downscaling test that passes non-empty topographic context and asserts the output changes in the expected direction while preserving array lengths.

**Step 2: Run tests to verify failure**
- Run: `pytest tests/test_weather_ingest.py tests/test_weather_downscale.py -v`
- Expected: FAIL because the current stub implementations do not support cache-backed ingestion or real downscaling.

**Step 3: Write minimal implementation**
- Implement `fetch_era5()` so it can read a local cache payload or a configured base URL, with explicit validation and clear errors when unavailable.
- Implement `downscale()` so it preserves identity behavior by default but adjusts temperature, GHI, and humidity when topo features are supplied.

**Step 4: Run tests to verify pass**
- Run: `pytest tests/test_weather_ingest.py tests/test_weather_downscale.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ml/weather/ingest.py ml/weather/downscale.py tests/test_weather_ingest.py tests/test_weather_downscale.py
git commit -m "feat: harden weather ingestion and downscaling"
```

### Task 2: Add hybrid residual correction to the PV forecasting pipeline

**Objective:** Apply a bounded residual correction to physics-based DRE generation and integrate a more explicit cooling-load model into the forecast pipeline.

**Files:**
- Modify: `ml/dre/pv_residual.py`
- Modify: `ml/forecasting/pipeline.py`
- Add: `tests/test_dre_residual.py`
- Update: `tests/test_forecast_pipeline.py`

**Step 1: Write failing tests**
- Add a residual-correction test that proves corrected PV output stays non-negative, follows feature sensitivity, and does not exceed a reasonable bounded uplift over physics output.
- Extend the forecast pipeline test so it checks for aligned arrays, gross-minus-DRE net demand identity, and sensitivity to weather/AC stressors.

**Step 2: Run tests to verify failure**
- Run: `pytest tests/test_dre_residual.py tests/test_forecast_pipeline.py -v`
- Expected: FAIL because the residual layer is currently a stub and the pipeline does not yet use it.

**Step 3: Write minimal implementation**
- Implement a deterministic residual-correction function using the supplied feature map, with clamping and strong validation.
- Integrate the correction into `forecast_substation()` after the physics PV model and before net demand is computed.
- Use the cooling-load model to make AC-driven demand more explicit and inspectable.

**Step 4: Run tests to verify pass**
- Run: `pytest tests/test_dre_residual.py tests/test_forecast_pipeline.py tests/test_api.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ml/dre/pv_residual.py ml/forecasting/pipeline.py tests/test_dre_residual.py tests/test_forecast_pipeline.py tests/test_api.py
git commit -m "feat: add hybrid residual correction to forecast pipeline"
```

### Task 3: Tighten end-to-end API and documentation coverage

**Objective:** Ensure the API, docs, and integration tests reflect the hardened platform behavior and remain stable for UI consumers.

**Files:**
- Modify: `tests/test_api.py`
- Modify: `tests/test_ui_integration.py`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`

**Step 1: Write failing tests**
- Add API assertions for any new diagnostic fields exposed by the pipeline, without breaking the existing contract.
- Add UI assertions that the dashboard still serves the updated forecast payload and reference strings remain intact.

**Step 2: Run tests to verify failure**
- Run: `pytest tests/test_api.py tests/test_ui_integration.py -v`
- Expected: FAIL until the API and UI documentation/tests are aligned.

**Step 3: Write minimal implementation**
- Update docs to describe the new ingestion, downscaling, and hybrid correction behavior.
- Keep the API backward-compatible while exposing useful diagnostics.

**Step 4: Run tests to verify pass**
- Run: `pytest -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add tests/test_api.py tests/test_ui_integration.py README.md docs/ARCHITECTURE.md
git commit -m "docs: align hyperlocal forecast platform coverage"
```
