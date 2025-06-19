"""
Contents:
get_mast_lightcurve: Download MAST light curves via Lightkurve for a given star.
get_tess_data: thin wrapper for TESS SPOC 120-second cadence light curves.
"""
import os
import glob
from astropy.io import fits
import lightkurve as lk


def get_tess_data(starid, cache_dir=None):
    """
    Download TESS SPOC 120-second cadence light curves for a given star.

    Parameters
    ----------
    starid : str
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
    # Search for data with specified mission, cadence, and author
    search_result = lk.search_lightcurve(
        starid,
        mission=mission,
        cadence=cadence,
        author=author
    )

    if len(search_result) == 0:
        return [], []

    # Ensure cache directory exists if provided
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    # Download all light curves
    if cache_dir:
        lc_collection = search_result.download_all(download_dir=cache_dir)
        lcfiles = [obj.meta['FILENAME'] for obj in lc_collection]
    else:
        lc_collection = search_result.download_all()
        raise NotImplementedError('get lcfiles')

    # Read data and headers
    data = []
    hdrs = []
    for f in lcfiles:
        hdul = fits.open(f)
        data.append(hdul[1].data)
        hdrs.append(hdul[0].header)

    return data, hdrs