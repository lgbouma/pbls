import os
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import time as timemodule
from pathlib import Path
import glob
from astropy.io import fits

# PBLS imports
from pbls.mp_pbls import fast_pbls_search
from pbls.pbls import pbls_search
from pbls.period_grids import generate_uniformfreq_period_grid
from pbls.paths import TESTRESULTSDIR
from pbls.visualization import plot_summary_figure
from pbls.getters import get_mast_lightcurve
from pbls.lc_processing import get_LS_Prot
from test_periodogram_processing import test_periodogram_processing

# External dependencies
import lightkurve as lk
from astrobase.lcmath import time_bin_magseries

PORB_DICT = {
    'HIP 67522 b': 6.9594731, # Barber+24
    'TOI-837 b': 8.3248762, # Bouma+20
    'AU Mic b': 8.4632, # Plavchan+20
    'TOI-942 b': 4.32419, # Zhou+20
    'V1298 Tau b': 24.1396, # David+19
    'V1298 Tau c': 12.4032, # David+19
    'K2-33 b': 5.424865, # Mann+16
    'Kepler-1627 b': 7.2028038, # Bouma+22a
    'Kepler-1643 b': 5.342657, # Bouma+22b
    'Kepler-1974 b': 6.8430341, # Bouma+22b, KOI-7368
    'Kepler-1975 b': 24.278571, # Bouma+22b, KOI-7913A
}


def setup_cache_directory():
    """Create cache directory for light curve data."""
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def run_pbls_analysis(time, flux, target_name, mission, sector=None, orbital_period=None):
    """
    Run PBLS analysis on a light curve.
    
    Parameters
    ----------
    time : array
        Time array in days
    flux : array
        Normalized flux array
    target_name : str
        Name of the target
    mission : str
        Mission name (TESS, K2, Kepler)
    sector : str, optional
        Sector identifier for TESS data
    orbital_period : float, optional
        Known orbital period for comparison
        
    Returns
    -------
    dict
        Results from PBLS analysis
    """
    # Ensure the test results directory exists
    os.makedirs(TESTRESULTSDIR, exist_ok=True)
    subdirs = ['png', 'csv', 'mp4']
    for subdir in subdirs:
        os.makedirs(os.path.join(TESTRESULTSDIR, subdir), exist_ok=True)
    
    if len(time) < 100:
        print(f"Insufficient data points ({len(time)}) for {target_name}")
        return None
    
    # Generate period grid
    total_time = np.nanmax(time) - np.nanmin(time)
    cadence = np.median(np.diff(time))
    
    periods = generate_uniformfreq_period_grid(
        total_time, cadence, oversample=1, period_min=2.0, clamp_period_max=50.0
    )
    durations_hr = np.array([1, 2, 3, 4, 6])
    
    print(f"Running PBLS analysis for {target_name} ({mission})")
    if sector:
        print(f"  Sector: {sector}")
    print(f"  Data points: {len(time)}")
    print(f"  Time span: {total_time:.2f} days")
    print(f"  Cadence: {cadence*24*60:.1f} minutes")
    if orbital_period:
        print(f"  Known orbital period: {orbital_period:.4f} days")
    
    # Run fast_pbls_search
    start_time = timemodule.time()
    epoch_steps = 50
    poly_order = 3
    result = fast_pbls_search(time, flux, periods, durations_hr, epoch_steps=epoch_steps, poly_order=poly_order)
    elapsed_time = timemodule.time() - start_time
    print(f"  PBLS search took {elapsed_time:.3f} seconds")
    
    # Extract results
    best_params = result['best_params']
    power_spectrum = result['power']
    trial_periods = result['periods']
    best_model = result['best_model']
    
    print(f"  Best period found: {best_params['period']:.4f} days")
    print(f"  Best duration (hours): {best_params['duration_hr']:.4f}")
    print(f"  Best SNR: {best_params['snr']:.2f}")
    
    if orbital_period:
        period_ratio = best_params['period'] / orbital_period
        print(f"  Period ratio (found/known): {period_ratio:.4f}")
    
    # Create summary figure
    fig = plot_summary_figure(time, flux, trial_periods, power_spectrum, best_params, best_model)
    
    # Save plot
    sector_str = f"_{str(sector).zfill(4)}" if sector else ""
    plot_path = os.path.join(
        TESTRESULTSDIR, 'png',
        f"true_positives_{mission}_{target_name.replace(' ', '_')}{sector_str}.png"
    )
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved plot: {plot_path}")
    
    # Save periodogram data
    csv_path = os.path.join(
        TESTRESULTSDIR, 'csv',
        f"true_positives_periodogram_{mission}_{target_name.replace(' ', '_')}{sector_str}.csv"
    )
    df = pd.DataFrame({
        'period': trial_periods,
        'power': power_spectrum,
    })
    df.to_csv(csv_path, index=False)
    print(f"  Saved periodogram: {csv_path}")
    
    # Save light curve data
    csv_path = os.path.join(
        TESTRESULTSDIR, 'csv',
        f"true_positives_lightcurve_{mission}_{target_name.replace(' ', '_')}{sector_str}.csv"
    )
    df = pd.DataFrame({
        'time': time,
        'flux': flux,
    })
    df.to_csv(csv_path, index=False)
    print(f"  Saved light curve: {csv_path}")
    
    ##########################################
    # Run periodogram processing (trimmean whitening)
    # time, flux, trial_periods, power_spectrum
    LS_Prot = get_LS_Prot(time, flux)
    from pbls.periodogram_processing import trimmean_whitening

    x_start = trial_periods.copy()
    y_start = power_spectrum.copy()
    pg_results = trimmean_whitening(trial_periods, power_spectrum, Prot=LS_Prot)

    # read the whitened periodogram results; recalculate best-fit model params
    max_key = max(np.array(list(pg_results.keys())))
    peak_period = pg_results[max_key]['peak_period']
    res = pbls_search(time, flux, np.array([peak_period]), durations_hr, epoch_steps, poly_order)

    # Extract period-level max SNR and corresponding best model params
    power0 = res['power'][0]
    bp = res['best_params']
    bm = res['best_model']

    # Plot summary figure (based on the peak found after gaussian peak whitening)
    post_power = pg_results[max_key]['residual']
    known_params = {'period': orbital_period}
    fig = plot_summary_figure(time, flux, x_start, y_start, bp, bm, post_power=post_power, known_params=known_params)

    plot_path = os.path.join(
        TESTRESULTSDIR, 'png',
        f"true_positives_pgcleaned_{mission}_{target_name.replace(' ', '_')}{sector_str}.png"
    )
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    return result


def test_true_positives():
    """Main test function that processes each target star sequentially:
    1) Download light curve
    2) Retrieve known orbital period
    3) Run PBLS analysis"""

    cache_dir = setup_cache_directory()

    print("Starting True Positives Test")
    print("=" * 50)
    
    # Define target systems by mission
    targets = {
        'TESS': ['TOI-942', 'TOI-837', 'HIP 67522', 'AU Mic', 'Kepler-1627'],
        'K2': ['V1298 Tau', 'K2-33'],
        #'Kepler': ['Kepler-1643', 'Kepler-1974', 'Kepler-1975']
    }

    mission_dtype = {
        'TESS': ['SPOC', 120],
        'K2': ['EVEREST', 1800],
        'Kepler': ['Kepler', 1800],
    }

    # Flatten to a list of tuples
    target_list = [(k,v) for k, v in targets.items()]
   
    for mission, target_name in target_list:

        author = mission_dtype[mission][0]
        cadence = mission_dtype[mission][1]

        print(f"\nProcessing {target_name} ({mission})")
        print("-" * 40)

        # Step 1: Download light curve for this target
        datas, hdrs = get_mast_lightcurve(starid, mission=mission, cadence=cadence, author=author, cache_dir=cache_dir)

        if len(datas) == 0:
            print(f"No data for {target_name} ({mission}), skipping")
            continue

        # Step 2: Get known orbital period(s)
        pl_names = [k for k in PORB_DICT.keys() if target_name in k]
        orbital_periods = [PORB_DICT[k] for k in pl_names]

        # Step 3: Run analysis (sectors / k2 quarters separate)
        for data, hdr in zip(datas, hdrs):

            time = data['TIME']
            if mission in ['TESS', 'Kepler']:
                flux = data['PDCSAP_FLUX']
                qual = data['QUALITY']
            elif mission == 'K2':
                flux = data['FCOR'] # EVEREST corrected flux
                qual = np.zeros_like(time) # K2 data doesn't have QUALITY column

            # drop non-zero quality flags
            sel = (qual == 0)
            time = time[sel]
            flux = flux[sel]

            sel = np.isfinite(time) & np.isfinite(flux)
            time = time[sel]
            flux = flux[sel]

            # run TESS analysis at 10-minute binning
            if mission == 'TESS':
                bd = time_bin_magseries( time, flux, bin_size=10/24/60 )
                btimes, bfluxs = bd['binnedtimes'], bd['binnedfluxes']
                time, flux = 1.*btimes, 1.*bfluxs

            flux /= np.nanmedian(flux)

            result = run_pbls_analysis(time, flux, target_name, mission,
                                        sector=sector_key,
                                        orbital_period=orbital_period)
            #FIXME CACHE RESULTS???

    # Print summary
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    
    for mission, targets in results.items():
        print(f"\n{mission}:")
        for target_name, target_results in targets.items():
            if mission == 'TESS' and isinstance(target_results, dict):
                print(f"  {target_name}: {len(target_results)} sectors analyzed")
                for sector, result in target_results.items():
                    bp = result['best_params']
                    print(f"    {sector}: P={bp['period']:.4f}d, SNR={bp['snr']:.2f}")
            else:
                if target_results is not None:
                    bp = target_results['best_params']
                    print(f"  {target_name}: P={bp['period']:.4f}d, SNR={bp['snr']:.2f}")
                else:
                    print(f"  {target_name}: Analysis failed")
    
    print("\nTrue positives test completed successfully!")
    return results


if __name__ == "__main__":
    # Run the test function
    test_true_positives()