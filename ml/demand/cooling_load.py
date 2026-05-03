"""Cooling-load model for the minimal hyperlocal MVP."""

from __future__ import annotations

import numpy as np


def heat_index_rothfusz(
    t_db: np.ndarray,
    rh: np.ndarray,
) -> np.ndarray:
    """Rothfusz regression with a low-temperature fallback."""
    T = np.asarray(t_db, float)
    R = np.asarray(rh, float)
    hi = (
        -8.78
        + 1.611 * T
        - 0.0123 * T * R
        + 0.00085 * T * R * R
        - 0.0116 * R
        + 0.000912 * T * T * R
        - 0.0000337 * T * T * R * R
        + 0.347 * R
        - 0.00159 * R * R
    )
    simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + R * 0.094)
    return np.where(T > 26.7, hi, simple)


def ac_usage_factor(
    t_db: np.ndarray,
    rh: np.ndarray,
    beta_0: float = -6.84,
    beta_1: float = 0.18,
) -> np.ndarray:
    """Sigmoid duty-cycle factor from heat index."""
    hi = heat_index_rothfusz(t_db, rh)
    logit = beta_0 + beta_1 * hi
    return 1.0 / (1.0 + np.exp(-np.clip(logit, -20, 20)))


def ac_penetration_logistic(
    year: int | np.ndarray,
    alpha_max: float,
    k: float,
    t0: float,
) -> np.ndarray:
    """α_AC(s, year) logistic diffusion by income decile."""
    y = np.asarray(year, float)
    return alpha_max / (1.0 + np.exp(-k * (y - t0)))


def cooling_load_mw(
    t_db: np.ndarray,
    rh: np.ndarray,
    alpha_ac: np.ndarray,
    n_connections: np.ndarray,
    w_rated_kw: float = 1.5,
    cop: float = 3.2,
    occupancy: np.ndarray | None = None,
) -> np.ndarray:
    """Return cooling load in MW with broadcasting across substations."""
    if occupancy is None:
        occupancy = np.ones_like(t_db)
    f_use = ac_usage_factor(t_db, rh)
    load_kw = (
        (1.0 / cop)
        * alpha_ac[None, :]
        * n_connections[None, :]
        * w_rated_kw
        * f_use[:, None]
        * occupancy[:, None]
    )
    return load_kw / 1000.0
