import numpy as np
import numba
import warnings

def split_segments(idx):
    """
    Given sorted indices idx, split into lists of contiguous runs.
    E.g. [2,3,4, 10,11] → [[2,3,4], [10,11]]
    """
    if idx.size == 0:
        return []
    # find breakpoints
    gaps = np.where(np.diff(idx) > 1)[0]
    starts = np.concatenate(([0], gaps + 1))
    ends   = np.concatenate((gaps, [idx.size - 1]))
    return [idx[s:e+1] for s, e in zip(starts, ends)]


@numba.njit
def detrend_segment(t_loc, f_loc, out_idx, poly_order):
    N = t_loc.shape[0]
    M = poly_order + 1
    Nout = out_idx.shape[0]
    # build Vandermonde matrix on out-of-transit points
    Vout = np.empty((Nout, M))
    for i in range(Nout):
        x = t_loc[out_idx[i]]
        for j in range(M):
            Vout[i, j] = x ** (poly_order - j)
    # normal equations: (VᵀV) c = Vᵀ f
    ATA = Vout.T @ Vout
    # → add small diagonal ridge to avoid singular matrix
    eps = 1e-8
    for j in range(M):
        ATA[j, j] += eps
    ATb = Vout.T @ f_loc[out_idx]
    coeffs = np.linalg.solve(ATA, ATb)
    # evaluate polynomial on all points
    mval = np.empty(N)
    for i in range(N):
        acc = 0.0
        for j in range(M):
            acc += coeffs[j] * (t_loc[i] ** (poly_order - j))
        mval[i] = acc
    return mval, f_loc - mval, coeffs

def pbls_search(time, flux, periods, durations_hr, epoch_steps=50, poly_order=2):
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
    durations_hr : np.ndarray
        Array of trial durations in units of hours.
    epoch_steps : int, optional
        Number of trial start phases for each (period, duration_hr) combination.
        The phases range from 0 to (1 - frac_duration).
    poly_order : int, optional
        Order of the local polynomial to be fit in time (e.g., 2 for quadratic).
    
    Returns
    -------
    dict
        A dictionary with the following keys:
          'best_params': dict with best period, duration_hr, epoch, depth, and snr.
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
    best_duration_hr = None
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
    coeff_list = []
    
    tmin = np.min(time)
    tmax = np.max(time)
    
    # Ensure time and flux are sorted in time
    sort_idx = np.argsort(time)
    time = time[sort_idx]
    flux = flux[sort_idx]
    
    # Loop over trial periods
    for trial_period in periods:

        period_max_snr = -np.inf
        coeffs_max_snr = None
        phase = ((time - tmin) % trial_period) / trial_period # pre-fold once per period

        durations = (durations_hr / 24.) / trial_period
        
        # Loop over trial durations
        for trial_duration in durations:
           
            # Define possible start phases (epochs) from 0 to (1 - duration)
            epochs = np.linspace(0, 1 - trial_duration, epoch_steps)

            half_pd = trial_duration * 0.5

            for epoch in epochs:

                # #2-#4: create a mask of all in transit points, which when
                # iterated over, yields each transit.
                
                # 2) compute relative phase to nearest transit center
                center_phase = epoch + half_pd
                rel_phase    = phase - center_phase
                rel_phase   -= np.round(rel_phase)     # now in [-0.5, +0.5]

                # 3) single local_mask for ±3 Tdur
                win = 3.0 * trial_duration
                local_mask = np.abs(rel_phase) <= win
                local_idx_all = np.nonzero(local_mask)[0]
                if local_idx_all.size < (poly_order + 1):
                    continue

                # 4) split into contiguous transits
                segs = split_segments(local_idx_all)
                good_transits = []
                for seg in segs:
                    # in-transit in this segment
                    in_mask = np.abs(rel_phase[seg]) <= half_pd
                    out_mask = ~in_mask
                    if out_mask.sum() < (poly_order + 1):
                        continue
                    # store segment idx + local in-transit positions
                    good_transits.append((seg, np.nonzero(in_mask)[0]))

                if not good_transits:
                    continue

                # “second pass”: iterate over each segment (each transit)
                all_in_flux = []; all_out_flux = []
                local_times = []; local_fluxes = []
                models      = []; residuals = []                
                poly_coeffs = []

                for (local_idx, in_local) in good_transits:
                    t_loc = time[local_idx]
                    f_loc = flux[local_idx]
                    out_local = np.setdiff1d(np.arange(len(local_idx)), in_local)

                    # fit poly to out-of-transit using either numba or polyfit.
                    # _t0 subtraction improves numerical stability.
                    USE_NUMBA = True
                    if USE_NUMBA:
                        _t0 = np.nanmedian(t_loc[out_local])
                        mval, fcor, poly = detrend_segment(t_loc - _t0, f_loc, out_local, poly_order)
                    else:
                        _t0  = np.nanmedian(t_loc[out_local])
                        p    = np.polyfit(t_loc[out_local] - _t0, f_loc[out_local], poly_order)
                        poly = np.poly1d(p)
                        mval = poly(t_loc - _t0)
                        fcor = f_loc - mval

                    poly_coeffs.append(poly)
                    local_times.append(t_loc)
                    local_fluxes.append(f_loc)
                    models.append(mval)
                    residuals.append(fcor)

                    all_in_flux.append (fcor[in_local])
                    all_out_flux.append(fcor[out_local])                

                # Concatenate data from all good transits for this (trial_period, trial_duration, epoch) trial
                all_in_transit_flux = np.concatenate(all_in_flux)
                all_out_transit_flux = np.concatenate(all_out_flux)
                local_time_concat = np.concatenate(local_times)
                local_flux_concat = np.concatenate(local_fluxes)
                model_flux_concat = np.concatenate(models)
                flux_resid_concat = np.concatenate(residuals)
                poly_coeffs_concat = np.vstack(poly_coeffs)
                
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
                    coeffs_max_snr = poly_coeffs_concat
                
                # Update global best parameters and best-model arrays if this trial is best so far
                if snr > best_snr:
                    best_snr = snr
                    best_period = trial_period
                    best_duration_hr = trial_duration * trial_period * 24.0  # convert to hours
                    best_epoch = epoch
                    best_depth = depth
                    
                    best_local_time = local_time_concat
                    best_local_flux = local_flux_concat
                    best_model_flux = model_flux_concat
                    best_flux_resid = flux_resid_concat
                    best_all_in_transit_flux = all_in_transit_flux
                    best_all_out_transit_flux = all_out_transit_flux

        power_list.append(period_max_snr)
        coeff_list.append(coeffs_max_snr)
    
    # Construct output dictionary with nested dictionaries
    result = {
        'best_params': {
            'period': best_period,
            'duration_hr': best_duration_hr,
            'epoch': best_epoch,
            'depth': best_depth,
            'snr': best_snr
        },
        'power': np.array(power_list),
        'coeffs': coeff_list,
        'periods': periods,
        'best_model': {
            'time': best_local_time,
            'flux': best_local_flux,
            'model_flux': best_model_flux,
            'flux_resid': best_flux_resid,
            'all_in_transit_flux': best_all_in_transit_flux,
            'all_out_transit_flux': best_all_out_transit_flux,
        }
    }
    
    return result