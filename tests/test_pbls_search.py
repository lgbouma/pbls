import os
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import time as timemodule

from pbls.pbls import pbls_search
from pbls.mp_pbls import fast_pbls_search
from pbls.period_grids import generate_uniformfreq_period_grid
from pbls.synthetic import generate_transit_rotation_light_curve
from pbls.paths import TESTRESULTSDIR
from pbls.visualization import plot_summary_figure

from test_periodogram_processing import test_periodogram_processing

def test_pbls_search():
    """
    Test the pbls_search function with synthetic data.
    This test generates a synthetic light curve with a known transit and rotation signal,
    runs the pbls_search, and checks if the best parameters match the known values.
    """
    
    # Ensure the test results directory exists
    os.makedirs(TESTRESULTSDIR, exist_ok=True)
    subdirs = ['png', 'csv', 'mp4']
    for subdir in subdirs:
        os.makedirs(os.path.join(TESTRESULTSDIR, subdir), exist_ok=True)

    # Define time array
    total_time = 30.0  # days
    cadence = 0.01     # days
    time = np.arange(0, total_time, cadence)

    # Define noise level
    noise_level = 2e-4

    # Define transit parameters
    transit_dict = {
        'period': 3.1666,      # days
        't0': 2.5,             # central transit time
        'depth': 0.001,        # fractional flux drop
        'duration_hr': 3.        # fractional duration
    }

    Prots = [3.5, 3.3, 2.5, 1.4, 0.85, 0.7]
    poly_order = 3

    for Prot in Prots:

        # Define rotation parameters
        rotation_dict = {
            'prot': Prot,         # stellar rotation period in days
            'a1': 0.04,          # amplitude of primary sinusoid
            'a2': 0.01,         # amplitude of secondary sinusoid
            'phi1': 0.0,         # phase offset for primary sinusoid
            'phi2': np.pi / 4    # phase offset for secondary sinusoid
        }

        # Generate the light curve
        flux = generate_transit_rotation_light_curve(
            time, transit_dict, rotation_dict, noise_level=noise_level
        )

        # Define periods via a linear frequency grid
        # wh3 (non-optimized at 5eec251): 10k periods -> 106 sec.  3k periods -> 46 sec.
        # periods = np.linspace(2, 10, 3000)         # Trial periods in days
        # durations_hr = np.array([1,2,3,4]) # trial durations in units of hours
        periods = generate_uniformfreq_period_grid(
            total_time, cadence, oversample=1, period_min=2.0, period_max=50.0
        )
        durations_hr = np.array([1,2,3,4])  # trial durations in units of hours

        # Run pbls_search on the synthetic data.
        start_time = timemodule.time()
        result = fast_pbls_search(time, flux, periods, durations_hr, epoch_steps=50, poly_order=poly_order)
        #result = pbls_search(time, flux, periods, durations_hr, epoch_steps=50, poly_order=3)
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
        true_period = transit_dict['period']
        true_duration = (transit_dict['duration_hr'] / 24) / true_period
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
        print("Best duration (hours): {:.4f}".format(best_params['duration_hr']))
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

        Porb = transit_dict['period']
        Prot = rotation_dict['prot']

        plot_path = os.path.join(
            TESTRESULTSDIR, 'png',
            f"test_pbls_search_result_Porb{Porb:.3f}_Prot{Prot:.3f}_po{poly_order:d}.png"
        )
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        csv_path = os.path.join(
            TESTRESULTSDIR, 'csv',
            f"pbls_search_periodogram_Porb{Porb:.3f}_Prot{Prot:.3f}_po{poly_order:d}.csv"
        )
        df = pd.DataFrame({
            'period':trial_periods,
            'power':power_spectrum,
        })
        df.to_csv(csv_path, index=False)
        print(f'Wrote {csv_path}')

        csv_path = os.path.join(
            TESTRESULTSDIR, 'csv',
            f"pbls_search_lightcurve_Porb{Porb:.3f}_Prot{Prot:.3f}_po{poly_order:d}.csv"
        )
        df = pd.DataFrame({
            'time':time,
            'flux':flux,
        })
        df.to_csv(csv_path, index=False)
        print(f'Wrote {csv_path}')

        test_periodogram_processing(Porb=Porb, Prot=Prot, method='trimmean', poly_order=poly_order)
        print(42*'-')


if __name__ == "__main__":
    # Run the test function
    test_pbls_search()
    print("Test completed successfully.")