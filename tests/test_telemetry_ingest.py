import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ml.telemetry.ingest import fetch_telemetry
from ml.telemetry.models import TelemetrySnapshot


class _TelemetryHandler(BaseHTTPRequestHandler):
    payload = None

    def do_GET(self):
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def telemetry_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TelemetryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_fetch_telemetry_reads_local_cache(monkeypatch, tmp_path):
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
    cache_path.write_text(json.dumps(payload))
    monkeypatch.setenv("HYPERLOCAL_TELEMETRY_CACHE", str(cache_path))
    monkeypatch.setenv("HYPERLOCAL_TELEMETRY_URL", "http://127.0.0.1:9/should-not-be-used")

    snapshot = fetch_telemetry()

    assert isinstance(snapshot, TelemetrySnapshot)
    assert snapshot.substation_id == "SS-14"
    assert snapshot.feeder_id == "FD-07"
    assert snapshot.timestamp == datetime(2026, 5, 3, 14, 0, tzinfo=timezone.utc)
    assert snapshot.load_mw == pytest.approx(18.5)
    assert snapshot.voltage_kv == pytest.approx(33.2)
    assert snapshot.frequency_hz == pytest.approx(49.97)
    assert snapshot.power_factor == pytest.approx(0.96)
    assert snapshot.transformer_loading_pct == pytest.approx(74.5)
    assert snapshot.feeder_loading_pct == pytest.approx(68.25)


def test_fetch_telemetry_uses_remote_when_cache_missing(monkeypatch, telemetry_server):
    _TelemetryHandler.payload = {
        "substation_id": "SS-21",
        "feeder_id": "FD-09",
        "timestamp": "2026-05-03T15:30:00Z",
        "load_mw": 21.25,
        "voltage_kv": 132.0,
        "frequency_hz": 50.01,
        "power_factor": 0.93,
    }
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_CACHE", raising=False)
    monkeypatch.setenv(
        "HYPERLOCAL_TELEMETRY_URL",
        f"http://127.0.0.1:{telemetry_server.server_address[1]}/telemetry",
    )

    snapshot = fetch_telemetry()

    assert snapshot.substation_id == "SS-21"
    assert snapshot.feeder_id == "FD-09"
    assert snapshot.timestamp == datetime(2026, 5, 3, 15, 30, tzinfo=timezone.utc)
    assert snapshot.load_mw == pytest.approx(21.25)
    assert snapshot.voltage_kv == pytest.approx(132.0)
    assert snapshot.frequency_hz == pytest.approx(50.01)
    assert snapshot.power_factor == pytest.approx(0.93)
    assert snapshot.transformer_loading_pct is None
    assert snapshot.feeder_loading_pct is None


def test_fetch_telemetry_without_cache_or_remote_raises_clear_error(monkeypatch):
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_CACHE", raising=False)
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_URL", raising=False)

    with pytest.raises(RuntimeError, match="HYPERLOCAL_TELEMETRY_URL"):
        fetch_telemetry()


def test_fetch_telemetry_rejects_remote_schema_errors(monkeypatch, telemetry_server):
    _TelemetryHandler.payload = {
        "substation_id": "SS-21",
        "feeder_id": "FD-09",
        "timestamp": "2026-05-03T15:30:00Z",
        "load_mw": 21.25,
        "voltage_kv": 132.0,
        "frequency_hz": 50.01,
    }
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_CACHE", raising=False)
    monkeypatch.setenv(
        "HYPERLOCAL_TELEMETRY_URL",
        f"http://127.0.0.1:{telemetry_server.server_address[1]}/telemetry",
    )

    with pytest.raises(RuntimeError, match="power_factor"):
        fetch_telemetry()


def test_fetch_telemetry_rejects_invalid_cache_json(monkeypatch, tmp_path):
    cache_path = tmp_path / "telemetry_cache.json"
    cache_path.write_text("not-json")
    monkeypatch.setenv("HYPERLOCAL_TELEMETRY_CACHE", str(cache_path))
    monkeypatch.delenv("HYPERLOCAL_TELEMETRY_URL", raising=False)

    with pytest.raises(RuntimeError, match="invalid.*cache.*JSON"):
        fetch_telemetry()
