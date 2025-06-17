import os
import csv
import time as timemodule
import numpy as np
import matplotlib.pyplot as plt

from pbls.synthetic import generate_synthetic_light_curve
from pbls.pbls import pbls_search
from pbls.mp_pbls import fast_pbls_search
from pbls.period_grids import generate_uniformfreq_period_grid
from pbls.paths import TESTRESULTSDIR


def test_runtime():
    """
    Test runtime of fast_pbls_search for various dataset sizes.
    """
    # Ensure result directories exist
    os.makedirs(TESTRESULTSDIR, exist_ok=True)
    csv_dir = os.path.join(TESTRESULTSDIR, 'csv')
    png_dir = os.path.join(TESTRESULTSDIR, 'png')
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)

    # Define test cases: (name, total_time_days, cadence_days)
    cases = [
        ('tess_10min', 28, 10/(60*24)),
        ('k2', 30*3, 30/(60*24)),
        ('tess_2min', 28, 2/(60*24)),
        ('tess_10min_multisector', 365, 10/(60*24)),
        ('kepler', 365*4, 30/(60*24)),
        #('plato', 365*2, 10/(60*24)),
        #('tess_2min_multisector', 365, 2/(60*24)),
    ]

    results = []
    for name, total_time, cadence in cases:

        N = total_time / cadence
        print(f"Running case: {name}, total_time={total_time} days, cadence={cadence*24*60:.2f} min, N={N:.0f} points")
        case_csv = os.path.join(csv_dir, f"{name}.csv")
        if os.path.exists(case_csv):
            with open(case_csv, 'r', newline='') as cf:
                reader = csv.reader(cf)
                next(reader)
                row = next(reader)
            npts = int(row[1])
            elapsed = float(row[2])
            results.append((name, npts, elapsed))
            print(f"Loaded cached results for {name}")
            continue

        # Generate periods via a linear frequency grid (oversampled more than 1x bc of cutoffs)
        # "Unity" sampling would run from Pmin=1/T to T/2.  Ofir+14 suggests that this approach
        # is inefficient.
        periods = generate_uniformfreq_period_grid(
            total_time, cadence, oversample=1, period_min=2.0, period_max=50.0
        )
        durations_hr = np.array([1,2,3,4])  # trial durations in units of hours

        # Compute duration fraction for synthetic light curve
        duration_frac = (durations_hr[0] / 24.0) / periods[0]
        # Generate light curve with box transit only
        time_arr, flux = generate_synthetic_light_curve(
            period=periods[0],
            duration=duration_frac,
            epoch=0.3,
            depth=0.01,
            total_time=total_time,
            cadence=cadence,
            noise_level=0.0
        )

        # Measure runtime
        start = timemodule.time()
        fast_pbls_search(
            time_arr,
            flux,
            periods,
            durations_hr,
            epoch_steps=50,
            poly_order=2
        )
        elapsed = timemodule.time() - start
        results.append((name, len(time_arr), elapsed))
        # Write individual case cache
        with open(case_csv, 'w', newline='') as cf:
            writer = csv.writer(cf)
            writer.writerow(['case', 'npoints', 'elapsed_time'])
            writer.writerow([name, len(time_arr), elapsed])

    # Merge individual case caches into overall CSV
    csv_path = os.path.join(csv_dir, 'test_runtime.csv')
    merged = []
    for name, _, _ in cases:
        case_csv = os.path.join(csv_dir, f"{name}.csv")
        if os.path.exists(case_csv):
            with open(case_csv, 'r', newline='') as cf:
                reader = csv.reader(cf)
                next(reader)
                row = next(reader)
                merged.append(row)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['case', 'npoints', 'elapsed_time'])
        writer.writerows(merged)

    # Plot runtime vs. number of points
    fig, ax = plt.subplots(figsize=(6, 4))
    for name, npts, elapsed in results:
        ax.plot(npts, elapsed, 'o', label=name)
    # Set x-axis to log scale
    ax.set_xscale('log')
    # Set y-axis to log scale
    ax.set_yscale('log')
    # Fit a linear regression line to the data
    npts_array = np.array([n for _, n, _ in results])
    elapsed_array = np.array([e for _, _, e in results])
    # Perform log-log linear regression
    log_n = np.log10(npts_array)
    log_t = np.log10(elapsed_array)
    m, b = np.polyfit(log_n, log_t, 1)

    # Generate fitted curve in original scale
    n_fit = np.logspace(log_n.min(), log_n.max(), 100)
    t_fit = 10**(m * np.log10(n_fit) + b)

    # Plot the fit line
    ax.plot(n_fit, t_fit, '-', label=f'Log-Log Fit: slope={m:.2f}')
    # Set labels, title, and legend using ax
    ax.set_xlabel('Number of points')
    ax.set_ylabel('Time (s per [96 cores * oversample])')
    ax.set_title('Runtime of fast_pbls_search vs. number of points')
    ax.legend()
    png_path = os.path.join(png_dir, 'test_runtime.png')
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    test_runtime()
    print('Test completed successfully.')
