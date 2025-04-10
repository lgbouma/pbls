import os
from os.path import join
import numpy as np, matplotlib.pyplot as plt
from pbls.synthetic import generate_synthetic_light_curve
from pbls.bls import box_least_squares
from pbls.visualization import plot_summary_figure
from pbls.paths import TESTRESULTSDIR

def test_bls_on_synthetic_data():
    # True transit parameters
    starid = "TestStar1234"
    true_period = 2.0      # days
    true_duration = 0.09    # fraction of period (i.e. 10% of the period)
    true_epoch = 0.4       # phase (fraction)
    true_depth = 0.02      # fractional drop (1% drop)
    noise_level = 0.0001    # noise level in flux units
    
    # Observation parameters
    T_total = 40.0         # total observation time in days
    cadence = 0.01         # time between observations in days
    
    # Generate synthetic light curve data
    time, flux = generate_synthetic_light_curve(period=true_period,
                                                duration=true_duration,
                                                epoch=true_epoch,
                                                depth=true_depth,
                                                total_time=T_total,
                                                cadence=cadence,
                                                noise_level=noise_level)
    
    # Run the BLS algorithm over a parameter grid that includes the true values
    best_results = box_least_squares(time, flux,
                                     min_period=1.5, max_period=2.5, period_step=0.01,
                                     min_duration=0.08, max_duration=0.12, duration_step=0.002,
                                     epoch_steps=100)
    
    print("BLS Recovered Results:")
    print(f"  Best Period  : {best_results['best_period']:.3f} days")
    print(f"  Best Duration: {best_results['best_duration']:.3f} (phase fraction)")
    print(f"  Best Epoch   : {best_results['best_epoch']:.3f} (phase fraction)")
    print(f"  Transit Depth: {best_results['best_depth']:.3f}")
    print(f"  Best SNR     : {best_results['best_snr']:.3f}")
    
    # Analytic prediction for the SNR (Carter & Winn 2008)
    N = len(time)       # total number of points
    gamma = N / T_total # sampling rate
    snr_per_transit = (true_depth / noise_level) * ( gamma * true_duration * true_period )**(1/2)
    N_transits = T_total / true_period
    predicted_snr = snr_per_transit * N_transits**(1/2)
    print(f"Predicted SNR (ideal): {predicted_snr:.3f}")

    from cdips.utils.lcutils import p2p_rms
    noise_p2p = 1.483 * p2p_rms(flux) # similar to median absolute deviation

    snr_per_transit = (true_depth / noise_p2p) * ( gamma * true_duration * true_period )**(1/2)
    predicted_snr = snr_per_transit * N_transits**(1/2)
    print(f"Predicted SNR (P2PRMS): {predicted_snr:.3f}")

    # Extract the periodogram data from the BLS output
    periods = best_results['periods']
    power = best_results['power']
    
    # Generate the summary plot that includes:
    #   A: Raw light curve
    #   B: Periodogram (using real periodogram data)
    #   C: Phase-folded light curve
    #   D: Text summary of the best BLS results
    plot_summary_figure(time, flux, periods, power, best_results)
    pngpath = join(TESTRESULTSDIR, f"{starid}_bls.png")
    plt.savefig(pngpath, dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    test_bls_on_synthetic_data()
