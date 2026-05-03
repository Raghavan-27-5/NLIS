from ml.weather.downscale import downscale


def test_downscale_preserves_identity_without_topography():
    grid_data = {
        "temp": [34.0, 38.0],
        "ghi": [850.0, 700.0],
        "humidity": [30.0, 35.0],
    }

    assert downscale(grid_data, None) is grid_data
    assert downscale(grid_data, {}) is grid_data


def test_downscale_adjusts_with_topography_and_preserves_lengths():
    grid_data = {
        "temp": [34.0, 38.0],
        "ghi": [850.0, 700.0],
        "humidity": [30.0, 35.0],
        "other": [1.0, 2.0],
    }
    topo_features = {"elevation_m": 1200.0, "slope_deg": 10.0, "aspect_deg": 180.0}

    downscaled = downscale(grid_data, topo_features)

    assert downscaled is not grid_data
    assert downscaled["temp"] == [26.0, 30.0]
    assert downscaled["humidity"] == [36.0, 41.0]
    assert downscaled["other"] == [1.0, 2.0]
    assert len(downscaled["temp"]) == len(grid_data["temp"])
    assert len(downscaled["ghi"]) == len(grid_data["ghi"])
    assert len(downscaled["humidity"]) == len(grid_data["humidity"])
    assert downscaled["ghi"][0] < grid_data["ghi"][0]
    assert downscaled["ghi"][1] < grid_data["ghi"][1]
