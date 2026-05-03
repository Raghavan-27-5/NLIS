import pytest

from ml.forecasting.calibration import calibrate_forecast


def test_calibrate_forecast_applies_bounded_additive_bias():
    forecast = [10.0, 12.0, 14.0]
    observed = [13.0, 15.0, 17.0]

    result = calibrate_forecast(forecast, observed, max_bias_fraction=0.10)

    assert result["raw_bias"] == pytest.approx(3.0)
    assert result["bias"] == pytest.approx(1.2)
    assert result["bias_limit"] == pytest.approx(1.2)
    assert result["calibrated_forecast"] == pytest.approx([11.2, 13.2, 15.2])


def test_calibrate_forecast_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        calibrate_forecast([1.0, 2.0], [1.0], max_bias_fraction=0.1)
