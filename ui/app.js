"use strict";

const API_BASE = new URLSearchParams(window.location.search).get("api")
  || window.HYPERLOCAL_API_BASE
  || window.location.origin;
const WEATHER_SOURCES = {
  Jaipur: "weather_sample.csv",
  Jodhpur: "weather_jodhpur.csv",
  Kota: "weather_kota.csv",
};
const BUNDLE_SOURCES = {
  "Jaipur South 220kV": "forecast_bundle.json",
  "Jodhpur North 132kV": "forecast_bundle_jodhpur.json",
  "Kota East 220kV": "forecast_bundle_kota.json",
};

const DEFAULT_SUBSTATION = "Jaipur South 220kV";
const DEFAULT_HORIZON = "Day-ahead (24h)";
const DEFAULT_BUNDLE = "Jaipur South 220kV";
const HORIZON_PRESETS = ["Intra-day (15-min)", "Day-ahead (24h)", "Week-ahead (168h)"];

const els = {
  refreshBtn: document.getElementById("refreshBtn"),
  refreshBtnTop: document.getElementById("refreshBtnTop"),
  refreshForecastBtn: document.getElementById("refreshForecastBtn"),
  horizonPresetButtons: Array.from(document.querySelectorAll("[data-horizon-preset]")),
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
  substationName: document.getElementById("substationName"),
  feederName: document.getElementById("feederName"),
  kpiAvgNet: document.getElementById("kpiAvgNet"),
  kpiPeakNet: document.getElementById("kpiPeakNet"),
  kpiPeakDre: document.getElementById("kpiPeakDre"),
  kpiRows: document.getElementById("kpiRows"),
  summaryMetrics: document.getElementById("summaryMetrics"),
  feederMetrics: document.getElementById("feederMetrics"),
  weatherMetrics: document.getElementById("weatherMetrics"),
  feederTableBody: document.getElementById("feederTableBody"),
  payloadPreview: document.getElementById("payloadPreview"),
  weatherPathText: document.getElementById("weatherPathText"),
  bundlePathText: document.getElementById("bundlePathText"),
  substationSelect: document.getElementById("substationSelect"),
  horizonSelect: document.getElementById("horizonSelect"),
  bundleSelect: document.getElementById("bundleSelect"),
  tempShift: document.getElementById("tempShift"),
  ghiScale: document.getElementById("ghiScale"),
  humidityShift: document.getElementById("humidityShift"),
  acShift: document.getElementById("acShift"),
  loadShift: document.getElementById("loadShift"),
  tempValue: document.getElementById("tempValue"),
  ghiValue: document.getElementById("ghiValue"),
  humidityValue: document.getElementById("humidityValue"),
  acValue: document.getElementById("acValue"),
  loadValue: document.getElementById("loadValue"),
  horizonLabel: document.getElementById("horizonLabel"),
  bundleLabel: document.getElementById("bundleLabel"),
  bandAlertChip: document.getElementById("bandAlertChip"),
  bandAlertValue: document.getElementById("bandAlertValue"),
  bandAlertText: document.getElementById("bandAlertText"),
  bandWidthText: document.getElementById("bandWidthText"),
  bandSeverityText: document.getElementById("bandSeverityText"),
  stationRiskChip: document.getElementById("stationRiskChip"),
  stationRiskBadge: document.getElementById("stationRiskBadge"),
  forecastMeta: document.getElementById("forecastMeta"),
  weatherMeta: document.getElementById("weatherMeta"),
  bundleMeta: document.getElementById("bundleMeta"),
};

const chartState = { dashboard: null, dre: null, demand: null };
let dashboardRequestSeq = 0;
let refreshTimer = null;
let refreshQueued = false;

els.weatherPathText.textContent = WEATHER_SOURCES.Jaipur;
els.bundlePathText.textContent = BUNDLE_SOURCES[DEFAULT_BUNDLE];
els.substationSelect.value = DEFAULT_SUBSTATION;
els.horizonSelect.value = DEFAULT_HORIZON;
els.bundleSelect.value = DEFAULT_BUNDLE;

function setStatus(text, kind = "idle") {
  els.statusText.innerHTML = text;
  els.statusDot.className = "statusdot";
  if (kind === "ok") els.statusDot.classList.add("ok");
  if (kind === "warn") els.statusDot.classList.add("warn");
}

function getHorizonScale() {
  const selected = els.horizonSelect.value;
  if (selected.startsWith("Intra-day")) return { loadScale: 0.92 };
  if (selected.startsWith("Week-ahead")) return { loadScale: 1.07 };
  return { loadScale: 1.0 };
}

function getWeatherSourceKey() {
  const sub = els.substationSelect.value;
  if (sub.startsWith("Jodhpur")) return "Jodhpur";
  if (sub.startsWith("Kota")) return "Kota";
  return "Jaipur";
}

function getSelectedPaths() {
  const substation = els.substationSelect.value;
  const bundleName = els.bundleSelect.value || substation;
  const bundlePath = BUNDLE_SOURCES[bundleName] || BUNDLE_SOURCES[DEFAULT_BUNDLE];
  const weatherKey = getWeatherSourceKey();
  const weatherPath = WEATHER_SOURCES[weatherKey] || WEATHER_SOURCES.Jaipur;
  return { bundlePath, weatherPath, weatherKey, substation, bundleName };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function max(values) {
  return Math.max(...values);
}

function min(values) {
  return Math.min(...values);
}

function fmtMw(value) {
  return `${value.toFixed(1)} MW`;
}

function fmtNum(value) {
  return Number.isFinite(value) ? value.toFixed(1) : "—";
}

function statusForRow(net, low, high) {
  if (net > high) return { label: "Above band", className: "red" };
  if (net < low) return { label: "Below band", className: "amber" };
  return { label: "Within band", className: "" };
}

function renderMetricList(target, metrics) {
  target.innerHTML = metrics.map((item) => `
    <div class="metric">
      <span>${item.label}</span>
      <strong>${item.value}</strong>
    </div>
  `).join("");
}

function renderBandChip(statusCounts, bundle) {
  const total = statusCounts.ok + statusCounts.amber + statusCounts.red;
  const outside = statusCounts.amber + statusCounts.red;
  const widths = bundle.upper.map((value, index) => value - bundle.lower[index]);
  const width = mean(widths);
  const maxWidth = max(widths);
  const label = outside === 0
    ? `Healthy · ${total} rows within band`
    : `${outside}/${total} rows outside band`;
  const severity = statusCounts.red > 0 ? "red" : outside > 0 ? "amber" : "green";
  els.bandAlertValue.textContent = `${label} · avg width ${fmtMw(width)}`;
  els.bandAlertText.textContent = label;
  els.bandWidthText.textContent = `${fmtMw(width)} avg · ${fmtMw(maxWidth)} max`;
  els.bandSeverityText.textContent = severity === "red" ? "Critical" : severity === "amber" ? "Warning" : "Healthy";
  els.bandAlertChip.classList.toggle("ok", severity === "green");
  els.bandAlertChip.classList.toggle("warn", severity !== "green");
  els.stationRiskChip.classList.toggle("ok", severity === "green");
  els.stationRiskChip.classList.toggle("warn", severity !== "green");
  els.stationRiskBadge.textContent = severity === "red" ? "Critical" : severity === "amber" ? "Elevated" : "Normal";
}

function destroyChart(key) {
  if (chartState[key]) {
    chartState[key].destroy();
    chartState[key] = null;
  }
}

function makeLineChart(canvasId, { labels, datasets, title, fills }) {
  const key = canvasId === "dashboardChart" ? "dashboard" : canvasId === "dreChart" ? "dre" : "demand";
  destroyChart(key);
  const ctx = document.getElementById(canvasId);
  if (fills && fills.length) {
    fills.forEach((fill) => {
      const source = datasets.find((dataset) => dataset.label === fill.sourceLabel);
      const target = datasets.find((dataset) => dataset.label === fill.targetLabel);
      if (source) {
        source.fill = target ? { target: datasets.indexOf(target), above: fill.color, below: fill.color } : fill.color;
        source.backgroundColor = fill.color;
      }
    });
  }
  return new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom" },
        title: { display: Boolean(title), text: title },
      },
      scales: {
        x: { grid: { color: "rgba(148,163,184,0.15)" } },
        y: { grid: { color: "rgba(148,163,184,0.15)" } },
      },
    },
  });
}
function setActiveTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tab);
  });
}

function bindTabs() {
  document.querySelectorAll(".tab-btn").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
}

function computeHeatIndex(tempC, humidityPct) {
  const T = Number(tempC);
  const R = Number(humidityPct);
  const tempF = T * 9 / 5 + 32;
  const hiF = (-42.379
    + 2.04901523 * tempF
    + 10.14333127 * R
    - 0.22475541 * tempF * R
    - 0.00683783 * tempF * tempF
    - 0.05481717 * R * R
    + 0.00122874 * tempF * tempF * R
    + 0.00085282 * tempF * R * R
    - 0.00000199 * tempF * tempF * R * R);
  return (hiF - 32) * 5 / 9;
}

function buildAdjustedWeather(rawWeather) {
  const tempShift = Number(els.tempShift.value || 0);
  const ghiScale = Number(els.ghiScale.value || 100) / 100;
  const humidityShift = Number(els.humidityShift.value || 0);
  const acShift = Number(els.acShift.value || 0) / 100;
  const loadShift = Number(els.loadShift.value || 0) / 100;
  const horizonScale = getHorizonScale().loadScale;

  const temp = rawWeather.temp.map((value) => value + tempShift);
  const ghi = rawWeather.ghi.map((value) => value * ghiScale);
  const humidity = rawWeather.humidity.map((value) => Math.max(0, value + humidityShift));
  const heatIndex = temp.map((value, index) => computeHeatIndex(value, humidity[index]));
  const acPenalty = Math.max(0, 1 - acShift * 0.2);
  const loadFactor = (1 + loadShift) * horizonScale;

  return {
    temp,
    ghi,
    humidity,
    heatIndex,
    tempShift,
    ghiScale,
    humidityShift,
    acShift,
    loadShift,
    horizonScale,
    acPenalty,
    loadFactor,
  };
}

function buildForecastRequest(rawBundle, adjustedWeather, controls) {
  const acPenetration = Math.min(1, Math.max(0, rawBundle.ac_penetration + controls.acShift));
  const nConnections = Math.max(1, Math.round(rawBundle.n_connections * (1 + controls.loadShift)));
  const baseLoadMw = rawBundle.base_load_mw * controls.loadFactor;
  return {
    substation_id: rawBundle.substation_id,
    feeder: rawBundle.feeder,
    weather: adjustedWeather.temp.map((value, index) => ({
      t_amb_c: value,
      ghi_wm2: adjustedWeather.ghi[index],
      humidity_pct: adjustedWeather.humidity[index],
      last_rain_days: rawBundle.weather[index]?.last_rain_days ?? 0,
    })),
    base_load_mw: baseLoadMw,
    ac_penetration: acPenetration,
    n_connections: nConnections,
    horizon: controls.horizon,
  };
}

function renderArchitecturePayload(bundle, weather, controls) {
  els.payloadPreview.textContent = JSON.stringify({
    api: {
      health: `${API_BASE}/v1/health`,
      weather_preview: `${API_BASE}/v1/weather/preview?path=${weather.path}`,
      bundle_raw: `${API_BASE}/v1/bundle/raw?path=${bundle.path}`,
      bundle_preview: `${API_BASE}/v1/bundle/preview?path=${bundle.path}`,
      forecast: `${API_BASE}/v1/forecast`,
    },
    substation: bundle.substation_id,
    feeder_id: bundle.feeder_id,
    controls,
    summary: bundle.summary,
    weather_features: weather.features,
  }, null, 2);
}

function updateControlLabels() {
  els.tempValue.textContent = `${els.tempShift.value} °C`;
  els.ghiValue.textContent = `${els.ghiScale.value}%`;
  els.humidityValue.textContent = `${els.humidityShift.value}%`;
  els.acValue.textContent = `${els.acShift.value}%`;
  els.loadValue.textContent = `${els.loadShift.value}%`;
  els.horizonLabel.textContent = els.horizonSelect.value;
  els.bundleLabel.textContent = els.bundleSelect.value;
  els.forecastMeta.textContent = `${els.substationSelect.value} · ${els.horizonSelect.value}`;
  els.weatherMeta.textContent = getWeatherSourceKey();
  els.bundleMeta.textContent = els.bundleSelect.value;
}

function buildDashboard(bundle, weather, controls) {
  const labels = bundle.net.map((_, index) => `T${index + 1}`);
  const statusCounts = { ok: 0, amber: 0, red: 0 };

  chartState.dashboard = makeLineChart("dashboardChart", {
    labels,
    datasets: [
      {
        label: "Gross demand",
        data: bundle.gross,
        borderColor: "#2458e0",
        backgroundColor: "rgba(36, 88, 224, 0.12)",
        tension: 0.32,
        fill: false,
      },
      {
        label: "DRE generation",
        data: bundle.dre,
        borderColor: "#128a57",
        backgroundColor: "rgba(18, 138, 87, 0.14)",
        tension: 0.32,
        fill: false,
      },
      {
        label: "Net demand",
        data: bundle.net,
        borderColor: "#c13b4a",
        backgroundColor: "rgba(193, 59, 74, 0.10)",
        tension: 0.32,
        fill: false,
      },
      {
        label: "Lower 90%",
        data: bundle.lower,
        borderColor: "rgba(194, 123, 0, 0.9)",
        borderDash: [6, 5],
        tension: 0.2,
        fill: false,
        pointRadius: 0,
      },
      {
        label: "Upper 90%",
        data: bundle.upper,
        borderColor: "rgba(194, 123, 0, 0.9)",
        borderDash: [6, 5],
        tension: 0.2,
        fill: false,
        pointRadius: 0,
      },
    ],
    fills: [
      { sourceLabel: "Upper 90%", targetLabel: "Lower 90%", color: "rgba(194, 123, 0, 0.10)" },
    ],
    title: `Forecast bundle preview · ${controls.substation} · ${els.horizonSelect.value}`,
  });

  els.kpiAvgNet.textContent = fmtMw(mean(bundle.net));
  els.kpiPeakNet.textContent = fmtMw(max(bundle.net));
  els.kpiPeakDre.textContent = fmtMw(max(bundle.dre));
  els.kpiRows.textContent = String(weather.rows);
  els.substationName.textContent = bundle.substation_id;
  els.feederName.textContent = bundle.feeder_id;

  renderMetricList(els.summaryMetrics, [
    { label: "Net demand mean", value: fmtMw(mean(bundle.net)) },
    { label: "Net demand peak", value: fmtMw(max(bundle.net)) },
    { label: "Net demand floor", value: fmtMw(min(bundle.net)) },
    { label: "Gross demand range", value: `${fmtMw(min(bundle.gross))} → ${fmtMw(max(bundle.gross))}` },
    { label: "DRE range", value: `${fmtMw(min(bundle.dre))} → ${fmtMw(max(bundle.dre))}` },
    { label: "Confidence width", value: fmtMw(bundle.upper[0] - bundle.net[0]) },
  ]);

  renderBandChip(statusCounts, bundle);
  renderMetricList(els.feederMetrics, [
    { label: "Feeder ID", value: bundle.feeder_id },
    { label: "Substation", value: bundle.substation_id },
    { label: "Horizon", value: els.horizonSelect.value },
    { label: "Editable inputs", value: "5 sliders" },
  ]);

  chartState.dre = makeLineChart("dreChart", {
    labels,
    datasets: [
      { label: "DRE generation", data: bundle.dre, borderColor: "#128a57", tension: 0.32 },
      { label: "GHI (scaled)", data: weather.ghi.map((value) => value / 120.0), borderColor: "#2458e0", tension: 0.32 },
      { label: "Heat index", data: weather.features.heat_index.map((value) => value / 10.0), borderColor: "#c27b00", tension: 0.32 },
    ],
    title: "DRE generation and weather signals",
  });

  chartState.demand = makeLineChart("demandChart", {
    labels,
    datasets: [
      { label: "Temperature", data: weather.temp, borderColor: "#2458e0", tension: 0.3 },
      { label: "Humidity", data: weather.humidity, borderColor: "#128a57", tension: 0.3 },
      { label: "Heat index", data: weather.features.heat_index, borderColor: "#c13b4a", tension: 0.3 },
      { label: "Gross demand", data: bundle.gross, borderColor: "#0f172a", tension: 0.3 },
    ],
    title: "Weather-to-demand sensitivity",
  });

  els.feederTableBody.innerHTML = labels.map((label, index) => {
    const status = statusForRow(bundle.net[index], bundle.lower[index], bundle.upper[index]);
    if (status.className === "amber") statusCounts.amber += 1;
    else if (status.className === "red") statusCounts.red += 1;
    else statusCounts.ok += 1;
    const badge = status.className ? `<span class="badge ${status.className}">${status.label}</span>` : `<span class="badge">${status.label}</span>`;
    return `
      <tr>
        <td>${label}</td>
        <td>${fmtNum(weather.temp[index])}</td>
        <td>${fmtNum(weather.ghi[index])}</td>
        <td>${fmtNum(weather.features.heat_index[index])}</td>
        <td>${fmtNum(bundle.gross[index])}</td>
        <td>${fmtNum(bundle.dre[index])}</td>
        <td>${fmtNum(bundle.net[index])}</td>
        <td>${badge}</td>
      </tr>
    `;
  }).join("");

  renderArchitecturePayload(bundle, weather, controls);
  return statusCounts;
}

async function fetchWeatherPayload(path) {
  const data = await fetchJson(`${API_BASE}/v1/weather/preview?path=${encodeURIComponent(path)}`);
  return { ...data, path };
}

async function fetchBundlePayload(path) {
  const data = await fetchJson(`${API_BASE}/v1/bundle/preview?path=${encodeURIComponent(path)}`);
  return { ...data, path };
}

async function refreshDashboard({ preserveTab = true } = {}) {
  const requestId = ++dashboardRequestSeq;
  try {
    setStatus("Loading editable dashboard data…", "warn");
    const { bundlePath, weatherPath, substation, bundleName } = getSelectedPaths();
    const [health, weather, bundlePreview, bundleRaw] = await Promise.all([
      fetchJson(`${API_BASE}/v1/health`),
      fetchWeatherPayload(weatherPath),
      fetchBundlePayload(bundlePath),
      fetchJson(`${API_BASE}/v1/bundle/raw?path=${encodeURIComponent(bundlePath)}`),
    ]);
    if (requestId !== dashboardRequestSeq) return;
    if (health?.status !== "ok") {
      throw new Error("health check did not return ok");
    }

    const controls = {
      substation,
      bundle: bundleName,
      horizon: els.horizonSelect.value,
      tempShift: Number(els.tempShift.value),
      ghiScale: Number(els.ghiScale.value),
      humidityShift: Number(els.humidityShift.value),
      acShift: Number(els.acShift.value),
      loadShift: Number(els.loadShift.value),
    };
    const adjustedWeather = buildAdjustedWeather(weather.weather);
    const forecastRequest = buildForecastRequest(bundleRaw, adjustedWeather, controls);
    const forecast = await fetchJson(`${API_BASE}/v1/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(forecastRequest),
    });
    if (requestId !== dashboardRequestSeq) return;

    const mergedWeather = {
      ...weather,
      weather: {
        temp: adjustedWeather.temp,
        ghi: adjustedWeather.ghi,
        humidity: adjustedWeather.humidity,
      },
      features: {
        ...weather.features,
        heat_index: adjustedWeather.heatIndex,
      },
    };
    const mergedBundle = {
      ...bundlePreview,
      gross: forecast.gross_demand_mw,
      dre: forecast.dre_generation_mw,
      net: forecast.net_demand_mw,
      lower: forecast.lower_90_mw,
      upper: forecast.upper_90_mw,
      path: bundlePath,
    };

    updateControlLabels();
    els.weatherPathText.textContent = weatherPath;
    els.bundlePathText.textContent = bundlePath;
    els.bundleSelect.value = bundleRaw.substation_id;
    buildDashboard(mergedBundle, mergedWeather, controls);
    setStatus(`Loaded ${substation} · ${els.horizonSelect.value} from the FastAPI MVP endpoints.`, "ok");
    if (!preserveTab) setActiveTab("dashboard");
  } catch (error) {
    if (requestId !== dashboardRequestSeq) return;
    setStatus(`Dashboard error: ${error.message}`, "warn");
    els.payloadPreview.textContent = JSON.stringify({ error: error.message }, null, 2);
  }
}

function bindControls() {
  const liveControls = [
    els.substationSelect,
    els.horizonSelect,
    els.bundleSelect,
    els.tempShift,
    els.ghiScale,
    els.humidityShift,
    els.acShift,
    els.loadShift,
  ];
  liveControls.forEach((element) => {
    element.addEventListener("input", () => {
      updateControlLabels();
      scheduleRefresh();
    });
    element.addEventListener("change", () => {
      updateControlLabels();
      scheduleRefresh();
    });
  });

  [els.refreshBtn, els.refreshBtnTop, els.refreshForecastBtn].forEach((button) => {
    button.addEventListener("click", () => refreshDashboard({ preserveTab: true }));
  });

  els.horizonPresetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      els.horizonSelect.value = button.dataset.horizonPreset;
      updateControlLabels();
      scheduleRefresh();
    });
  });
}

function scheduleRefresh() {
  if (refreshTimer) window.clearTimeout(refreshTimer);
  refreshQueued = true;
  refreshTimer = window.setTimeout(() => {
    refreshTimer = null;
    if (!refreshQueued) return;
    refreshQueued = false;
    refreshDashboard({ preserveTab: true });
  }, 180);
}

bindTabs();
bindControls();
setActiveTab("dashboard");
updateControlLabels();

if (window.Chart) {
  refreshDashboard({ preserveTab: true });
} else {
  setStatus("Chart.js failed to load. The data endpoints are still available.", "warn");
  els.payloadPreview.textContent = JSON.stringify({
    error: "Chart.js unavailable",
    weather_path: WEATHER_SOURCES.Jaipur,
    bundle_path: BUNDLE_SOURCES[DEFAULT_BUNDLE],
  }, null, 2);
}
