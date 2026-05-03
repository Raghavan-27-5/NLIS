from ml.data.loaders import ForecastBundle, WeatherPointBundle, load_forecast_bundle_json
from ml.dre.pv_physics import FeederSpec
from ml.forecasting.pipeline import forecast_from_bundle


def test_forecast_from_bundle_matches_pipeline_contract(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        """
        {
          "substation_id": "Jaipur South 220kV",
          "feeder": {
            "feeder_id": "RJ-KUSUM-001",
            "pv_type": "kusum_c",
            "rated_mw": 2.0,
            "tilt_deg": 18.0,
            "azimuth_deg": 180.0,
            "lat": 26.9,
            "lon": 75.8
          },
          "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
            {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0},
            {"t_amb_c": 41.0, "ghi_wm2": 500.0, "humidity_pct": 40.0, "last_rain_days": 2.0}
          ],
          "base_load_mw": 435.0,
          "ac_penetration": 0.58,
          "n_connections": 20000
        }
        """
    )

    bundle = load_forecast_bundle_json(bundle_path)
    result = forecast_from_bundle(bundle)

    assert result["substation_id"] == "Jaipur South 220kV"
    assert result["feeder_id"] == "RJ-KUSUM-001"
    assert len(result["net_demand_mw"]) == 3
    assert result["summary"]["peak_net_demand_mw"] >= result["summary"]["avg_net_demand_mw"]


def test_forecast_from_multi_feeder_bundle_returns_aggregated_dre(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        """
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
              "lon": 75.8
            },
            {
              "feeder_id": "RJ-KUSUM-001",
              "pv_type": "kusum_c",
              "rated_mw": 2.0,
              "tilt_deg": 18.0,
              "azimuth_deg": 180.0,
              "lat": 26.9,
              "lon": 75.8
            }
          ],
          "weather": [
            {"t_amb_c": 34.0, "ghi_wm2": 850.0, "humidity_pct": 30.0, "last_rain_days": 2.0},
            {"t_amb_c": 38.0, "ghi_wm2": 700.0, "humidity_pct": 35.0, "last_rain_days": 2.0}
          ],
          "base_load_mw": 435.0,
          "ac_penetration": 0.58,
          "n_connections": 20000,
          "topo_features": {
            "elevation_m": 1200.0,
            "slope_deg": 10.0,
            "aspect_deg": 180.0
          }
        }
        """
    )

    bundle = load_forecast_bundle_json(bundle_path)
    result = forecast_from_bundle(bundle)

    assert len(result["feeders"]) == 2
    assert result["downscaled_weather"]["temp"][0] != 34.0
