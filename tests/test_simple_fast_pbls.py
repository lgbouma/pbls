import os
import time
import numpy as np
import pytest

from pbls.pbls import pbls_search
# from pbls.jit_pbls import fast_pbls_search # BROKEN
from pbls.mp_pbls import fast_pbls_search
from pbls.synthetic import generate_transit_rotation_light_curve
from pbls.paths import TESTRESULTSDIR

def test_fast_vs_standard_pbls_search():
    # --- generate a small synthetic light curve ---
    total_time = 30.0  # days
    cadence = 0.01     # days
    t = np.arange(0, total_time, cadence)

    transit_dict = {
        'period': 3.1666,      # days
        't0': 2.5,             # central transit time
        'depth': 0.0005,        # fractional flux drop
        'duration': 0.1        # fractional duration
    }
    rotation_dict = {
        'prot': 3.8,         # stellar rotation period in days
        'a1': 0.04,          # amplitude of primary sinusoid
        'a2': 0.01,         # amplitude of secondary sinusoid
        'phi1': 0.0,         # phase offset for primary sinusoid
        'phi2': np.pi / 4    # phase offset for secondary sinusoid
    }

    flux = generate_transit_rotation_light_curve(t, transit_dict, rotation_dict, noise_level=1e-7)

    periods = np.linspace(3, 3.3, 10)         # Trial periods in days
    durations = np.linspace(0.005, 0.02, 10)    # Trial durations (as a fraction of period)

    # --- run standard pbls_search ---
    t0 = time.perf_counter()
    res_std = pbls_search(t, flux, periods, durations, epoch_steps=50, poly_order=2)
    dt_std = time.perf_counter() - t0

    # --- run accelerated fast_pbls_search ---
    t1 = time.perf_counter()
    res_fast = fast_pbls_search(t, flux, periods, durations, epoch_steps=50, poly_order=2)
    dt_fast = time.perf_counter() - t1

    # --- report performance ---
    print(f"\npbls_search runtime: {dt_std:.3f}s, fast_pbls_search runtime: {dt_fast:.3f}s")

    # --- compare best_params ---
    bp_std = res_std['best_params']
    bp_fast = res_fast['best_params']
    for key in ('period', 'duration', 'epoch', 'depth'):
        print(bp_std[key], bp_fast[key])
        #assert pytest.approx(bp_std[key], rel=1e-6, abs=1e-8) == bp_fast[key]
    
    print(bp_std['snr'], bp_fast['snr'])
    #assert pytest.approx(bp_std['snr'], rel=1e-5) == bp_fast['snr']

if __name__ == "__main__":
    # Run the test function
    test_fast_vs_standard_pbls_search()