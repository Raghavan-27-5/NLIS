import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ml.weather.ingest import fetch_era5


class _ERA5Handler(BaseHTTPRequestHandler):
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
def era5_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ERA5Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_fetch_era5_reads_local_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "era5_cache.json"
    cache_path.write_text(
        json.dumps(
            {
                "temp": [34.0, 38.0],
                "ghi": [850.0, 700.0],
                "humidity": [30.0, 35.0],
            }
        )
    )
    monkeypatch.setenv("HYPERLOCAL_ERA5_CACHE", str(cache_path))
    monkeypatch.setenv("HYPERLOCAL_ERA5_URL", "http://127.0.0.1:9/should-not-be-used")

    data = fetch_era5(26.9, 75.8, "2026-05-01", "2026-05-02")

    assert data == {
        "temp": [34.0, 38.0],
        "ghi": [850.0, 700.0],
        "humidity": [30.0, 35.0],
    }


def test_fetch_era5_uses_remote_when_cache_missing(monkeypatch, era5_server):
    _ERA5Handler.payload = {
        "temp": [30.5, 31.0],
        "ghi": [900.0, 875.0],
        "humidity": [22.0, 24.0],
    }
    monkeypatch.delenv("HYPERLOCAL_ERA5_CACHE", raising=False)
    monkeypatch.setenv("HYPERLOCAL_ERA5_URL", f"http://127.0.0.1:{era5_server.server_address[1]}/era5")

    data = fetch_era5(26.9, 75.8, "2026-05-01", "2026-05-02")

    assert data == _ERA5Handler.payload


def test_fetch_era5_without_cache_or_remote_raises_clear_error(monkeypatch):
    monkeypatch.delenv("HYPERLOCAL_ERA5_CACHE", raising=False)
    monkeypatch.delenv("HYPERLOCAL_ERA5_URL", raising=False)

    with pytest.raises(RuntimeError, match="HYPERLOCAL_ERA5_URL"):
        fetch_era5(26.9, 75.8, "2026-05-01", "2026-05-02")


def test_fetch_era5_rejects_remote_schema_errors(monkeypatch, era5_server):
    _ERA5Handler.payload = {"temp": [1.0], "ghi": [2.0]}
    monkeypatch.delenv("HYPERLOCAL_ERA5_CACHE", raising=False)
    monkeypatch.setenv("HYPERLOCAL_ERA5_URL", f"http://127.0.0.1:{era5_server.server_address[1]}/era5")

    with pytest.raises(RuntimeError, match="humidity"):
        fetch_era5(26.9, 75.8, "2026-05-01", "2026-05-02")
