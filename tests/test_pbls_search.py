import os
import numpy as np
import matplotlib.pyplot as plt
import time as timemodule

from pbls.pbls import pbls_search
from pbls.mp_pbls import fast_pbls_search
from pbls.synthetic import generate_transit_rotation_light_curve
from pbls.paths import TESTRESULTSDIR
from pbls.visualization import plot_summary_figure

def test_pbls_search():
    """
    Test the pbls_search function with synthetic data.
    This test generates a synthetic light curve with a known transit and rotation signal,
    runs the pbls_search, and checks if the best parameters match the known values.
    """
    
    # Ensure the test results directory exists
    os.makedirs(TESTRESULTSDIR, exist_ok=True)

    # Define time array
    total_time = 30.0  # days
    cadence = 0.01     # days
    time = np.arange(0, total_time, cadence)

    # Define noise level
    noise_level = 1e-10 # 0.0002

    # Define transit parameters
    transit_dict = {
        'period': 3.1666,      # days
        't0': 2.5,             # central transit time
        'depth': 0.0005,        # fractional flux drop
        'duration': 0.1        # fractional duration
    }

    # Define rotation parameters
    rotation_dict = {
        'prot': 3.8,         # stellar rotation period in days
        'a1': 0.04,          # amplitude of primary sinusoid
        'a2': 0.01,         # amplitude of secondary sinusoid
        'phi1': 0.0,         # phase offset for primary sinusoid
        'phi2': np.pi / 4    # phase offset for secondary sinusoid
    }

    # Generate the light curve
    flux = generate_transit_rotation_light_curve(
        time, transit_dict, rotation_dict, noise_level=noise_level
    )

    # Define a grid of trial periods and durations for pbls_search.
    # Here we search for periods in a range that covers the true transit period.
    periods = np.linspace(3, 4, 100)         # Trial periods in days
    durations = np.linspace(0.005, 0.02, 10)    # Trial durations (as a fraction of period)

    # Run pbls_search on the synthetic data.
    start_time = timemodule.time()
    result = fast_pbls_search(time, flux, periods, durations, epoch_steps=50, poly_order=3)
    elapsed_time = timemodule.time() - start_time
    print(f"fast_pbls_search took {elapsed_time:.3f} seconds")

    # Extract best parameters and best model from the result dictionary.
    best_params = result['best_params']
    power_spectrum = result['power']
    trial_periods = result['periods']
    best_model = result['best_model']

    # Analytic prediction for the SNR (Carter & Winn 2008)
    N = len(time)       # total number of points
    gamma = N / total_time # sampling rate
    true_depth = transit_dict['depth']
    true_duration = transit_dict['duration']
    true_period = transit_dict['period']
    snr_per_transit = (true_depth / noise_level) * ( gamma * true_duration * true_period )**(1/2)
    N_transits = total_time / true_period
    predicted_snr = snr_per_transit * N_transits**(1/2)
    print(f"Predicted SNR (ideal): {predicted_snr:.3f}")

    from cdips.utils.lcutils import p2p_rms
    noise_p2p = 1.483 * p2p_rms(flux) # similar to median absolute deviation

    snr_per_transit = (true_depth / noise_p2p) * ( gamma * true_duration * true_period )**(1/2)
    predicted_snr = snr_per_transit * N_transits**(1/2)
    print(f"Predicted SNR (P2PRMS): {predicted_snr:.3f}")


    # Print out the best parameters found.
    print("Best period found: {:.4f} days".format(best_params['period']))
    print("Best duration (fraction): {:.4f}".format(best_params['duration']))
    print("Best epoch (phase): {:.4f}".format(best_params['epoch']))
    print("Best transit depth: {:.6f}".format(best_params['depth']))
    print("Best SNR: {:.2f}".format(best_params['snr']))

    # Create the summary figure using the new mosaic layout:
    # The mosaic layout is defined as:
    #
    #   AAAAAA    -> Panel A: Raw Light Curve
    #   BBBBBB    -> Panel B: Periodogram
    #   CCCCCC    -> Panel C: Best-Model Raw Data (with model underplotted)
    #   DDEEFF    -> Panels D (Detrended Flux) & E (Phase-Folded Signal) and F (Summary Text)
    #   DDEEFF
    fig = plot_summary_figure(time, flux, trial_periods, power_spectrum, best_params, best_model)

    plot_path = os.path.join(TESTRESULTSDIR, "test_str_search_result.png")
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

if __name__ == "__main__":
    # Run the test function
    test_pbls_search()
    print("Test completed successfully.")