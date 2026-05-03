import numpy as np

from ml.demand.cooling_load import cooling_load_mw


def test_cooling_load_increases_with_temperature():
    t_db = np.array([30.0, 45.0], dtype=float)
    rh = np.array([35.0, 35.0], dtype=float)
    alpha_ac = np.array([0.58], dtype=float)
    n_connections = np.array([10_000], dtype=float)

    load = cooling_load_mw(t_db, rh, alpha_ac, n_connections)

    assert load.shape == (2, 1)
    assert load[1, 0] > load[0, 0]
    assert load[0, 0] >= 0
