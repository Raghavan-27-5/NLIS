import pytest

from ml.forecasting.scoring import score_forecast


def test_score_forecast_computes_error_metrics_and_interval_stats():
    forecast = [10.0, 12.0, 14.0]
    observed = [11.0, 11.0, 15.0]
    lower = [9.0, 10.0, 13.0]
    upper = [12.0, 13.0, 16.0]

    result = score_forecast(forecast, observed, lower=lower, upper=upper)

    assert result["n_points"] == 3
    assert result["bias"] == pytest.approx(-0.3333333333)
    assert result["mae"] == pytest.approx(1.0)
    assert result["rmse"] == pytest.approx(1.0)
    assert result["mape"] == pytest.approx((1.0 / 11.0 + 1.0 / 11.0 + 1.0 / 15.0) / 3.0 * 100.0)
    assert result["interval_coverage"] == pytest.approx(1.0)
    assert result["interval_width"] == pytest.approx(3.0)


def test_score_forecast_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        score_forecast([1.0, 2.0], [1.0], lower=[0.0, 0.0], upper=[2.0, 2.0])
