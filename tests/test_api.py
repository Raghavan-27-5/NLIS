from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_forecast_endpoint_returns_net_demand():
    payload = {
        "substation_id": "Jaipur South 220kV",
        "feeder": {
            "feeder_id": "RJ-KUSUM-001",
            "pv_type": "kusum_c",
            "rated_mw": 2.0,
            "tilt_deg": 18.0,
            "azimuth_deg": 180.0,
            "lat": 26.9,
            "lon": 75.8,
        },
        "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
            {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0},
        ],
        "base_load_mw": 435.0,
        "ac_penetration": 0.58,
        "n_connections": 20000,
    }

    response = client.post("/v1/forecast", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["substation_id"] == "Jaipur South 220kV"
    assert body["feeder_id"] == "RJ-KUSUM-001"
    assert body["horizon"] is None
    assert len(body["gross_demand_mw"]) == 2
    assert len(body["net_demand_mw"]) == 2
    assert len(body["dre_generation_mw"]) == 2
    assert len(body["lower_90_mw"]) == 2
    assert len(body["upper_90_mw"]) == 2
    assert len(body["feeders"]) == 1
    assert all(dre >= 0.0 for dre in body["dre_generation_mw"])
    assert body["summary"]["avg_net_demand_mw"] <= body["summary"]["peak_net_demand_mw"]
    assert "heat_index" in body["weather_features"]


def test_forecast_endpoint_accepts_optional_telemetry_bias(tmp_path, monkeypatch):
    payload = {
        "substation_id": "Jaipur South 220kV",
        "feeder": {
            "feeder_id": "RJ-KUSUM-001",
            "pv_type": "kusum_c",
            "rated_mw": 2.0,
            "tilt_deg": 18.0,
            "azimuth_deg": 180.0,
            "lat": 26.9,
            "lon": 75.8,
        },
        "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
            {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0},
        ],
        "base_load_mw": 435.0,
        "ac_penetration": 0.58,
        "n_connections": 20000,
        "telemetry": {
            "substation_id": "Jaipur South 220kV",
            "feeder_id": "RJ-KUSUM-001",
            "timestamp": "2026-05-03T14:00:00Z",
            "load_mw": 500.0,
            "voltage_kv": 33.2,
            "frequency_hz": 49.97,
            "power_factor": 0.96,
            "transformer_loading_pct": 74.5,
            "feeder_loading_pct": 68.25,
        },
    }

    response = client.post("/v1/forecast", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["gross_demand_mw"]) == 2
    assert len(body["net_demand_mw"]) == 2
    assert all(abs((gross - dre) - net) < 1e-6 for gross, dre, net in zip(body["gross_demand_mw"], body["dre_generation_mw"], body["net_demand_mw"]))


def test_forecast_endpoint_supports_multiple_feeders_and_topography():
    payload = {
        "substation_id": "Jaipur South 220kV",
        "feeders": [
            {
                "feeder_id": "RJ-RT-001",
                "pv_type": "rooftop",
                "rated_mw": 0.8,
                "tilt_deg": 20.0,
                "azimuth_deg": 180.0,
                "lat": 26.9,
                "lon": 75.8,
            },
            {
                "feeder_id": "RJ-KUSUM-001",
                "pv_type": "kusum_c",
                "rated_mw": 2.0,
                "tilt_deg": 18.0,
                "azimuth_deg": 180.0,
                "lat": 26.9,
                "lon": 75.8,
            },
        ],
        "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
            {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0},
        ],
        "base_load_mw": 435.0,
        "ac_penetration": 0.58,
        "n_connections": 20000,
        "topo_features": {"elevation_m": 1200.0, "slope_deg": 10.0, "aspect_deg": 180.0},
    }

    response = client.post("/v1/forecast", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["feeders"]) == 2
    assert body["downscaled_weather"]["temp"][0] != payload["weather"][0]["t_amb_c"]


def test_forecast_endpoint_rejects_mismatched_telemetry():
    payload = {
        "substation_id": "Jaipur South 220kV",
        "feeder": {
            "feeder_id": "RJ-KUSUM-001",
            "pv_type": "kusum_c",
            "rated_mw": 2.0,
            "tilt_deg": 18.0,
            "azimuth_deg": 180.0,
            "lat": 26.9,
            "lon": 75.8,
        },
        "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
        ],
        "base_load_mw": 435.0,
        "ac_penetration": 0.58,
        "n_connections": 20000,
        "telemetry": {
            "substation_id": "Other SS",
            "feeder_id": "RJ-KUSUM-001",
            "timestamp": "2026-05-03T14:00:00Z",
            "load_mw": 500.0,
            "voltage_kv": 33.2,
            "frequency_hz": 49.97,
            "power_factor": 0.96,
        },
    }

    response = client.post("/v1/forecast", json=payload)

    assert response.status_code == 400
    assert "substation_id" in response.json()["detail"]
