"""
There are a number of options for how to choose the period grid over which to
calculate the periodogram.

generate_uniformfreq_period_grid:
    A uniform grid in frequencies, transformed back to periods.
    (In period space, this implies heavier sampling at shorter periods.)

generate_Ofir2014_period_grid:
    Ofir+2014 argues for a cubic grid in frequency.  This follows from the
    fractional transit duration, q, being written q = R/(GM)^{1/3}*f^{2/3}, and
    a subsequent argument on the duty cycle imposing a limit on the frequency
    peak.   This implementation follows the one in transitleastsquares.

generate_Jenkins2010_period_grid:
    Jenkins+2010 describes a grid in period set by a condition for overlaps
    between proposed transit signals.  Implementing this in a periodogram
    requires durations to be the outermost loop.
"""
import numpy as np

def generate_uniformfreq_period_grid(
    total_time, cadence, oversample=1, period_min=2.0, clamp_period_max=50.0
):
    """
    Generate a period grid by uniform sampling in the frequency domain.

    Args:
        total_time (float): Total observing time span in days.
        cadence (float): Observation cadence in days.
        oversample (int): Frequency oversampling factor (default=1).
        period_min (float): Minimum period to search (default=2.0 days).
        clamp_period_max (float): Maximum period to search before clamping (default=50.0 days).

    Returns:
        numpy.ndarray: Trial periods spanning [period_min, min(total_time/2, period_max)].
    """

    # Clamp maximum period to half the observing span
    period_max = min(total_time / 2.0, clamp_period_max)
    # Number of frequency samples
    N_freq = int(oversample * total_time / cadence)
    # Frequency bounds
    f_min = 1.0 / period_max
    f_max = 1.0 / period_min
    # Uniform frequency grid and corresponding periods
    frequencies = np.linspace(f_min, f_max, N_freq)[::-1]
    periods = 1.0 / frequencies
    return periods

def generate_Ofir2014_period_grid(
    time_span,
    R_star=1.0,
    M_star=1.0,
    period_min=2.0,
    clamp_period_max=50.0,
    oversampling_factor=1.0,
    n_transits_min=3,
):
    """
    Generate a period grid following Ofir+2014 with cubic frequency sampling.

    Args:
        time_span (float): Total observing time span in days.
        R_star (float): Stellar radius in solar radii (default=1.0).
        M_star (float): Stellar mass in solar masses (default=1.0).
        period_min (float): Minimum period to search (default=2.0 days).
        clamp_period_max (float): Maximum period to search (default=50.0 days, clamped to time_span/2).
        oversampling_factor (float): Oversampling factor A denominator (default=1.0).
        n_transits_min (int): Minimum number of transits (default=3).

    Returns:
        numpy.ndarray: Trial periods in days spanning [period_min, period_max].
    """
    import numpy as np
    from numpy import pi
    # Define constants locally to drop dependency on transitleastsquares
    R_sun = 6.957e8       # Solar radius in meters
    M_sun = 1.98847e30    # Solar mass in kg
    G = 6.67430e-11       # Gravitational constant in m^3 kg^-1 s^-2
    SECONDS_PER_DAY = 86400.0

    # convert to SI
    R = R_star * R_sun
    M = M_star * M_sun
    T = time_span * SECONDS_PER_DAY

    # Clamp maximum period to half the observing span
    period_max = min(time_span / 2.0, clamp_period_max)

    # NOTE: different from what Ofir advocates, which is a Roche-limit cutoff.
    f_min = 1.0 / period_max
    f_max = 1.0 / period_min

    A = ((2 * pi) ** (2.0 / 3) / pi) * R / (G * M) ** (1.0 / 3) / (T * oversampling_factor)
    C = f_min ** (1.0 / 3) - A / 3.0
    N_opt = (f_max ** (1.0 / 3) - f_min ** (1.0 / 3) + A / 3.0) * 3.0 / A

    X = np.arange(int(N_opt)) + 1
    f_x = (A / 3.0 * X + C) ** 3
    P_x = 1.0 / f_x[::-1]

    periods = P_x / SECONDS_PER_DAY
    mask = (periods > period_min) & (periods <= period_max)
    return periods[mask]

def generate_Jenkins2010_period_grid(
    duration,
    total_time,
    period_min,
    period_max,
    min_corr: float = 0.9,
):
    """
    Generate a period grid for TPS given transit duration and observing span (Jenkins et al. 2010).

    Args:
        duration (float or astropy.units.Quantity): Transit duration in days.
        total_time (float or astropy.units.Quantity): Total observing time span in days.
        period_min (float or astropy.units.Quantity): Minimum period to search.
        period_max (float or astropy.units.Quantity): Maximum period to search.
        min_corr (float): Minimum overlap correlation between templates.

    Returns:
        numpy.ndarray: Trial periods spanning [period_min, period_max].
    """

    periods = [period_min]
    P = period_min
    while P < period_max:
        delta_P = 4 * (1 - min_corr) * duration * P / total_time
        P = P + delta_P
        periods.append(P)
    return np.array(periods)

