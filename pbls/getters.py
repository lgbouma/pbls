"""
Contents:
get_mast_lightcurve: Download MAST light curves via Lightkurve for a given star.
get_tess_data: thin wrapper for TESS SPOC 120-second cadence light curves.
    fast_get_mast_lightcurve: As above, but using a hard-coded cache.
"""
import os
from glob import glob
from astropy.io import fits
import lightkurve as lk
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

def get_OSG_local_lightcurve(star_id):

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
        starid,
        mission='TESS',
        cadence=120,
        author='SPOC',
        cache_dir=cache_dir
    )

    
def fast_get_mast_lightcurve(starid, mission='TESS', cadence=120, author='SPOC', cache_dir=None):
    """
    Download MAST light curves via Lightkurve for a given star.

    This works for TESS, Kepler, or K2 by specifying mission, cadence, and author.

    Parameters
    ----------
    starid : str
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

    assert isinstance(cache_dir, str)
    # Ensure cache directory exists if provided
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    # Check if TESS data were already downloaded.
    lcfiles = []
    if mission == 'TESS' and author == 'SPOC' and cadence == 120:
        ticid = NAME_TO_TICID.get(starid, None)
        if ticid is None:
            pass
        else:
            lcfiles = np.sort(glob(join(cache_dir, 'mastDownload', 'TESS', f'tess*{ticid}*', f'tess*{ticid}*.fits')))

    elif mission == 'Kepler' and author == 'Kepler' and cadence == 1800:
        kicid = NAME_TO_KICID.get(starid, None)
        if kicid is None:
            pass
        else:
            lcfiles = np.sort(glob(join(cache_dir, 'mastDownload', 'Kepler', f'kplr*{kicid}*', f'kplr*{kicid}*.fits')))

        
    if len(lcfiles) == 0:
        search_result = lk.search_lightcurve(
            starid,
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

def get_mast_lightcurve(starid, mission='TESS', cadence=120, author='SPOC', cache_dir=None):
    """
    Download MAST light curves via Lightkurve for a given star.

    This works for TESS, Kepler, or K2 by specifying mission, cadence, and author.

    Parameters
    ----------
    starid : str
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

    assert isinstance(cache_dir, str)
    # Ensure cache directory exists if provided
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    # Search for data with specified mission, cadence, and author
    search_result = lk.search_lightcurve(
        starid,
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