"""
Standard light curve processing functions.

Contents:
* preprocess_lightcurve: Standard cleaning before PBLS.
* get_LS_Prot: Measure rotation period via Lomb-Scargle peak given time and flux.
* time_bin_lightcurve: Bin the light curve in time with a fixed binsize.
* transit_mask: Get transit mask given t, P, Tdur, t0
"""
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
import socket, pickle
import numpy as np
from astropy.timeseries import LombScargle
from wotan import slide_clip

def get_LS_Prot(time, flux, Prot_min=0.1, Prot_max=15., N_freq = 1_000_000, verbose=1):
    """measure rotation period (via Lomb Scargle peak) from the light curve"""
    ls = LombScargle(time, flux)
    
    minimum_frequency = 1.0 / Prot_max
    maximum_frequency = 1.0 / Prot_min
    
    frequency = np.linspace(minimum_frequency, maximum_frequency, N_freq)
    power_ls = ls.power(frequency)
    best_freq = frequency[np.argmax(power_ls)]
    LS_Prot = 1.0 / best_freq
    if verbose:
        LOGINFO(f"Measured LS period: {LS_Prot:.4f} days")

    return LS_Prot

    
def transit_mask(t, P, Tdur, t0):
    """Create a mask for transits given time, period, transit duration, and
    transit (midtime) epoch.  All should be passed in units of days."""
    
    mask = np.abs(  (t - t0 + 0.5*P) % P - 0.5 * P )  < 0.5 * Tdur
    return mask


def time_bin_lightcurve(time, flux, binsize):
    """Bin the light curve in time with a fixed binsize.
    Returns arrays of binned time (bin centers) and mean flux in each bin."""

    t_min, t_max = np.nanmin(time), np.nanmax(time)
    # Define bin edges from t_min to t_max
    edges = np.arange(t_min, t_max + binsize, binsize)
    # Digitize assigns each time to a bin index
    bin_idx = np.digitize(time, edges) - 1

    binned_time = []
    binned_flux = []
    # Iterate over all bins
    for i in range(len(edges) - 1):
        mask = bin_idx == i
        if not np.any(mask):
            continue
        # Compute mean time and flux in the bin
        binned_time.append(np.nanmean(time[mask]))
        binned_flux.append(np.nanmean(flux[mask]))

    return np.array(binned_time), np.array(binned_flux)

def preprocess_lightcurve(datas, hdrs, mission):
    """
    Drop non-zero quality flags; require finite time and flux;
    require positive flux; set dtype to float64; median normalize
    sliding clip [100,2]*MAD over LS_Prot/20 to trim flares;
    re-require finite time and flux.
    The flare window requires at least 10 points per window
    -> K2/Kepler means at least 5 hours window;
    TESS means at least 20 minute window;
    but standard window is 10% of LS_Prot.
    """

    _time, _flux = [], []
    sectors = []

    for data, hdr in zip(datas, hdrs):

        time = data['TIME']

        # NOTE: logic here could be better; could drop `mission` arg and read
        # direct from header.
        if mission == 'TESS':
            flux = data['SAP_FLUX']
            qual = data['QUALITY']
        elif mission == 'K2':
            flux = data['FCOR'] # EVEREST corrected flux
            qual = np.zeros_like(time) # K2 data doesn't have QUALITY column
        elif mission == 'Kepler':
            flux = data['SAP_FLUX']
            qual = data['SAP_QUALITY']
        
        sel = (qual == 0)
        time = time[sel]
        flux = flux[sel]

        sel = np.isfinite(time) & np.isfinite(flux)
        time = time[sel]
        flux = flux[sel]

        sel = (flux > 0)
        time = time[sel]
        flux = flux[sel]

        time = time.astype(np.float64)
        flux = flux.astype(np.float64)
        
        flux /= np.nanmedian(flux)

        LS_Prot = get_LS_Prot(time, flux)
        cadence = np.nanmedian(np.diff(time))
        window_length = np.maximum(LS_Prot/20, cadence * 10)

        clipped_flux = slide_clip(
            time, flux, window_length=window_length,
            low=100, high=2, method='mad', center='median'
        )

        sel = np.isfinite(time) & np.isfinite(clipped_flux)
        time = time[sel]
        flux = 1.* clipped_flux[sel]
        assert len(time) == len(flux)

        # run TESS analysis at 30-minute binning after flare removal
        if mission == 'TESS':
            binsize = 30/24/60
            btimes, bfluxs = time_bin_lightcurve( time, flux, binsize=binsize )
            time, flux = 1.*btimes, 1.*bfluxs

        _time.append(time)
        _flux.append(flux)

    time = np.concatenate(_time)
    flux = np.concatenate(_flux)

    return time, flux