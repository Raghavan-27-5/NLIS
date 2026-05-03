import pytest

from ml.dre.pv_residual import apply_residual_correction


def test_residual_correction_is_deterministic_and_bounded():
    physics = [1.0, 2.0, 3.0]
    features = {
        "ghi_wm2": [100.0, 700.0, 900.0],
        "t_amb_c": [20.0, 35.0, 42.0],
        "humidity_pct": [25.0, 55.0, 80.0],
        "last_rain_days": [1.0, 7.0, 30.0],
    }

    corrected_1 = apply_residual_correction(physics, features)
    corrected_2 = apply_residual_correction(physics, features)

    assert corrected_1 == corrected_2
    assert len(corrected_1) == len(physics)
    for base, corrected in zip(physics, corrected_1):
        assert corrected >= 0.0
        assert corrected >= base * 0.90
        assert corrected <= base * 1.08 + 1e-9


def test_residual_correction_responds_to_features():
    physics = [2.0, 2.0]
    low_signal = {
        "ghi_wm2": [50.0, 80.0],
        "t_amb_c": [20.0, 22.0],
        "humidity_pct": [80.0, 85.0],
        "last_rain_days": [0.0, 1.0],
    }
    high_signal = {
        "ghi_wm2": [850.0, 900.0],
        "t_amb_c": [36.0, 40.0],
        "humidity_pct": [25.0, 30.0],
        "last_rain_days": [12.0, 18.0],
    }

    low = apply_residual_correction(physics, low_signal)
    high = apply_residual_correction(physics, high_signal)

    assert low != high
    assert all(corrected >= 0.0 for corrected in low)
    assert all(corrected >= 0.0 for corrected in high)
    assert max(high) >= max(low)
