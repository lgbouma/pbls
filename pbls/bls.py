import numpy as np

def box_least_squares(time, flux, min_period, max_period, period_step, 
                      min_duration, max_duration, duration_step, epoch_steps=100):
    """
    Perform the Box Least Squares (BLS) algorithm to search for periodic transit signals.
    
    Parameters:
        time : array-like
            Observation times.
        flux : array-like
            Observed brightness values (assumed detrended).
        min_period, max_period : float
            Search range for the transit period.
        period_step : float
            Increment step for trial periods.
        min_duration, max_duration : float
            Range of transit durations to test (expressed as a fraction of the period).
        duration_step : float
            Increment step for trial durations.
        epoch_steps : int, optional
            Number of trial transit start positions (epochs) to test for each period-duration combination.
            
    Returns:
        dict
            Dictionary containing:
                'best_period': Best-fit transit period.
                'best_duration': Best-fit transit duration (phase fraction).
                'best_epoch': Best-fit transit epoch (phase).
                'best_depth': Estimated transit depth.
                'best_snr': Signal-to-noise ratio of the best fit.
                'periods': Array of trial periods.
                'power': Array of maximum detection statistic for each trial period.
    """
    best_snr = -np.inf
    best_period = None
    best_duration = None
    best_epoch = None
    best_depth = None
    
    # Create vector for trial periods and corresponding periodogram power
    periods = np.arange(min_period, max_period, period_step)
    power_list = []

    durations = np.arange(min_duration, max_duration, duration_step)
    
    # Loop over trial periods
    for trial_period in periods:
        period_max_snr = -np.inf
        # Compute the phase for each time point
        phase = (time % trial_period) / trial_period
        sorted_indices = np.argsort(phase)
        phase_sorted = phase[sorted_indices]
        flux_sorted = flux[sorted_indices]
        
        # Loop over trial durations and epochs
        for trial_duration in durations:
            # Define a grid of possible transit start epochs
            epochs = np.linspace(0, 1 - trial_duration, epoch_steps)
            for epoch in epochs:
                in_transit_mask = (phase_sorted >= epoch) & (phase_sorted < (epoch + trial_duration))
                if np.sum(in_transit_mask) == 0 or np.sum(~in_transit_mask) == 0:
                    continue  # Skip if there are no points in or out of transit
                
                in_transit_flux = flux_sorted[in_transit_mask]
                out_transit_flux = flux_sorted[~in_transit_mask]
                
                # Estimate transit depth as the difference between out-of-transit and in-transit means
                transit_depth = np.mean(out_transit_flux) - np.mean(in_transit_flux)
                
                # Compute the signal-to-noise ratio (SNR)
                snr = transit_depth / np.sqrt(np.var(in_transit_flux) / np.sum(in_transit_mask) +
                                               np.var(out_transit_flux) / np.sum(~in_transit_mask))
                
                # Update the maximum SNR for this trial period
                if snr > period_max_snr:
                    period_max_snr = snr
                
                # Update global best if necessary
                if snr > best_snr:
                    best_snr = snr
                    best_period = trial_period
                    best_duration = trial_duration
                    best_epoch = epoch
                    best_depth = transit_depth
        
        power_list.append(period_max_snr)
    
    power_array = np.array(power_list)
    
    return {
        'best_period': best_period,
        'best_duration': best_duration,
        'best_epoch': best_epoch,
        'best_depth': best_depth,
        'best_snr': best_snr,
        'periods': periods,
        'power': power_array
    }
