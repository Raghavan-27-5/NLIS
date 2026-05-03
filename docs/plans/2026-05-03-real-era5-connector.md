# Real ERA5 Weather Connector Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add real weather connector plumbing so the forecast stack can fetch ERA5-style weather from a configurable remote JSON endpoint when local cache data is unavailable.

**Architecture:** Preserve the deterministic offline cache path, but extend the weather ingestion adapter to support a configurable HTTP JSON source with clear validation and error handling. Use a simple standard-library HTTP client so the repo stays dependency-light, and keep the public return shape unchanged (`temp`, `ghi`, `humidity`). Add regression tests for cache, remote, and failure paths, then update docs so operators know how to configure the connector.

**Tech Stack:** Python stdlib (`urllib`, `json`, `os`), pytest, FastAPI, file-backed adapters

---

### Task 1: Add remote ERA5 connector plumbing

**Objective:** Extend `fetch_era5()` so it can fetch from a remote JSON endpoint when no cache is configured, while preserving deterministic cache behavior.

**Files:**
- Modify: `ml/weather/ingest.py`
- Add: `tests/test_weather_ingest.py`

**Step 1: Write failing tests**
- Add a test that starts a tiny local HTTP server returning JSON with `temp`, `ghi`, and `humidity`, sets `HYPERLOCAL_ERA5_URL`, and asserts `fetch_era5()` returns those series.
- Add a test that ensures the remote URL gets used when cache is absent.
- Keep the existing cache/no-cache tests.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_weather_ingest.py -v`
- Expected: FAIL because the current implementation only reads local cache.

**Step 3: Write minimal implementation**
- Add a remote fetch path using `urllib.request`.
- Support either a plain base URL with query parameters or a templated URL.
- Validate the response is JSON with the required keys.
- Raise clear `RuntimeError` messages for network, HTTP, or schema failures.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_weather_ingest.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ml/weather/ingest.py tests/test_weather_ingest.py
git commit -m "feat: add remote ERA5 connector plumbing"
```

### Task 2: Update docs and run full regression verification

**Objective:** Document the new connector configuration and verify that the full hyperlocal stack still passes after the ingest change.

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Test: `tests/test_api.py`, `tests/test_ui_integration.py`, `tests/test_forecast_pipeline.py`

**Step 1: Write failing tests**
- No new code behavior expected here; instead, ensure existing tests still describe the supported pipeline correctly.
- If a doc string or contract assertion is now stale, update the relevant test or docs.

**Step 2: Run test to verify failure**
- Run: `pytest -q`
- Expected: either PASS or a small number of doc/contract-related failures that reveal any stale assumptions.

**Step 3: Write minimal implementation**
- Update README and architecture docs to describe cache-first, remote-fallback ERA5 ingestion.
- Keep the API contract unchanged.

**Step 4: Run test to verify pass**
- Run: `pytest -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add README.md docs/ARCHITECTURE.md tests/test_api.py tests/test_ui_integration.py tests/test_forecast_pipeline.py
git commit -m "docs: document remote ERA5 connector"
```
