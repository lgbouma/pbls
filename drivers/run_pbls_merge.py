#!/usr/bin/env python3
"""
Usage: `run_pbls_merge.py $(star_id) $(iteration) $(threshold) $(maxiter)`

Merge results from chunked PBLS jobs on the OSG.

To access the OSG filesystem (which isn't accessible from apptainer /
singularity containers), this script is executed by the HTCondor DAG driver in
the *default OSG environment*, where the pickle files are written.  Hence, no
numpy or other non-default libraries.
"""
#############
## LOGGING ##
#############
import logging
log_sub = '{'
log_fmt = '[{levelname:1.1} {asctime} {module}:{lineno}] {message}'
log_date_fmt = '%y%m%d %H:%M:%S'

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
import os, sys, pickle, socket
import tarfile
import math
from glob import glob
from os.path import join

def main():

    star_id = sys.argv[1]
    iter_ix = int(sys.argv[2])
    snr_threshold = float(sys.argv[3])
    default_maxiter = 3
    maxiter = int(sys.argv[4]) if len(sys.argv) > 4 else default_maxiter

    LOGINFO(42*'-')
    LOGINFO('Starting run_pbls_merge_mask.py with')
    LOGINFO(f'star_id = {star_id} (type={type(star_id)})')
    LOGINFO(f'iter_ix = {iter_ix} (type={type(iter_ix)})')
    LOGINFO(f'snr_threshold = {snr_threshold} (type={type(snr_threshold)})')
    LOGINFO(f'maxiter = {maxiter} (type={type(maxiter)})')

    # Take periodogram chunked over periods and make it a single periodogram.
    join_tarball_chunks_to_periodogram(
        star_id, iter_ix=iter_ix
    )

    sys.exit(0)
        
def join_tarball_chunks_to_periodogram(star_id, iter_ix=0):

    hostname = socket.gethostname()

    if hostname in ['wh1', 'wh2', 'wh3']:
        receivingdir = f'/ar0/RECEIVING/{star_id}'
        processingdir = f'/ar0/PROCESSING/{star_id}'
        outprocessingdir = f'/ar0/PROCESSING/merged_periodograms'
    elif 'osg' in hostname:
        receivingdir = f'/ospool/ap21/data/ekul/pbls_results/{star_id}'
        processingdir = f'/ospool/ap21/data/ekul/pbls_results/PROCESSING/{star_id}'
        outprocessingdir = f'/ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms'
    else:
        raise NotImplementedError(
            f"Hostname {hostname} not recognized. "
            "Please implement the logic for this hostname."
        )

    if not os.path.exists(processingdir):
        os.mkdir(processingdir)
    if not os.path.exists(outprocessingdir):
        os.mkdir(outprocessingdir)

    tar_paths = glob(join(receivingdir, f'joboutput_{star_id}*iter{iter_ix}.tar.gz'))
    N_tars = len(tar_paths)
    LOGINFO(f'Found {N_tars} tarballs for {star_id} in {receivingdir}')

    for ix, tar_path in enumerate(tar_paths):
        if N_tars >= 100:
            if ix % int(N_tars/10) == 0:
                LOGINFO(f"{ix}/{N_tars}...")
        extract_tarball(tar_path, processingdir, verbose=0)

    pklpaths = sorted(glob(join(processingdir, 'srv', '*', f'{star_id}*iter{iter_ix}.pkl')))

    powers = []
    periods = []
    coeffs = []
    best_params = None
    best_model = None

    max_power = None

    for pklpath in sorted(pklpaths):
        with open(pklpath, 'rb') as f:
            data = pickle.load(f)

            N = len(data['power'])

            if N == 0:
                LOGINFO(f"Warning: {pklpath} has no data, skipping.")
                continue

            powers.append(data['power'])
            periods.append(data['periods'])

            finite_power_vals = [p for p in data['power'] if not math.isnan(p)]
            this_max_power = max(finite_power_vals) if len(finite_power_vals) > 0 else 0

            if max_power is None or this_max_power > max_power:
                max_power = this_max_power
                best_params = data['best_params']
                best_model = data['best_model']

    periods = [p for sub in periods for p in sub]
    powers = [p for sub in powers for p in sub]

    inds = sorted(range(len(periods)), key=lambda i: periods[i])
    periods = [periods[i] for i in inds]
    powers = [powers[i] for i in inds]

    # Cache the resulting merged periodogram
    result = {
        'best_params': best_params,
        'power': powers,
        'periods': periods,
        'best_model': best_model,
    }

    # Write as CSV avoiding pandas.
    lines = ['period,power\n'] + [f"{period},{power}\n" for period, power in zip(periods, powers)]
    outcsv = join(outprocessingdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.csv')
    with open(outcsv, 'w') as f:
        f.writelines(lines)
    LOGINFO(f"Wrote merged periodogram to {outcsv}")

    outpickle = join(outprocessingdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.pkl')
    with open(outpickle, 'wb') as f:
        pickle.dump(result, f)
    LOGINFO(f"Wrote merged periodogram to {outpickle}")

    LOGINFO(best_params)


def extract_tarball(tarball_name, extract_path, verbose=1):
    """
    Unzip a gzipped tar archive.
    """
    with tarfile.open(tarball_name, "r:gz") as tar:
        tar.extractall(path=extract_path)
        if verbose:
            LOGINFO(f"Extracted {tarball_name} to {extract_path}")


if __name__ == "__main__":
    main()