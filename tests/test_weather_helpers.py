from ml.weather.features import build_weather_features


def test_weather_feature_builder_returns_derived_fields():
    features = build_weather_features(
        {
            "temp": [34.0, 38.0],
            "ghi": [850.0, 700.0],
            "humidity": [30.0, 35.0],
        }
    )

    assert features["temp"] == [34.0, 38.0]
    assert features["ghi"] == [850.0, 700.0]
    assert features["humidity"] == [30.0, 35.0]
    assert "heat_index" in features
    assert len(features["heat_index"] ) == 2
