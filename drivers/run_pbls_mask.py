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
import os
import sys
from pbls.lc_processing import mask_top_pbls_peak

def main():

    star_id = sys.argv[1]
    iter_ix = int(sys.argv[2])
    snr_threshold = float(sys.argv[3])
    default_maxiter = 3
    maxiter = int(sys.argv[4]) if len(sys.argv) > 4 else default_maxiter

    LOGINFO(42*'-')
    LOGINFO('Starting run_pbls_mask.py with')
    LOGINFO(f'star_id = {star_id} (type={type(star_id)})')
    LOGINFO(f'iter_ix = {iter_ix} (type={type(iter_ix)})')
    LOGINFO(f'snr_threshold = {snr_threshold} (type={type(snr_threshold)})')
    LOGINFO(f'maxiter = {maxiter} (type={type(maxiter)})')

    LOGINFO(f'{os.listdir("./")}')

    # Create the masked light curve for the periodogram's best peak, save it to
    # a CSV file, and return the max SNR.
    max_snr = mask_top_pbls_peak(
        star_id, iter_ix=iter_ix, snr_threshold=snr_threshold, maxiter=maxiter
    )

    continue_condition = (max_snr > snr_threshold) and (iter_ix < maxiter)

    LOGINFO(f'Max SNR for star {star_id} at iteration {iter_ix}: {max_snr:.2f}')
    LOGINFO(42*'-')

    if continue_condition:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()