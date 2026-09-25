from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class FlexibleAsset:
    name: str
    max_power_mw: float
    energy_required_mwh: float
    available: list[bool]


def optimize_absorption(surplus_mw: list[float], assets: list[FlexibleAsset], interval_hours: float = 0.5):
    """Schedule flexible demand to absorb predicted renewable surplus.

    Linear program: maximize absorbed energy subject to interval surplus, asset power,
    availability, and per-asset total-energy limits.
    """
    surplus = np.asarray(surplus_mw, dtype=float)
    T = len(surplus)
    A = len(assets)
    n = A * T

    # linprog minimizes, so negative energy means maximize absorption.
    c = np.full(n, -interval_hours)
    bounds = []
    for asset in assets:
        if len(asset.available) != T:
            raise ValueError(f"{asset.name}: availability length must equal surplus length")
        for t in range(T):
            bounds.append((0.0, asset.max_power_mw if asset.available[t] else 0.0))

    A_ub, b_ub = [], []

    # Across assets, scheduled power cannot exceed predicted surplus in each interval.
    for t in range(T):
        row = np.zeros(n)
        for a in range(A):
            row[a * T + t] = 1.0
        A_ub.append(row)
        b_ub.append(max(0.0, surplus[t]))

    # Each asset has a total energy requirement/cap.
    for a, asset in enumerate(assets):
        row = np.zeros(n)
        row[a * T : (a + 1) * T] = interval_hours
        A_ub.append(row)
        b_ub.append(asset.energy_required_mwh)

    result = linprog(c, A_ub=np.asarray(A_ub), b_ub=np.asarray(b_ub), bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(result.message)

    schedule = result.x.reshape(A, T)
    absorbed_mwh = schedule.sum() * interval_hours
    available_mwh = np.maximum(surplus, 0).sum() * interval_hours
    return {
        "schedule_mw": {asset.name: schedule[i].round(3).tolist() for i, asset in enumerate(assets)},
        "absorbed_mwh": float(absorbed_mwh),
        "available_surplus_mwh": float(available_mwh),
        "capture_rate": float(absorbed_mwh / available_mwh) if available_mwh else 0.0,
    }
