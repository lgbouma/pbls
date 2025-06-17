import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import time as timemodule

from pbls.mp_pbls import fast_pbls_search
from pbls.period_grids import generate_uniformfreq_period_grid
from pbls.synthetic import generate_transit_rotation_light_curve
from pbls.paths import TESTRESULTSDIR


def test_fast_pbls_scaling():
    """
    Test fast_pbls_search scaling by measuring elapsed time versus number of workers.
    Caches results to a CSV in TESTRESULTSDIR and skips if cache exists.
    """
    os.makedirs(TESTRESULTSDIR, exist_ok=True)
    csv_path = os.path.join(TESTRESULTSDIR, "scaling_results.csv")
    img_path = os.path.join(TESTRESULTSDIR, "test_fast_pbls_scaling.png")
    if os.path.exists(csv_path):
        print(f"Scaling results cached in {csv_path}")

    # Generate synthetic light curve data
    total_time = 30.0  # days
    cadence = 0.01     # days
    time = np.arange(0, total_time, cadence)
    noise_level = 1e-10

    transit_dict = {
        'period': 3.1666,
        't0': 2.5,
        'depth': 0.0005,
        'duration': 0.1
    }
    rotation_dict = {
        'prot': 3.8,
        'a1': 0.04,
        'a2': 0.01,
        'phi1': 0.0,
        'phi2': np.pi / 4
    }
    flux = generate_transit_rotation_light_curve(
        time, transit_dict, rotation_dict, noise_level=noise_level
    )

    # Define periods via a linear frequency grid (oversample=5)
    periods = generate_uniformfreq_period_grid(
        total_time, cadence, oversample=1, period_min=2.0, period_max=50.0
    )
    durations = np.linspace(0.005, 0.02, 10)

    nworkers_list = [12, 24, 48, 96]
    results = []

    for nworkers in nworkers_list:
        start = timemodule.time()
        fast_pbls_search(
            time, flux, periods, durations,
            epoch_steps=50, poly_order=3,
            nworkers=nworkers
        )
        elapsed = timemodule.time() - start
        results.append((nworkers, elapsed))

    # Write results to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['nworkers', 'elapsed_time'])
        writer.writerows(results)

    # Plot scaling results against ideal linear trend
    n_arr = np.array([r[0] for r in results])
    t_arr = np.array([r[1] for r in results])
    # Ideal linear scaling based on first measurement
    constant = t_arr[0] * n_arr[0]
    ideal = constant / n_arr

    plt.figure(figsize=(6, 4))
    plt.plot(n_arr, t_arr, 'o-', label='Measured')
    plt.plot(n_arr, ideal, '--', label='Ideal linear scaling')
    plt.xlabel('Number of workers')
    plt.ylabel('Elapsed time (s)')
    plt.title('fast_pbls_search Scaling with nworkers')
    plt.legend()
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()

    
if __name__ == "__main__":
    test_fast_pbls_scaling()
    print("Test completed successfully.")