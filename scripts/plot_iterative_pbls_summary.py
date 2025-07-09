import os, pickle
from os.path import join
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from pbls.visualization import plot_summary_figure
from pbls.paths import RESULTSDIR

#star_id = 'kplr006184894' # kepler-1627
#star_id = 'kplr008653134' # kepler-1643
star_id = 'kplr010736489' # kepler-1974 = koi 7368

max_iter = 3

pgdir = join(RESULTSDIR, 'merged_periodograms')
lcdir = join(RESULTSDIR, 'masked_lightcurves')
outdir = join(RESULTSDIR, 'iterative_pbls_summaries')

for iter_ix in range(max_iter):

    pklpath = join(pgdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.pkl')
    lcpath = join(lcdir, f'{star_id}_masked_lightcurve_iter{iter_ix}.csv')

    if not os.path.exists(pklpath) or not os.path.exists(lcpath):
        print(f"Skipping iteration {iter_ix} for {star_id}: no periodogram / masked lc file found.")
        continue

    with open(pklpath, 'rb') as f:
        d = pickle.load(f)
        
    df = pd.read_csv(lcpath)

    # Extract best parameters and best model from the result dictionary.
    best_params = d['best_params']
    power_spectrum = np.array(d['power'])
    trial_periods = np.array(d['periods'])
    best_model = d['best_model']
    for k,v in best_model.items():
        best_model[k] = np.array(v)

    # time and flux before masking
    time = np.array(df['time'].values)
    flux = np.array(df['flux_original'].values)

    plt.close("all")

    fig = plot_summary_figure(time, flux, trial_periods, power_spectrum, best_params, best_model)

    plot_path = os.path.join(
        outdir, 
        f"{star_id}_pbls_search_result_iter{iter_ix}.png"
    )
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    print(f"Saved summary figure to {plot_path}")

    # Print out the best parameters found.
    print("Best period found: {:.4f} days".format(best_params['period']))
    print("Best duration (hours): {:.4f}".format(best_params['duration_hr']))
    print("Best epoch (days): {:.4f}".format(best_params['epoch_days']))
    print("Best transit depth: {:.2f} ppt".format(best_params['depth']*1e3))
    print("Best SNR: {:.2f}".format(best_params['snr']))
    print(42*'-')