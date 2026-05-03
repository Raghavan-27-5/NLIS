import numpy as np

from ml.dre.pv_physics import FeederSpec, dre_generation


def test_dre_generation_drops_with_more_soiling():
    spec = FeederSpec(
        feeder_id="RJ-RT-001",
        pv_type="rooftop",
        rated_mw=1.0,
        tilt_deg=20.0,
        azimuth_deg=180.0,
        lat=26.9,
        lon=75.8,
    )
    g_poa = np.array([800.0, 800.0], dtype=float)
    t_amb = np.array([35.0, 35.0], dtype=float)
    last_rain_days = np.array([0.0, 60.0], dtype=float)

    result = dre_generation(spec, g_poa, t_amb, last_rain_days)

    assert result["output_mw"].shape == (2,)
    assert result["output_mw"][0] > 0
    assert result["output_mw"][1] < result["output_mw"][0]
    assert np.all(result["eta_total"] > 0)
