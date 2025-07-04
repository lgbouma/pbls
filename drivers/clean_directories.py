"""
(OSG-only) Cleans directories for where to route results and logs
NOTE: currently a driver; could be moved to /pbls/ but OSG env install would complicate.

Usage: clean_directories.py <star_id>

e.g. python clean_directories.py "kplr006184894" # Kepler-1627
(or 'kplr008653134' # Kepler-1643)
"""

import os
import sys
from datetime import datetime
from os.path import join

def clean_result_and_log_directories(star_id, maxiter=3):
    """
    "Pre" script to clean up directories for iterative PBLs runs.

    Relevant locations are:
    * Directories for all log files
    * Previous periodogram and masked light curve files for the same star.
    * Intermediate periodogram pkl chunk files.

    The cleaning approach is to rename using a timestamp and random hex suffix.
    """

    res_basedir = '/ospool/ap21/data/ekul/pbls_results'
    results_dir = join(res_basedir, star_id)

    log_basedir = '/home/ekul/proj/pbls/drivers/logs'
    logs_dir = join(log_basedir, star_id)
    iter_dirs = [join(log_basedir, star_id, f'iter{ix}') for ix in range(maxiter)]

    proc_basedir = '/ospool/ap21/data/ekul/pbls_results/PROCESSING'
    proc_dir = join(proc_basedir, star_id)

    pgfiles = (
        [join(proc_basedir, 'merged_periodograms', f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.csv') for iter_ix in range(maxiter)]
        +
        [join(proc_basedir, 'merged_periodograms', f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.pkl') for iter_ix in range(maxiter)]
    )
    pgfiles = [pgfile for pgfile in pgfiles if os.path.exists(pgfile)]

    lcfiles =  [join(proc_basedir, 'masked_lightcurves', f'{star_id}_masked_lightcurve_iter{iter_ix}.csv') for iter_ix in range(maxiter)]
    lcfiles = [lcfile for lcfile in lcfiles if os.path.exists(lcfile)]

    allfiles = pgfiles + lcfiles

    dirtypes = ['results', 'logs', 'processing']

    timestamp = datetime.now().strftime('%Y%m%d')
    suffix = os.urandom(4).hex()

    for filepath in allfiles:
        pre = filepath.split(".")[0]
        post = filepath.split(".")[1]
        new_filepath = ".".join([f"{pre}_{timestamp}_{suffix}", post])
        os.rename(filepath, new_filepath)
        print(f"Moved existing file to: {new_filepath}")

    for dirtype, directory in zip(dirtypes, [results_dir, logs_dir, proc_dir]):

        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {dirtype} directory: {directory}")
        else:
            # Directory already exists.  Move it to a new directory with both (a)
            # timestamp based on when it was last modified, and (b) a randomly
            # generated suffix.
            new_dir = f"{directory}_{timestamp}_{suffix}"
            os.rename(directory, new_dir)
            print(f"Moved existing {dirtype} directory to: {new_dir}")
            os.makedirs(directory)
            print(f"Created {dirtype} directory: {directory}")

    for directory in iter_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {dirtype} directory: {directory}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: clean_directories.py <star_id>", file=sys.stderr)
        sys.exit(1)

    clean_result_and_log_directories(sys.argv[1])