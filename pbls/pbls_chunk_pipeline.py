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
import os, pickle
from os.path import join
import time as timemodule
import numpy as np

from pbls.paths import CACHEDIR
from pbls.getters import get_OSG_local_lightcurve
from pbls.lc_processing import preprocess_lightcurve
from pbls.period_grids import generate_uniformfreq_period_grid
from pbls.pbls import pbls_search
from pbls.mp_pbls import fast_pbls_search

def run_pbls_chunk(star_id, period_grid_chunk_ix, N_total_chunks):

    poly_order = 3
    durations_hr = np.array([1, 2, 3, 4, 6])
    period_min = 2.0
    clamp_period_max = 50.0
    oversample = 1

    LOGINFO(42*'-')
    LOGINFO(f"Starting {star_id}...")

    if 'kplr' in star_id:
        mission = 'Kepler'
    elif 'tess' in star_id:
        mission = 'TESS'
    elif '_k2_' in star_id:
        mission = 'K2'

    # Get light curve data for this target and preprocess it.
    datas, hdrs = get_OSG_local_lightcurve(star_id)
    N_lcfiles = len(datas)
    LOGINFO(f"{star_id}: {N_lcfiles} light curves found.")
    time, flux = preprocess_lightcurve(datas, hdrs, mission)

    # Generate period grid and chunk it.
    total_time = np.nanmax(time) - np.nanmin(time)
    cadence = np.median(np.diff(time))
    periods = generate_uniformfreq_period_grid(
        total_time, cadence, oversample=oversample,
        period_min=period_min, clamp_period_max=clamp_period_max
    )
    N_periods = len(periods)
    periods_per_chunk = int(np.ceil(N_periods/N_total_chunks))
    this_slice = slice(period_grid_chunk_ix*periods_per_chunk,
                       (period_grid_chunk_ix+1)*periods_per_chunk)
    this_chunk_periods = periods[this_slice]

    LOGINFO(f"  Data points: {len(time)}")
    LOGINFO(f"  Total trial periods: {len(periods)}")
    LOGINFO(f"  This chunk trial periods: {len(this_chunk_periods)}")
    LOGINFO(f"  Time span: {total_time:.2f} days")
    LOGINFO(f"  Cadence: {cadence*24*60:.1f} minutes")
    
    # Run PBLS and cache result to a pickle file.
    # Don't use fast_pbls_search because on OSG we're using single cores per job.
    LOGINFO('Starting PBLS search...')
    start_time = timemodule.time()
    #result = fast_pbls_search(time, flux, this_chunk_periods, durations_hr, poly_order=poly_order)
    result = pbls_search(time, flux, this_chunk_periods, durations_hr, poly_order=poly_order)
    elapsed_time = timemodule.time() - start_time
    LOGINFO(f"  PBLS search took {elapsed_time:.3f} seconds")

    pkl_path = join(CACHEDIR, f"{star_id}_{period_grid_chunk_ix}_{N_total_chunks}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(result, f)
    LOGINFO(f"Cached PBLS result at {pkl_path}")