import numpy as np

def generate_synthetic_light_curve(period=2.0, duration=0.1, epoch=0.3, depth=0.01, 
                                   total_time=20.0, cadence=0.01, noise_level=0.001):
    """
    Generate a synthetic light curve with a box-shaped transit.
    
    Parameters:
        period : float
            True period of the transit.
        duration : float
            Transit duration as a fraction of the period.
        epoch : float
            Transit start phase (0 to 1).
        depth : float
            Transit depth (flux drop).
        total_time : float
            Total duration of the observations.
        cadence : float
            Time interval between observations.
        noise_level : float
            Standard deviation of Gaussian noise added to the flux.
            
    Returns:
        tuple: (time, flux) arrays.
    """
    time = np.arange(0, total_time, cadence)
    flux = np.ones_like(time)
    
    duration_days = duration * period

    in_transit = np.abs(  (time - epoch + 0.5*period) % period - 0.5 * period )  < 0.5 * duration_days

    flux[in_transit] -= depth
    
    # Add Gaussian noise
    flux += np.random.normal(0, noise_level, size=flux.shape)
    
    return time, flux

def generate_transit_rotation_light_curve(
    time: np.ndarray,
    transit_dict: dict,
    rotation_dict: dict,
    noise_level: float=0.001,
) -> np.ndarray:
    """
    Generate a synthetic light curve with a transit and stellar rotation signals.

    Parameters
    ----------
    time : np.ndarray
        Array of time values (e.g., in days).
    transit_dict : dict
        Dictionary containing transit parameters. Example keys:
            - 'period': The orbital period of the transiting planet.
            - 't0': The reference (center) time of the first transit.
            - 'depth': The transit depth, in relative flux units (e.g., 0.01 for 1%).
            - 'duration': The total transit duration in the same units as `time`.
              (Or you can define ingress/egress more elaborately if desired.)
            - ... (anything else you need)
    rotation_dict : dict
        Dictionary containing stellar rotation parameters. Example keys:
            - 'prot': The stellar rotation period.
            - 'a1': Amplitude of the primary sinusoid (larger amplitude).
            - 'a2': Amplitude of the secondary sinusoid (smaller amplitude).
            - 'phi1': Phase offset (radians) for the primary sinusoid.
            - 'phi2': Phase offset (radians) for the secondary sinusoid.
            - ... (anything else you need)
    noise_level : float
        Standard deviation of Gaussian noise added to the flux.

    Returns
    -------
    flux : np.ndarray
        The synthetic flux values at each time point, combining rotation and transit.
    """

    # --- 1) Stellar Rotation Model ---
    # We model the rotation as a sum of two sinusoids:
    #   rotation_flux(t) = a1*sin(2π * t / prot + φ1) + a2*sin(4π * t / prot + φ2)
    # (since the second sinusoid is at Prot/2, that doubles the frequency)
    prot = rotation_dict.get('prot', 25.0)    # default to 25 days for rotation
    a1   = rotation_dict.get('a1', 5e-3)      # amplitude (larger)
    a2   = rotation_dict.get('a2', 1e-3)      # amplitude (smaller)
    phi1 = rotation_dict.get('phi1', 0.0)     # phase offset (radians)
    phi2 = rotation_dict.get('phi2', 0.0)     # phase offset (radians)

    rotation_flux = (
        a1 * np.sin((2 * np.pi / prot) * time + phi1) +
        a2 * np.sin((4 * np.pi / prot) * time + phi2)
    )

    # --- 2) Transit Model ---
    # For simplicity, we treat the transit as a simple box-shape:
    #   if (time is in-transit) => flux dips by 'depth'
    # More sophisticated transit shapes could be used.

    period      = transit_dict.get('period', 10.0)     # planet's orbital period
    t0          = transit_dict.get('t0', 0.0)          # time of central transit
    depth       = transit_dict.get('depth', 0.01)      # fraction of flux reduced (e.g., 0.01 = 1%)
    duration_hr = transit_dict.get('duration_hr', 3)   # duration of transit
    duration    = (duration_hr / 24.0) / period        # fractional duration

    # For a single transit, define the start and end times:
    # We can replicate across many orbital phases if needed (multiple transits).
    # Below, we apply the “box” across any integer multiple of period from t0.
    
    flux_transit = np.ones_like(time)  # baseline of 1.0
    # Identify in-transit points for each transit epoch:
    #   a planet transits at times t0 + k*period for integer k
    #   we mark those intervals as in-transit
    # For a box model, if |time - (t0 + k*period)| < duration/2 => in-transit
    # This naive approach does not handle overlapping transits or more complicated setups.

    # You can customize this to handle an arbitrary number of transits.
    # For example, we find all integer k that place a transit within the time range.
    # (We’ll do a rough bounding for k; you might refine this logic if your time is large.)
    k_min = int(np.floor((time[0] - t0) / period))
    k_max = int(np.ceil((time[-1] - t0) / period))

    for k in range(k_min, k_max+1):
        # The center of the k-th transit
        transit_center = t0 + k * period
        # Mark in-transit points
        in_transit = np.abs(time - transit_center) <= (duration / 2.0)
        # Reduce flux by 'depth' for in-transit times
        flux_transit[in_transit] -= depth

    # --- 3) Combine the signals ---
    # Usually, the rotation would modulate the star’s out-of-transit baseline flux near ~1.0.
    # We add the rotation variation on top of the baseline, then multiply by the transit “dip.”
    # For a small amplitude rotation model, you can add it linearly. 
    # But combining it multiplicatively is also common. 
    # For a simpler approach: final flux = baseline(=1) + rotation - transit_depth
    # We'll assume small amplitude => additive for rotation, multiplicative for transit.
    # So final_flux(t) = (1 + rotation_flux(t)) * (flux_transit(t))
    # (since flux_transit(t) is 1 out-of-transit, 1 - depth in-transit)
    
    flux = (1.0 + rotation_flux) * flux_transit

    # Add Gaussian noise
    flux += np.random.normal(0, noise_level, size=flux.shape)

    return flux