import numpy as np
from astropy.timeseries import LombScargle

def get_LS_Prot(time, flux, Prot_min=0.1, Prot_max=15., N_freq = 1_000_000):
    """measure rotation period (via Lomb Scargle peak) from the light curve"""
    ls = LombScargle(time, flux)
    
    minimum_frequency = 1.0 / Prot_max
    maximum_frequency = 1.0 / Prot_min
    
    frequency = np.linspace(minimum_frequency, maximum_frequency, N_freq)
    power_ls = ls.power(frequency)
    best_freq = frequency[np.argmax(power_ls)]
    LS_Prot = 1.0 / best_freq
    print(f"Measured LS period: {LS_Prot:.4f} days")

    return LS_Prot

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