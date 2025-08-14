#############
## LOGGING ##
#############
import logging
from pbls import log_sub, log_fmt, log_date_fmt

DEBUG = False
if DEBUG:
    level = logging.DEBUG
else:
    level = logging.INFO
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=level,
    style=log_sub,
    format=log_fmt,
    datefmt=log_date_fmt,
    force=True
)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception

#############
## IMPORTS ##
#############
import os, sys, socket, pickle
from os.path import join
import numpy as np, pandas as pd

from pbls.getters import (
    get_OSG_local_fits_lightcurve, get_OSG_local_csv_lightcurve, parse_star_id
)
from pbls.lc_processing import preprocess_lightcurve, get_LS_Prot
from pbls.periodogram_processing import iterative_gaussian_whitening, trimmean_whitening
from pbls.pbls import pbls_search
from pbls.visualization import plot_summary_figure

def main():

    star_id = sys.argv[1]
    iter_ix = int(sys.argv[2])

    # HARD-CODED PARAMETERS (for now)
    method = 'trimmean'  # or 'itergaussian'
    poly_order = 3
    durations_hr = np.array([1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6])

    LOGINFO(42*'-')
    LOGINFO('Starting run_periodogram_processing.py with')
    LOGINFO(f'star_id = {star_id} (type={type(star_id)})')
    LOGINFO(f'iter_ix = {iter_ix} (type={type(iter_ix)})')

    LOGINFO(f'{os.listdir("./")}')

    hostname = socket.gethostname()

    mission, inject_dict, base_star_id = parse_star_id(star_id)

    ##########################################
       
    # Get periodogram information
    pg_csv_path = f"./{star_id}_merged_pbls_periodogram_iter{iter_ix}.csv"
    df = pd.read_csv(pg_csv_path)
    x, y = df['period'].values, df['power'].values
    x_start, y_start = x.copy(), y.copy()

    # Load time and flux
    ########################################################################
    # vvv BEGIN EXACT DUPLICATE of code from pbls/pbls_chunk_pipeline.py vvv
    # [Otherwise masks + PBLS iterations wouldn't apply to exact same LCs.]
    if iter_ix == 0:
        if hostname in ['wh1', 'wh2', 'wh3', 'marduk.local']:
            raise NotImplementedError
        else:
            datas, hdrs = get_OSG_local_fits_lightcurve(base_star_id)
            N_lcfiles = len(datas)
            LOGINFO(f"{star_id}: {N_lcfiles} light curves found.")
            time, flux = preprocess_lightcurve(datas, hdrs, mission, inject_dict=inject_dict)
    else:
        # Load the masked light curve made by mask.sub last iteration.
        time, flux = get_OSG_local_csv_lightcurve(star_id, iter_ix=iter_ix-1)
    # ^^^ END EXACT DUPLICATE ^^^
    ########################################################################

    sel = np.isfinite(time) & np.isfinite(flux)
    ftime, fflux = time[sel], flux[sel]
    LS_Prot = get_LS_Prot(ftime, fflux)

    if method == 'itergaussian':
        pg_results = iterative_gaussian_whitening(x, y)
    elif method == 'trimmean':
        pg_results = trimmean_whitening(x, y, Prot=LS_Prot)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'itergaussian' or 'trimmean'.")

    # Read the whitened periodogram results; recalculate best-fit model params
    max_key = max(np.array(list(pg_results.keys())))
    peak_period = pg_results[max_key]['peak_period']
    res = pbls_search(ftime, fflux, np.array([peak_period]), durations_hr, poly_order)

    # Extract period-level max SNR and corresponding best model params
    power0 = res['power'][0]
    bp = res['best_params']
    bm = res['best_model']

    # Post-processed PBLS power
    post_power = pg_results[max_key]['residual']

    # Cache post-processed periodogram results to pickle and CSV files.
    assert len(x) == len(post_power), "Length of periods and post_power must match."

    # Define directories for reading merged periodograms
    if hostname in ['wh1', 'wh2', 'wh3']:
        outprocessingdir = f'/ar0/PROCESSING/merged_periodograms/viz'
        if not os.path.exists(outprocessingdir): os.makedirs(outprocessingdir)
    elif 'osg' in hostname:
        # Pre-tarred light curves are passed via HTCondor mask.sub to CWD.
        outprocessingdir = "./"
    else:
        raise NotImplementedError

    result = {
        'best_params': bp,
        'power': post_power,
        'periods': x,
        'best_model': bm,
    }

    outpickle = join(outprocessingdir, f'{star_id}_merged_postprocessed_pbls_periodogram_iter{iter_ix}.pkl')
    with open(outpickle, 'wb') as f:
        pickle.dump(result, f)
    LOGINFO(f"Wrote merged post-processed periodogram to {outpickle}")

    lines = ['period,power\n'] + [f"{period},{power}\n" for period, power in zip(x, post_power)]
    outcsv = join(outprocessingdir, f'{star_id}_merged_postprocessed_pbls_periodogram_iter{iter_ix}.csv')
    with open(outcsv, 'w') as f:
        f.writelines(lines)
    LOGINFO(f"Wrote merged post-processed periodogram to {outcsv}")
    LOGINFO(bp)

    # Make summary figure plot (based on the peak found after whitening)
    fig = plot_summary_figure(time, flux, x_start, y_start, bp, bm, post_power=post_power)

    plot_path = join(
        outprocessingdir, f"{star_id}_pbls_pgproc{method}_iter{iter_ix}.png"
    )
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    LOGINFO(f"Saved summary figure to {plot_path}")


if __name__ == "__main__":
    main()