"""
(OSG-only) Cleans directories for where to route results and logs
NOTE: currently a driver; could be moved to /pbls/ but OSG env install would complicate.
"""

import os
from datetime import datetime

def clean_result_and_log_directories(star_id):
    """
    Cleans directories for where to route results and logs (expected by condor_submit.sub)
    """

    res_basedir = '/ospool/ap21/data/ekul/pbls_results'
    results_dir = os.path.join(res_basedir, star_id)

    log_basedir = '/home/ekul/proj/pbls/drivers/logs'
    logs_dir = os.path.join(log_basedir, star_id)

    dirtypes = ['results', 'logs']

    for dirtype, directory in zip(dirtypes, [results_dir, logs_dir]):

        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {dirtype} directory: {directory}")
        else:
            # Directory already exists.  Move it to a new directory with both (a)
            # timestamp based on when it was last modified, and (b) a randomly
            # generated suffix.
            timestamp = datetime.now().strftime('%Y%m%d')
            suffix = os.urandom(4).hex()
            new_dir = f"{directory}_{timestamp}_{suffix}"
            os.rename(directory, new_dir)
            print(f"Moved existing {dirtype} directory to: {new_dir}")
            os.makedirs(directory)
            print(f"Created {dirtype} directory: {directory}")

if __name__ == "__main__":

    star_id = "kplr006184894" # Kepler-1627
    #star_id = 'kplr008653134' # Kepler-1643

    clean_result_and_log_directories(star_id)