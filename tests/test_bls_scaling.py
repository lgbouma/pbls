import os
import pickle
from os.path import join
import numpy as np
import matplotlib.pyplot as plt
from pbls.synthetic import generate_synthetic_light_curve
from pbls.bls import box_least_squares
from pbls.paths import TESTRESULTSDIR, CACHEDIR

def test_bls_scaling():
    # Observation parameters
    T_total = 365.0       # one year of observations in days
    cadence = 0.02        # time between observations in days
    N = int(T_total / cadence)
    gamma = N / T_total   # sampling rate (points per day)
    
    # Transit parameters (free parameters)
    true_duration = 0.1   # fraction of period (i.e. 10% of the period)
    true_epoch = 0.3      # phase (fraction)
    noise_level = 0.001   # noise level in flux units
    # Free parameter: desired SNR per transit
    snr_per_transit_target = 20.0  
    # Compute the transit depth required to achieve the desired SNR per transit
    # snr_per_transit = (depth / noise_level) * sqrt(gamma * true_duration)
    depth = snr_per_transit_target * noise_level / np.sqrt(gamma * true_duration)
    
    # Range of orbital periods (in days) to test. This will change the number of transits.
    period_list = np.linspace(1, 100, num=20)
    
    # Prepare lists to store the number of transits, predicted SNR, and recovered SNR.
    N_transits_list = []
    predicted_snr_list = []
    recovered_snr_list = []
    
    # Loop over the list of orbital periods
    for period in period_list:
        # Analytic prediction for the SNR (Carter & Winn 2008)
        N_transits = T_total / period
        snr_per_transit = snr_per_transit_target  # our design target
        predicted_snr = snr_per_transit * np.sqrt(N_transits)
        
        # Verbose progress output
        print(f"Processing period: {period:.2f} days, "
              f"Number of transits: {N_transits:.2f}, "
              f"Predicted SNR: {predicted_snr:.3f}")
        
        # Cache file name for this period's simulation
        cache_filename = join(CACHEDIR, f"bls_scaling_{period:.2f}.pkl")
        
        if os.path.exists(cache_filename):
            print("  -> Loaded result from cache.")
            with open(cache_filename, 'rb') as f:
                result = pickle.load(f)
        else:
            print("  -> Generating synthetic light curve and running BLS...")
            # Generate synthetic light curve for this period.
            time, flux = generate_synthetic_light_curve(
                period=period,
                duration=true_duration,
                epoch=true_epoch,
                depth=depth,
                total_time=T_total,
                cadence=cadence,
                noise_level=noise_level
            )
            # Run BLS; set a narrow search window around the injected period.
            best_results = box_least_squares(
                time, flux,
                min_period=0.8 * period, max_period=1.2 * period, period_step=0.01,
                min_duration=0.05, max_duration=0.15, duration_step=0.005,
                epoch_steps=50
            )
            result = {
                'time': time,
                'flux': flux,
                'best_results': best_results,
                'injected_period': period
            }
            with open(cache_filename, 'wb') as f:
                pickle.dump(result, f)
        
        # Append results for plotting
        N_transits_list.append(T_total / period)
        predicted_snr_list.append(predicted_snr)
        recovered_snr_list.append(result['best_results']['best_snr'])
    
    # Convert lists to numpy arrays for plotting
    N_transits_arr = np.array(N_transits_list)
    predicted_snr_arr = np.array(predicted_snr_list)
    recovered_snr_arr = np.array(recovered_snr_list)
    
    # Create a plot comparing predicted SNR and recovered SNR vs. number of transits.
    plt.figure(figsize=(8, 6))
    plt.plot(N_transits_arr, predicted_snr_arr, 'k-', label='Predicted SNR')
    plt.plot(N_transits_arr, recovered_snr_arr, 'ro', label='Recovered SNR (BLS)')
    plt.xlabel("Number of Transits")
    plt.ylabel("SNR")
    plt.title("BLS Scaling: Recovered vs Predicted SNR")
    plt.legend()
    plt.grid(True)
    
    # Save the plot
    pngpath = join(TESTRESULTSDIR, "bls_scaling.png")
    plt.savefig(pngpath, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {pngpath}")
    plt.show()

if __name__ == '__main__':
    test_bls_scaling()
