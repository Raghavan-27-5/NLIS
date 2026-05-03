# Forecast Confidence and Alert Bands Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Surface forecast confidence bands and operator alert bands in the served dashboard so users can see uncertainty, breaches, and band health at a glance.

**Architecture:** Keep the existing API contract unchanged and layer new operator-oriented UI affordances on top of the current forecast payload. Use the existing `lower_90_mw` / `upper_90_mw` arrays to render a shaded confidence interval, derive alert counts from row-level band breaches, and summarize the result in a compact top-bar indicator and a dedicated dashboard card.

**Tech Stack:** FastAPI, Chart.js, vanilla JavaScript, pytest

---

### Task 1: Add UI affordances for confidence/alert bands

**Objective:** Add a visible confidence-band summary card and a top-bar alert indicator without changing the backend contract.

**Files:**
- Modify: `ui/index.html`
- Modify: `ui/app.js`

**Step 1: Write failing test**
- Add assertions to `tests/test_ui_integration.py` that the served HTML and JS reference the confidence-band panel and alert-band summary elements.
- Add assertions to `tests/test_forecast_pipeline.py` or `tests/test_api.py` that the forecast interval arrays remain aligned and bracket `net_demand_mw`.

**Step 2: Run test to verify failure**
- Run: `python -m pytest tests/test_ui_integration.py::test_ui_index_served -v`
- Expected: FAIL because the new confidence-band elements do not exist yet.

**Step 3: Write minimal implementation**
- Add a `Confidence & alert bands` card in the dashboard section.
- Add a top-bar chip for `Band alerts`.
- Render metrics from `lower_90_mw`, `upper_90_mw`, and row-level breach counts.

**Step 4: Run test to verify pass**
- Run: `python -m pytest tests/test_ui_integration.py tests/test_forecast_pipeline.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ui/index.html ui/app.js tests/test_ui_integration.py tests/test_forecast_pipeline.py docs/plans/2026-05-03-confidence-alert-bands.md
git commit -m "feat: add confidence and alert band UI"
```

### Task 2: Render the confidence interval as a shaded band

**Objective:** Make the forecast uncertainty visually obvious in the main dashboard chart.

**Files:**
- Modify: `ui/app.js`

**Step 1: Write failing test**
- Add a UI integration assertion that `ui/app.js` includes the confidence-band fill configuration and the band summary data fields.

**Step 2: Run test to verify failure**
- Run: `python -m pytest tests/test_ui_integration.py::test_ui_app_js_uses_api_routes_and_live_edit_controls -v`
- Expected: FAIL until the chart configuration references the shaded band.

**Step 3: Write minimal implementation**
- Use `lower_90_mw` and `upper_90_mw` as chart datasets.
- Configure Chart.js to fill the region between them.

**Step 4: Run test to verify pass**
- Run: `python -m pytest tests/test_ui_integration.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add ui/app.js tests/test_ui_integration.py
git commit -m "feat: shade forecast confidence band"
```

### Task 3: Verify band health in the API contract

**Objective:** Ensure the forecast contract continues to expose valid confidence intervals.

**Files:**
- Modify: `tests/test_api.py`
- Modify: `tests/test_forecast_pipeline.py`

**Step 1: Write failing test**
- Assert interval arrays are the same length as `net_demand_mw` and every point satisfies `lower_90_mw <= net_demand_mw <= upper_90_mw`.

**Step 2: Run test to verify failure**
- Run: `python -m pytest tests/test_api.py tests/test_forecast_pipeline.py -q`
- Expected: FAIL if the invariants are missing.

**Step 3: Write minimal implementation**
- No backend contract changes needed; keep the checks as regression coverage.

**Step 4: Run test to verify pass**
- Run: `python -m pytest tests/test_api.py tests/test_forecast_pipeline.py -q`
- Expected: PASS

**Step 5: Commit**
```bash
git add tests/test_api.py tests/test_forecast_pipeline.py
git commit -m "test: cover forecast confidence bands"
```
