from datetime import datetime, timezone

from ml.dre.pv_physics import FeederSpec, dre_generation
from ml.dre.pv_residual import apply_residual_correction
from ml.forecasting.pipeline import forecast_substation
from ml.telemetry.models import TelemetrySnapshot


def test_forecast_pipeline_returns_net_demand_and_intervals():
    feeder = FeederSpec(
        feeder_id="RJ-KUSUM-001",
        pv_type="kusum_c",
        rated_mw=2.0,
        tilt_deg=18.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )

    t_amb_c = [34.0, 38.0, 41.0]
    ghi_wm2 = [850.0, 700.0, 500.0]
    humidity_pct = [30.0, 35.0, 40.0]
    last_rain_days = [2.0, 2.0, 2.0]

    result = forecast_substation(
        feeder=feeder,
        t_amb_c=t_amb_c,
        ghi_wm2=ghi_wm2,
        humidity_pct=humidity_pct,
        last_rain_days=last_rain_days,
        base_load_mw=435.0,
        ac_penetration=0.58,
        n_connections=20_000,
    )

    physics = dre_generation(
        feeder,
        ghi_wm2,
        t_amb_c,
        last_rain_days,
    )["output_mw"].tolist()
    expected_dre = apply_residual_correction(
        physics,
        {
            "ghi_wm2": ghi_wm2,
            "t_amb_c": t_amb_c,
            "humidity_pct": humidity_pct,
            "last_rain_days": last_rain_days,
        },
    )

    assert len(result["dre_generation_mw"]) == 3
    assert len(result["gross_demand_mw"]) == 3
    assert len(result["net_demand_mw"]) == 3
    assert len(result["lower_90_mw"]) == 3
    assert len(result["upper_90_mw"]) == 3
    assert len(result["feeders"]) == 1
    assert result["dre_generation_mw"] == expected_dre

    for gross, dre, net in zip(
        result["gross_demand_mw"], result["dre_generation_mw"], result["net_demand_mw"],
    ):
        assert abs((gross - dre) - net) < 1e-6

    for low, net, high in zip(result["lower_90_mw"], result["net_demand_mw"], result["upper_90_mw"]):
        assert low <= net <= high

    assert result["summary"]["peak_net_demand_mw"] >= result["summary"]["avg_net_demand_mw"]


def test_forecast_pipeline_uses_telemetry_to_bias_gross_demand_upward():
    feeder = FeederSpec(
        feeder_id="RJ-KUSUM-001",
        pv_type="kusum_c",
        rated_mw=2.0,
        tilt_deg=18.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )

    telemetry = TelemetrySnapshot(
        substation_id="Jaipur South 220kV",
        feeder_id="RJ-KUSUM-001",
        timestamp=datetime(2026, 5, 3, 14, 0, tzinfo=timezone.utc),
        load_mw=500.0,
        voltage_kv=33.2,
        frequency_hz=49.97,
        power_factor=0.96,
        transformer_loading_pct=74.5,
        feeder_loading_pct=68.25,
    )

    kwargs = dict(
        feeder=feeder,
        t_amb_c=[34.0, 38.0],
        ghi_wm2=[850.0, 700.0],
        humidity_pct=[30.0, 35.0],
        last_rain_days=[2.0, 2.0],
        base_load_mw=435.0,
        ac_penetration=0.58,
        n_connections=20_000,
    )

    baseline = forecast_substation(**kwargs)
    biased = forecast_substation(**kwargs, telemetry=telemetry)

    assert len(biased["gross_demand_mw"]) == len(baseline["gross_demand_mw"]) == 2
    assert all(b > a for a, b in zip(baseline["gross_demand_mw"], biased["gross_demand_mw"]))
    assert all(abs((gross - dre) - net) < 1e-6 for gross, dre, net in zip(biased["gross_demand_mw"], biased["dre_generation_mw"], biased["net_demand_mw"]))


def test_forecast_pipeline_aggregates_multiple_feeders():
    rooftop = FeederSpec(
        feeder_id="RJ-RT-001",
        pv_type="rooftop",
        rated_mw=0.8,
        tilt_deg=20.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )
    kusum = FeederSpec(
        feeder_id="RJ-KUSUM-001",
        pv_type="kusum_c",
        rated_mw=2.0,
        tilt_deg=18.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )

    result = forecast_substation(
        feeders=[rooftop, kusum],
        t_amb_c=[34.0, 38.0],
        ghi_wm2=[850.0, 700.0],
        humidity_pct=[30.0, 35.0],
        last_rain_days=[2.0, 2.0],
        base_load_mw=435.0,
        ac_penetration=0.58,
        n_connections=20_000,
    )

    assert len(result["feeders"]) == 2
    expected_total = [
        sum(parts)
        for parts in zip(*(item["dre_generation_mw"] for item in result["feeders"]))
    ]
    assert result["dre_generation_mw"] == expected_total


def test_forecast_pipeline_uses_topography_and_connection_counts():
    feeder = FeederSpec(
        feeder_id="RJ-KUSUM-001",
        pv_type="kusum_c",
        rated_mw=2.0,
        tilt_deg=18.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )

    low_connections = forecast_substation(
        feeder=feeder,
        t_amb_c=[36.0, 39.0],
        ghi_wm2=[880.0, 760.0],
        humidity_pct=[30.0, 34.0],
        last_rain_days=[2.0, 2.0],
        base_load_mw=300.0,
        ac_penetration=0.40,
        n_connections=5_000,
    )
    high_connections = forecast_substation(
        feeder=feeder,
        t_amb_c=[36.0, 39.0],
        ghi_wm2=[880.0, 760.0],
        humidity_pct=[30.0, 34.0],
        last_rain_days=[2.0, 2.0],
        base_load_mw=300.0,
        ac_penetration=0.40,
        n_connections=25_000,
    )
    topo_adjusted = forecast_substation(
        feeder=feeder,
        t_amb_c=[36.0, 39.0],
        ghi_wm2=[880.0, 760.0],
        humidity_pct=[30.0, 34.0],
        last_rain_days=[2.0, 2.0],
        base_load_mw=300.0,
        ac_penetration=0.40,
        n_connections=25_000,
        topo_features={"elevation_m": 1200.0, "slope_deg": 10.0, "aspect_deg": 180.0},
    )

    assert all(b > a for a, b in zip(low_connections["gross_demand_mw"], high_connections["gross_demand_mw"]))
    assert topo_adjusted["downscaled_weather"]["temp"] != high_connections["downscaled_weather"]["temp"]
    assert topo_adjusted["dre_generation_mw"] != high_connections["dre_generation_mw"]
