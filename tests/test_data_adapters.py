import json

from ml.data.loaders import ForecastBundle, load_forecast_bundle_json, load_weather_csv


def test_load_weather_csv_parses_real_columns(tmp_path):
    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "timestamp,temp_c,ghi_wm2,humidity_pct,last_rain_days\n"
        "2026-05-03T00:00:00Z,34.0,850.0,30.0,2.0\n"
        "2026-05-03T01:00:00Z,38.0,700.0,35.0,2.0\n"
    )

    weather = load_weather_csv(csv_path)

    assert weather["temp"] == [34.0, 38.0]
    assert weather["ghi"] == [850.0, 700.0]
    assert weather["humidity"] == [30.0, 35.0]
    assert weather["last_rain_days"] == [2.0, 2.0]


def test_load_forecast_bundle_json_builds_bundle(tmp_path):
    json_path = tmp_path / "bundle.json"
    json_path.write_text(
        json.dumps(
            {
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
        )
    )

    bundle = load_forecast_bundle_json(json_path)

    assert isinstance(bundle, ForecastBundle)
    assert bundle.substation_id == "Jaipur South 220kV"
    assert bundle.feeder.feeder_id == "RJ-KUSUM-001"
    assert len(bundle.feeders) == 1
    assert len(bundle.weather) == 2
    assert bundle.weather[0].t_amb_c == 34.0


def test_load_forecast_bundle_json_supports_multi_feeder_and_topography(tmp_path):
    json_path = tmp_path / "bundle.json"
    json_path.write_text(
        json.dumps(
            {
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
                    {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0}
                ],
                "base_load_mw": 435.0,
                "ac_penetration": 0.58,
                "n_connections": 20000,
                "topo_features": {"elevation_m": 1200.0, "slope_deg": 10.0, "aspect_deg": 180.0},
            }
        )
    )

    bundle = load_forecast_bundle_json(json_path)

    assert len(bundle.feeders) == 2
    assert bundle.topo_features == {"elevation_m": 1200.0, "slope_deg": 10.0, "aspect_deg": 180.0}
