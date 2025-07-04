"""
Contents:
get_mast_lightcurve: Download MAST light curves via Lightkurve for a given star.
get_tess_data: thin wrapper for TESS SPOC 120-second cadence light curves.
    fast_get_mast_lightcurve: As above, but using a hard-coded cache.
"""
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