import numpy as np

def pbls_search(time, flux, periods, durations, epoch_steps=50, poly_order=2):
    """
    A Box Least Squares (BLS) variant that fits and subtracts a local polynomial trend
    in the time domain around each transit event to mitigate stellar spot-induced variability.
    
    For each (period, duration, epoch) trial:
      1. Identify all transit events within the observed time range.
      2. In a first pass, compute the local time window for each transit (±3*Tdur)
         and check that there are enough out-of-transit points (outside ±0.5*Tdur)
         to perform a polynomial fit.
      3. In a second pass, for each "good" transit, fit a polynomial to the out-of-transit
         data (in time) and subtract it from the entire local window.
      4. Combine the corrected in-transit and out-of-transit fluxes across transits,
         then compute the transit depth and SNR.
    
    In addition, for the best-fit model (highest SNR), the function stores:
      a) The concatenated local times and original fluxes for all the good transits.
      b) The concatenated best-fit model fluxes (from the polynomial evaluated on the local time).
      c) The concatenated flux residuals after subtracting the polynomial model.
      d) The concatenated in-transit and out-of-transit fluxes (post-detrending).
    
    Parameters
    ----------
    time : np.ndarray
        1D array of time values (e.g., in days).
    flux : np.ndarray
        1D array of flux values corresponding to `time`.
    periods : np.ndarray
        Array of trial orbital periods.
    durations : np.ndarray
        Array of trial durations (as a fraction of the period).
        For example, if durations = [0.01, 0.02], these imply 1% and 2% of the period.
    epoch_steps : int, optional
        Number of trial start phases for each (period, duration) combination.
        The phases range from 0 to (1 - duration).
    poly_order : int, optional
        Order of the local polynomial to be fit in time (e.g., 2 for quadratic).
    
    Returns
    -------
    dict
        A dictionary with the following keys:
          'best_params': dict with best period, duration, epoch, depth, and snr.
          'power': numpy array of maximum SNR for each trial period.
          'periods': the trial periods array.
          'best_model': dict with concatenated arrays for:
               'time': local times,
               'flux': original local flux,
               'model_flux': best-fit polynomial evaluated on the local times,
               'flux_resid': detrended flux (flux - model_flux),
               'all_in_transit_flux': in-transit flux after detrending,
               'all_out_transit_flux': out-of-transit flux after detrending.
    """
    best_snr = -np.inf
    best_period = None
    best_duration = None
    best_epoch = None
    best_depth = None
    
    # These will store the best model's concatenated arrays
    best_local_time = None
    best_local_flux = None
    best_model_flux = None
    best_flux_resid = None
    best_all_in_transit_flux = None
    best_all_out_transit_flux = None
    
    power_list = []
    
    tmin = np.min(time)
    tmax = np.max(time)
    
    # Ensure time and flux are sorted in time
    sort_idx = np.argsort(time)
    time = time[sort_idx]
    flux = flux[sort_idx]
    
    # Loop over trial periods
    for trial_period in periods:
        period_max_snr = -np.inf
        
        # Loop over trial durations
        for trial_duration in durations:
            # Convert fractional duration to absolute time (in days)
            Tdur_in_days = trial_duration * trial_period
            
            # Define possible start phases (epochs) from 0 to (1 - duration)
            epochs = np.linspace(0, 1 - trial_duration, epoch_steps)
            
            for epoch in epochs:
                # Define a reference transit start time T0 (the first possible transit)
                T0 = tmin + epoch * trial_period
                
                # Determine how many transits fall within the observation window:
                n_min = int(np.ceil((tmin - T0) / trial_period))
                n_max = int(np.floor((tmax - T0) / trial_period))
                
                # First pass: Identify "good" transits that have enough data to fit a polynomial.
                good_transits = []  # Will store tuples: (local_idx, in_transit_local)
                for n in range(n_min, n_max + 1):
                    # Center time for the nth transit: transit start + half duration
                    Tcenter = T0 + n * trial_period + 0.5 * Tdur_in_days
                    
                    # Define the local window (±3 transit durations)
                    local_start = Tcenter - 3.0 * Tdur_in_days
                    local_end   = Tcenter + 3.0 * Tdur_in_days
                    local_mask = (time >= local_start) & (time <= local_end)
                    local_idx = np.where(local_mask)[0]
                    if len(local_idx) < (poly_order + 1):
                        continue
                    
                    # Define the in-transit region (±0.5 Tdur around Tcenter)
                    in_transit_start = Tcenter - 0.5 * Tdur_in_days
                    in_transit_end   = Tcenter + 0.5 * Tdur_in_days
                    in_transit_full = (time >= in_transit_start) & (time <= in_transit_end)
                    # Get indices relative to the local window
                    in_transit_local = np.where(in_transit_full[local_idx])[0]
                    # Out-of-transit indices within the local window:
                    out_transit_local = np.setdiff1d(np.arange(len(local_idx)), in_transit_local)
                    if len(out_transit_local) < (poly_order + 1):
                        continue
                    
                    good_transits.append((local_idx, in_transit_local))
                
                # If no transit in this (period, duration, epoch) trial is "good", skip it.
                if len(good_transits) == 0:
                    continue
                
                # Second pass: Process each good transit event and accumulate arrays.
                all_in_transit_flux_list = []
                all_out_transit_flux_list = []
                local_time_list = []
                local_flux_list = []
                model_flux_list = []
                flux_resid_list = []
                
                for (local_idx, in_transit_local) in good_transits:
                    t_local = time[local_idx]
                    f_local = flux[local_idx]
                    
                    # Out-of-transit indices within the local window
                    all_indices = np.arange(len(local_idx))
                    out_transit_local = np.setdiff1d(all_indices, in_transit_local)
                    
                    # Fit a polynomial to the out-of-transit data (in time)
                    p = np.polyfit(t_local[out_transit_local], f_local[out_transit_local], poly_order)
                    poly = np.poly1d(p)
                    
                    # Evaluate model on the local time array
                    model_vals = poly(t_local)
                    
                    # Subtract the polynomial from all data in the local window
                    f_local_corrected = f_local - model_vals
                    
                    # Append local arrays for best-model tracking
                    local_time_list.append(t_local)
                    local_flux_list.append(f_local)
                    model_flux_list.append(model_vals)
                    flux_resid_list.append(f_local_corrected)
                    
                    # Identify and store in-transit and out-of-transit detrended fluxes for SNR computation
                    all_in_transit_flux_list.append(f_local_corrected[in_transit_local])
                    all_out_transit_flux_list.append(f_local_corrected[out_transit_local])
                
                # Concatenate data from all good transits for this (trial_period, trial_duration, epoch) trial
                all_in_transit_flux = np.concatenate(all_in_transit_flux_list)
                all_out_transit_flux = np.concatenate(all_out_transit_flux_list)
                local_time_concat = np.concatenate(local_time_list)
                local_flux_concat = np.concatenate(local_flux_list)
                model_flux_concat = np.concatenate(model_flux_list)
                flux_resid_concat = np.concatenate(flux_resid_list)
                
                # Compute the transit depth and SNR on the detrended (residual) data
                depth = np.mean(all_out_transit_flux) - np.mean(all_in_transit_flux)
                n_in = len(all_in_transit_flux)
                n_out = len(all_out_transit_flux)
                var_in = np.var(all_in_transit_flux)
                var_out = np.var(all_out_transit_flux)
                snr = depth / np.sqrt(var_in / n_in + var_out / n_out)
                
                # Update period-level max SNR
                if snr > period_max_snr:
                    period_max_snr = snr
                
                # Update global best parameters and best-model arrays if this trial is best so far
                if snr > best_snr:
                    best_snr = snr
                    best_period = trial_period
                    best_duration = trial_duration
                    best_epoch = epoch
                    best_depth = depth
                    
                    best_local_time = local_time_concat
                    best_local_flux = local_flux_concat
                    best_model_flux = model_flux_concat
                    best_flux_resid = flux_resid_concat
                    best_all_in_transit_flux = all_in_transit_flux
                    best_all_out_transit_flux = all_out_transit_flux
        
        power_list.append(period_max_snr)
    
    # Construct output dictionary with nested dictionaries
    result = {
        'best_params': {
            'period': best_period,
            'duration': best_duration,
            'epoch': best_epoch,
            'depth': best_depth,
            'snr': best_snr
        },
        'power': np.array(power_list),
        'periods': periods,
        'best_model': {
            'time': best_local_time,
            'flux': best_local_flux,
            'model_flux': best_model_flux,
            'flux_resid': best_flux_resid,
            'all_in_transit_flux': best_all_in_transit_flux,
            'all_out_transit_flux': best_all_out_transit_flux
        }
    }
    
    return result