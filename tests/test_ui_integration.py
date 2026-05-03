from pathlib import Path

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]

WEATHER = ROOT / "sample_data/weather_sample.csv"
BUNDLE = ROOT / "sample_data/forecast_bundle.json"
BUNDLE_JODHPUR = ROOT / "sample_data/forecast_bundle_jodhpur.json"
BUNDLE_KOTA = ROOT / "sample_data/forecast_bundle_kota.json"


def test_root_redirects_to_ui():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers["location"].endswith("/ui/")


def test_ui_index_served():
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "Hyperlocal Forecast Dashboard" in response.text
    assert "substationSelect" in response.text
    assert "horizonSelect" in response.text
    assert "bundleSelect" in response.text
    assert "tempShift" in response.text
    assert "ghiScale" in response.text
    assert "humidityShift" in response.text
    assert "acShift" in response.text
    assert "loadShift" in response.text
    assert "refreshForecastBtn" in response.text
    assert "stationRiskChip" in response.text
    assert "stationRiskBadge" in response.text
    assert "/v1/weather/preview" in response.text
    assert "/v1/bundle/preview" in response.text
    assert "/v1/bundle/raw" in response.text
    assert "/v1/forecast" in response.text
    assert "/ui/app.js" in response.text


def test_ui_app_js_uses_api_routes_and_live_edit_controls():
    response = client.get("/ui/app.js")
    assert response.status_code == 200
    assert "/v1/weather/preview" in response.text
    assert "/v1/bundle/preview" in response.text
    assert "/v1/forecast" in response.text
    assert "substationSelect" in response.text
    assert "horizonSelect" in response.text
    assert "bundleSelect" in response.text
    assert "tempShift" in response.text
    assert "ghiScale" in response.text
    assert "humidityShift" in response.text
    assert "acShift" in response.text
    assert "loadShift" in response.text
    assert "refreshForecastBtn" in response.text
    assert str(WEATHER) in response.text
    assert str(BUNDLE) in response.text
    assert str(BUNDLE_JODHPUR) in response.text
    assert str(BUNDLE_KOTA) in response.text


def test_ui_app_js_defines_band_status_before_use():
    response = client.get("/ui/app.js")
    assert response.status_code == 200
    source = response.text
    status_counts_idx = source.index("const statusCounts = { ok: 0, amber: 0, red: 0 };")
    render_band_idx = source.index("renderBandChip(statusCounts, bundle);")
    assert status_counts_idx < render_band_idx


def test_weather_preview_endpoint_returns_features():
    response = client.get(f"/v1/weather/preview?path={WEATHER}")
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert "heat_index" in body["features"]
    assert body["weather"]["temp"][0] == 34.0


def test_bundle_preview_endpoint_returns_forecast_summary():
    response = client.get(f"/v1/bundle/preview?path={BUNDLE}")
    assert response.status_code == 200
    body = response.json()
    assert body["substation_id"] == "Jaipur South 220kV"
    assert "summary" in body
    assert "avg_net_demand_mw" in body["summary"]
    assert len(body["gross_demand_mw"]) == 6
    assert len(body["net_demand_mw"]) == 6


def test_bundle_raw_endpoint_exposes_structured_payload():
    response = client.get(f"/v1/bundle/raw?path={BUNDLE_JODHPUR}")
    assert response.status_code == 200
    body = response.json()
    assert body["substation_id"] == "Jodhpur North 132kV"
    assert body["feeder"]["feeder_id"] == "RJ-KUSUM-014"
    assert len(body["weather"]) == 6


def test_forecast_endpoint_responds_to_live_edit_controls():
    bundle = client.get(f"/v1/bundle/raw?path={BUNDLE_KOTA}").json()
    weather = client.get(f"/v1/weather/preview?path={WEATHER}").json()
    body = {
        "substation_id": bundle["substation_id"],
        "feeder": bundle["feeder"],
        "weather": [
            {
                "t_amb_c": point + 2.0,
                "ghi_wm2": ghi * 0.95,
                "humidity_pct": min(100.0, humidity + 4.0),
                "last_rain_days": rain,
            }
            for point, ghi, humidity, rain in zip(
                weather["weather"]["temp"],
                weather["weather"]["ghi"],
                weather["weather"]["humidity"],
                weather["weather"]["last_rain_days"],
            )
        ],
        "base_load_mw": bundle["base_load_mw"] * 1.05,
        "ac_penetration": min(1.0, bundle["ac_penetration"] + 0.05),
        "n_connections": bundle["n_connections"],
        "horizon": "Day-ahead (24h)",
    }
    response = client.post("/v1/forecast", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["substation_id"] == bundle["substation_id"]
    assert result["horizon"] == "Day-ahead (24h)"
    assert len(result["net_demand_mw"]) == 6
    assert len(result["dre_generation_mw"]) == 6
