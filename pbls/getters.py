"""
Contents:

Light curve getters:
    get_mast_lightcurve: Download MAST light curves via Lightkurve for a given star.
    get_tess_data: thin wrapper for TESS SPOC 120-second cadence light curves.
        fast_get_mast_lightcurve: As above, but using a hard-coded cache.
    get_OSG_local_fits_lightcurve: Get LCs from local FITS (on OSG).
    get_OSG_local_csv_lightcurve: Get (masked) LC from local CSV (on OSG).

Star ID parsers:
    parse_star_id: Get mission & (optional) injection parameters from star_id.
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
import os
from glob import glob
from astropy.io import fits
from os.path import join
import numpy as np

from pbls.pipeline_utils import extract_tarball

# hard cache for common cases
NAME_TO_TICID = {
    'HIP 67522': '166527623',
    'TOI-837': '460205581',
    'AU Mic': '441420236',
    'TOI-942': '146520535',
    'Kepler-1627': '120105470',
}
NAME_TO_KICID = {
    'Kepler-1627': '6184894',
    'Kepler-1643': '8653134',
    'Kepler-1974': '10736489',
    'Kepler-1975': '8873450',
}

def get_OSG_local_fits_lightcurve(star_id):

    # Pre-tarred light curves are passed as tarball via HTCondor.
    tarballpath = f"./{star_id}.tar.gz"
    extractpath = "./"
    extract_tarball(tarballpath, extractpath)

    # Read data and headers
    lcfiles = np.sort(glob(f"{star_id}*.fits"))
    data = []
    hdrs = []
    for f in lcfiles:
        hdul = fits.open(f)
        data.append(hdul[1].data)
        hdrs.append(hdul[0].header)

    return data, hdrs

    
def get_OSG_local_csv_lightcurve(star_id, iter_ix=0):
    """
    Get the masked light curve produced *during* a given iteration of PBLS.
    So, if you're on the second PBLS iteration (which we index as iter_ix=1),
    you should pass iter_ix=0.
    """

    # CSV light curves are passed via HTCondor through the DAGman.
    csvpath = f"./{star_id}_masked_lightcurve_iter{iter_ix}.csv"

    import pandas as pd

    df = pd.read_csv(csvpath)
    time = np.array(df['time_masked'])
    flux = np.array(df['flux_masked'])

    return time, flux


def get_tess_data(star_id, cache_dir=None):
    """
    Download TESS SPOC 120-second cadence light curves for a given star.

    Parameters
    ----------
    star_id : str
        SIMBAD-resolvable target identifier.
    cache_dir : str, optional
        Directory to cache downloaded FITS files. If None, default download_dir is used.

    Returns
    -------
    data : list
        List of FITS table data arrays (hdul[1].data).
    hdrs : list
        List of FITS primary headers (hdul[0].header).
    """
    return get_mast_lightcurve(
        star_id,
        mission='TESS',
        cadence=120,
        author='SPOC',
        cache_dir=cache_dir
    )

    
def fast_get_mast_lightcurve(star_id, mission='TESS', cadence=120, author='SPOC', cache_dir=None):
    """
    Download MAST light curves via Lightkurve for a given star.

    This works for TESS, Kepler, or K2 by specifying mission, cadence, and author.

    Parameters
    ----------
    star_id : str
        SIMBAD-resolvable target identifier.
    mission : str, optional
        Observatory mission name (e.g., 'TESS', 'Kepler', 'K2'). Default is 'TESS'.
    cadence : int, optional
        Observing cadence in seconds (e.g., 120 for TESS short cadence, 1800 for K2). Default is 120.
    author : str, optional
        Pipeline or author tag (e.g., 'SPOC', 'EVEREST', 'Kepler'). Default is 'SPOC'.
    cache_dir : str, optional
        Directory to cache downloaded FITS files. If None, default lightkurve cache is used.

    Returns
    -------
    data : list
        List of FITS table data arrays (hdul[1].data).
    hdrs : list
        List of FITS primary headers (hdul[0].header).
    """

    import lightkurve as lk

    assert isinstance(cache_dir, str)
    # Ensure cache directory exists if provided
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    # Check if TESS data were already downloaded.
    lcfiles = []
    if mission == 'TESS' and author == 'SPOC' and cadence == 120:
        ticid = NAME_TO_TICID.get(star_id, None)
        if ticid is None:
            pass
        else:
            lcfiles = np.sort(glob(join(cache_dir, 'mastDownload', 'TESS', f'tess*{ticid}*', f'tess*{ticid}*.fits')))

    elif mission == 'Kepler' and author == 'Kepler' and cadence == 1800:
        kicid = NAME_TO_KICID.get(star_id, None)
        if kicid is None:
            pass
        else:
            lcfiles = np.sort(glob(join(cache_dir, 'mastDownload', 'Kepler', f'kplr*{kicid}*', f'kplr*{kicid}*.fits')))

        
    if len(lcfiles) == 0:
        search_result = lk.search_lightcurve(
            star_id,
            mission=mission,
            cadence=cadence,
            author=author
        )

        if len(search_result) == 0:
            return [], []

        # Download all light curves
        lc_collection = search_result.download_all(download_dir=cache_dir)
        lcfiles = np.sort([obj.meta['FILENAME'] for obj in lc_collection])

    # Read data and headers
    data = []
    hdrs = []
    for f in lcfiles:
        hdul = fits.open(f)
        data.append(hdul[1].data)
        hdrs.append(hdul[0].header)

    return data, hdrs

def get_mast_lightcurve(star_id, mission='TESS', cadence=120, author='SPOC', cache_dir=None):
    """
    Download MAST light curves via Lightkurve for a given star.

    This works for TESS, Kepler, or K2 by specifying mission, cadence, and author.

    Parameters
    ----------
    star_id : str
        SIMBAD-resolvable target identifier.
    mission : str, optional
        Observatory mission name (e.g., 'TESS', 'Kepler', 'K2'). Default is 'TESS'.
    cadence : int, optional
        Observing cadence in seconds (e.g., 120 for TESS short cadence, 1800 for K2). Default is 120.
    author : str, optional
        Pipeline or author tag (e.g., 'SPOC', 'EVEREST', 'Kepler'). Default is 'SPOC'.
    cache_dir : str, optional
        Directory to cache downloaded FITS files. If None, default lightkurve cache is used.

    Returns
    -------
    data : list
        List of FITS table data arrays (hdul[1].data).
    hdrs : list
        List of FITS primary headers (hdul[0].header).
    """

    import lightkurve as lk

    assert isinstance(cache_dir, str)
    # Ensure cache directory exists if provided
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    # Search for data with specified mission, cadence, and author
    search_result = lk.search_lightcurve(
        star_id,
        mission=mission,
        cadence=cadence,
        author=author
    )

    if len(search_result) == 0:
        return [], []

    # Download all light curves
    lc_collection = search_result.download_all(download_dir=cache_dir)
    lcfiles = np.sort([obj.meta['FILENAME'] for obj in lc_collection])

    # Read data and headers
    data = []
    hdrs = []
    for f in lcfiles:
        hdul = fits.open(f)
        data.append(hdul[1].data)
        hdrs.append(hdul[0].header)

    return data, hdrs

    
def parse_star_id(star_id):

    # get mission from star_id
    if 'kplr' in star_id or 'Kepler-' in star_id:
        mission = 'Kepler'
    elif 'tess' in star_id or 'TOI-' in star_id:
        mission = 'TESS'
    elif '_k2_' in star_id or 'K2-' in star_id:
        mission = 'K2'

    # create injection dict if needed
    # star_id format in such cases:
    # "kplr12390401_inject-PXpXXX-RYpYYY-TZpZZZ-EXpXXX" for period, radius, duration, epoch.
    inject_dict = None

    base_star_id = star_id

    if '_inject-' in star_id:

        # hard Rstar cache for common cases
        # NOTE: this doesn't scale; if you want to inject on stars other than those
        # specified here, you'll need to estimate those stellar radii some other
        # way.
        TICID_RSTARS = {
            '166527623': 1.38, # HIP 67522
            '460205581': 1.022, # TOI-837
            '441420236': 0.75, # AU Mic
            '146520535': 1.022, # TOI-942
            '120105470': 0.881, # Kepler-1627
        }
        KICID_RSTARS = {
            '6184894': 0.881, # Kepler-1627
            '8653134': 0.855,    # 'Kepler-1643': 
            '10736489': 0.876,   # 'Kepler-1974' = KOI-7368
            '8873450': 0.790,    # 'Kepler-1975' = KOI-7913A 
        }

        base_star_id = star_id.split('_inject-')[0]
        if base_star_id.startswith('kplr'):
            # remove "kplr" and any leading zeros
            kicid = base_star_id[4:].lstrip('0')
            Rs_Rsun = KICID_RSTARS[kicid]
            Rs_earths = Rs_Rsun * 109.07637071
        else:
            raise NotImplementedError("Only Kepler injection parsing is implemented. "+
                                      "To do more, add Rstar logic here.")

        inject_str = star_id.split('_inject-')[1]
        inject_parts = inject_str.split('-')
        inject_dict = {}
        for part in inject_parts:
            if part.startswith('P'):
                inject_dict['period'] = float(part[1:].replace('p', '.'))
            elif part.startswith('T'):
                inject_dict['duration_hr'] = float(part[1:].replace('p', '.'))
            elif part.startswith('E'):
                inject_dict['epoch'] = float(part[1:].replace('p', '.'))
            elif part.startswith('R'):
                Rp_earths = float(part[1:].replace('p', '.')) # units: Earth radii
                inject_dict['depth'] = (Rp_earths / Rs_earths) ** 2

        LOGINFO(f"  Injection parameters: {inject_dict}")

    return mission, inject_dict, base_star_id