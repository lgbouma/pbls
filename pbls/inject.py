from __future__ import annotations

import numpy as np
from typing import Iterable

def inject_transit(
    time: Iterable[float],
    flux: Iterable[float],
    inject_dict: dict,
):
    """
    Inject a box-shaped transit into a light curve.

    Parameters
    ----------
    time : array-like
        Timestamps (days).
    flux : array-like
        Flux values. Will not be modified in-place.
    inject_dict : dict
        Dictionary with required keys:
            - 'period' (float, days)
            - 'duration_hr' (float, hours)
            - 'depth' (float, same units as flux; e.g., relative flux)
            - 'epoch' (float, days)

    Returns
    -------
    np.ndarray
        New flux array with the transit injected.
    """
    t = np.asarray(time, dtype=float)
    f = np.asarray(flux, dtype=float)

    # Extract required parameters from inject_dict
    required = {"period", "duration_hr", "depth", "epoch"}
    missing = required - inject_dict.keys()
    if missing:
        raise KeyError(f"inject_dict missing keys: {sorted(missing)}")
    period = float(inject_dict["period"])
    duration_hr = float(inject_dict["duration_hr"])
    depth = float(inject_dict["depth"])
    epoch = float(inject_dict["epoch"])

    if period <= 0:
        raise ValueError("period must be > 0")
    if duration_hr <= 0:
        raise ValueError("duration_hr must be > 0")
    if depth < 0:
        raise ValueError("depth must be >= 0")

    duration_days = duration_hr / 24.0
    t0 = epoch

    # Box-transit mask: points within half-duration of the nearest transit center.
    # in_transit when phase distance from center < half duration.
    in_transit = np.abs(((t - t0 + 0.5 * period) % period) - 0.5 * period) < 0.5 * duration_days

    out = f.copy()
    out[in_transit] -= depth
    return out