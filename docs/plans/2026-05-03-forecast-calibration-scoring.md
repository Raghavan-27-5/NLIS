# Forecast Calibration and Scoring Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add forecast calibration and scoring capabilities so operators can quantify forecast error, interval coverage, and bias using the platform's existing hyperlocal demand forecasts.

**Architecture:** Keep the current forecast-generation path stable and add a lightweight evaluation layer beside it. Build deterministic calibration utilities that can produce a bounded bias adjustment from forecast-vs-observed series, plus scoring utilities that compute standard error metrics and interval coverage. Expose both capabilities through explicit API endpoints so they can be used in operator workflows without changing the existing forecast contract.

**Tech Stack:** Python stdlib, NumPy, FastAPI, pytest, dataclasses

---

### Task 1: Add calibration and scoring core utilities

**Objective:** Create reusable forecast calibration and scoring helpers with deterministic validation and bounded adjustments.

**Files:**
- Create: `ml/forecasting/calibration.py`
- Create: `ml/forecasting/scoring.py`
- Add: `tests/test_forecast_calibration.py`
- Add: `tests/test_forecast_scoring.py`

**Step 1: Write failing tests**
- Add a calibration test that verifies a forecast series is adjusted by a bounded bias derived from observations, preserves length, and rejects mismatched lengths.
- Add a scoring test that verifies bias, MAE, RMSE, MAPE, and interval coverage are computed correctly for a simple deterministic example.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_forecast_calibration.py tests/test_forecast_scoring.py -v`
- Expected: FAIL because the new modules do not exist yet.

**Step 3: Write minimal implementation**
- Implement a calibration helper that clamps the applied bias to a configurable percentage of the forecast mean.
- Implement a scoring helper that returns a compact dictionary of standard evaluation metrics.
- Keep the helpers pure and deterministic.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_forecast_calibration.py tests/test_forecast_scoring.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ml/forecasting/calibration.py ml/forecasting/scoring.py tests/test_forecast_calibration.py tests/test_forecast_scoring.py
git commit -m "feat: add forecast calibration and scoring utilities"
```

### Task 2: Expose calibration and scoring endpoints

**Objective:** Add API endpoints for forecast calibration and scoring without changing the existing forecast response contract.

**Files:**
- Create: `services/api/routers/evaluation.py`
- Modify: `services/api/main.py`
- Add: `tests/test_forecast_evaluation_api.py`
- Update: `tests/test_api.py`

**Step 1: Write failing tests**
- Add an API test for `POST /v1/forecast/calibrate` that returns a calibrated series and bias summary.
- Add an API test for `POST /v1/forecast/score` that returns evaluation metrics and interval coverage.
- Ensure the existing forecast endpoint tests still pass unchanged.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_forecast_evaluation_api.py tests/test_api.py -v`
- Expected: FAIL until the new router and endpoints are implemented.

**Step 3: Write minimal implementation**
- Add a new router for evaluation endpoints.
- Wire the router into the FastAPI app.
- Validate request payloads and return the metrics from the new core utilities.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_forecast_evaluation_api.py tests/test_api.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add services/api/main.py services/api/routers/evaluation.py tests/test_forecast_evaluation_api.py tests/test_api.py
git commit -m "feat: expose forecast calibration and scoring endpoints"
```

### Task 3: Update docs and run full regression verification

**Objective:** Document the calibration/scoring workflow and verify the entire repository remains green.

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/plans/2026-05-03-forecast-calibration-scoring.md` only if the implementation requires a wording correction

**Step 1: Write failing test**
- No new behavior should be introduced here; use the existing test suite to detect stale assumptions if needed.

**Step 2: Run test to verify failure**
- Run: `pytest -q`
- Expected: PASS or a small number of failures that reveal documentation or contract mismatches.

**Step 3: Write minimal implementation**
- Update docs to describe how operators calibrate forecasts and score them against observed demand.
- Keep the existing forecast API unchanged.

**Step 4: Run test to verify pass**
- Run: `pytest -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add README.md docs/ARCHITECTURE.md docs/plans/2026-05-03-forecast-calibration-scoring.md
git commit -m "docs: add forecast calibration and scoring workflow"
```
