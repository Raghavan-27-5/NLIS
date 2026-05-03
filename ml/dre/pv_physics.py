"""PV physics for the minimal hyperlocal MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

PVType = Literal["rooftop", "kusum_c", "kusum_a"]


@dataclass(frozen=True)
class FeederSpec:
    feeder_id: str
    pv_type: PVType
    rated_mw: float
    tilt_deg: float
    azimuth_deg: float
    lat: float
    lon: float
    gamma: float = -0.004
    noct: float = 44.0
    eta_panel: float = 0.195
    eta_inv: float = 0.975


def compute_tcell(
    g_poa: np.ndarray,
    t_amb: np.ndarray,
    noct: float = 44.0,
) -> np.ndarray:
    """NOCT cell temperature model."""
    safe_g = np.where(np.isfinite(g_poa) & (g_poa >= 0), g_poa, 0.0)
    safe_t = np.where(np.isfinite(t_amb), t_amb, 25.0)
    return safe_t + safe_g * (noct - 20.0) / 800.0


def eta_temperature(
    t_cell: np.ndarray,
    gamma: float = -0.004,
    t_stc: float = 25.0,
) -> np.ndarray:
    """Temperature derating factor."""
    return np.maximum(0.0, 1.0 + gamma * (t_cell - t_stc))


def compute_soiling_factor(
    last_rain_days: np.ndarray,
    pv_type: PVType,
) -> np.ndarray:
    """Simple soiling accumulation with rain reset proxy."""
    rate = 0.001 if pv_type == "kusum_c" else 0.0015
    return np.maximum(0.7, 1.0 - rate * np.clip(last_rain_days, 0, 200))


def dre_generation(
    spec: FeederSpec,
    g_poa: np.ndarray,
    t_amb: np.ndarray,
    last_rain_days: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return DRE output, cell temp, and efficiency cascade in MW terms."""
    g_poa = np.asarray(g_poa, dtype=float)
    t_amb = np.asarray(t_amb, dtype=float)
    last_rain_days = np.asarray(last_rain_days, dtype=float)

    if g_poa.shape != t_amb.shape or g_poa.shape != last_rain_days.shape:
        raise ValueError("shape mismatch")

    g_safe = np.where(np.isfinite(g_poa), np.maximum(0.0, g_poa), 0.0)
    t_cell = compute_tcell(g_safe, t_amb, spec.noct)
    eta_t = eta_temperature(t_cell, spec.gamma)
    eta_s = compute_soiling_factor(last_rain_days, spec.pv_type)
    eta_total = spec.eta_panel * spec.eta_inv * eta_t * eta_s

    area_eff = spec.rated_mw * 1e6 / (spec.eta_panel * 1000.0)
    output_w = eta_total * g_safe * area_eff
    output_mw = output_w / 1e6

    return {
        "output_mw": output_mw,
        "t_cell": t_cell,
        "eta_total": eta_total,
        "g_poa_used": g_safe,
        "capacity_factor": np.where(spec.rated_mw > 0, output_mw / spec.rated_mw, 0.0),
    }
