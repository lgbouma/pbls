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