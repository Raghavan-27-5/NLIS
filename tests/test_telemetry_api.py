import json

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_telemetry_preview_endpoint_reads_configured_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "telemetry_cache.json"
    payload = {
        "substation_id": "SS-14",
        "feeder_id": "FD-07",
        "timestamp": "2026-05-03T14:00:00Z",
        "load_mw": 18.5,
        "voltage_kv": 33.2,
        "frequency_hz": 49.97,
        "power_factor": 0.96,
        "transformer_loading_pct": 74.5,
        "feeder_loading_pct": 68.25,
    }
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("HYPERLOCAL_TELEMETRY_CACHE", str(cache_path))
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_URL", raising=False)

    response = client.get("/v1/telemetry/preview")

    assert response.status_code == 200
    assert response.json() == payload
