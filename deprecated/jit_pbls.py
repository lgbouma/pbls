"""
(Failing) Numba-accelerated version of pbls_search.

Contains manual implementations for setdiff1d and polyfit.

Contents:
    fast_pbls_search
    fast_pbls_search_jit
"""
import numpy as np
from numba import njit, prange

# rename jit version and return flat tuple instead of dict
@njit(parallel=True)
def fast_pbls_search_jit(time, flux, periods, durations, epoch_steps=50, poly_order=2):
    """
    Numba-accelerated clone of pbls_search. Parallelizes over trial periods (and/or epochs).
    """
    # Initialize best-fit variables
    best_snr = -1e300
    best_period = 0.0
    best_duration = 0.0
    best_epoch = 0.0
    best_depth = 0.0

    # Prepare containers for best model (must be arrays for numba)
    best_local_time = np.empty(0, dtype=np.float64)
    best_local_flux = np.empty(0, dtype=np.float64)
    best_model_flux = np.empty(0, dtype=np.float64)
    best_flux_resid = np.empty(0, dtype=np.float64)
    best_all_in_transit_flux = np.empty(0, dtype=np.float64)
    best_all_out_transit_flux = np.empty(0, dtype=np.float64)

    power_list = np.empty(periods.shape[0])
    
    # Sort time & flux
    # ...numba‐friendly sort or assume pre‐sorted...

    # Outer loop over periods
    for i in prange(periods.shape[0]):
        trial_period = periods[i]
        period_max_snr = -1e300

        # Loop over durations
        for j in range(durations.shape[0]):
            trial_duration = durations[j]
            Tdur = trial_duration * trial_period
            # Loop over epochs
            for k in range(epoch_steps):
                epoch = k * (1.0 - trial_duration) / max(epoch_steps-1,1)
                
                # Define a reference transit start time T0 (the first possible transit)
                T0 = time[0] + epoch * trial_period
                
                # Determine how many transits fall within the observation window:
                n_min = int(np.ceil((time[0] - T0) / trial_period))
                n_max = int(np.floor((time[-1] - T0) / trial_period))
                
                # First pass: Identify "good" transits that have enough data to fit a polynomial.
                good_transits = []
                for n in range(n_min, n_max + 1):
                    # Center time for the nth transit: transit start + half duration
                    Tcenter = T0 + n * trial_period + 0.5 * Tdur
                    
                    # Define the local window (±3 transit durations)
                    local_start = Tcenter - 3.0 * Tdur
                    local_end   = Tcenter + 3.0 * Tdur
                    local_mask = (time >= local_start) & (time <= local_end)
                    local_idx = np.where(local_mask)[0]
                    if len(local_idx) < (poly_order + 1):
                        continue
                    
                    # Define the in-transit region (±0.5 Tdur around Tcenter)
                    in_transit_start = Tcenter - 0.5 * Tdur
                    in_transit_end   = Tcenter + 0.5 * Tdur
                    in_transit_full = (time >= in_transit_start) & (time <= in_transit_end)
                    # Get indices relative to the local window
                    in_transit_local = np.where(in_transit_full[local_idx])[0]
                    # Out-of-transit indices within the local window:
                    # Manual out-of-transit index computation (numba‐friendly)
                    n_local = len(local_idx)
                    temp_out = np.empty(n_local, np.int64)
                    cnt = 0
                    for ii in range(n_local):
                        is_in = False
                        for jj in range(len(in_transit_local)):
                            if ii == in_transit_local[jj]:
                                is_in = True
                                break
                        if not is_in:
                            temp_out[cnt] = ii
                            cnt += 1
                    out_transit_local = temp_out[:cnt]
                    if cnt < (poly_order + 1):
                        continue
                    good_transits.append((local_idx, in_transit_local))
                
                # If no transit in this (period, duration, epoch) trial is "good", skip it.
                if len(good_transits) == 0:
                    continue
                
                # --- begin numba-friendly concat replacement ---
                # 1) compute total sizes
                tot_in = 0
                tot_out = 0
                tot_loc = 0
                for gt in good_transits:
                    loc_idx, in_idx = gt
                    nloc = loc_idx.shape[0]
                    nin  = in_idx.shape[0]
                    tot_loc += nloc
                    tot_in  += nin
                    tot_out += (nloc - nin)
                # 2) allocate flat arrays
                all_in_flux   = np.empty(tot_in)
                all_out_flux  = np.empty(tot_out)
                local_time    = np.empty(tot_loc)
                local_flux    = np.empty(tot_loc)
                model_flux    = np.empty(tot_loc)
                flux_resid    = np.empty(tot_loc)
                # 3) fill them
                pi = 0    # in-transit pointer
                po = 0    # out-transit pointer
                pl = 0    # local-pointer
                for gt in good_transits:
                    loc_idx, in_idx = gt
                    t_loc = time[loc_idx]
                    f_loc = flux[loc_idx]
                    # fit+model (use your existing manual Vandermonde code here)
                    # manual Vandermonde fit for numba
                    x = t_loc[out_transit_local]
                    y = f_loc[out_transit_local]
                    m = x.shape[0]
                    n = poly_order + 1
                    # build Vandermonde matrix A (m × n)
                    A = np.empty((m, n))
                    for ii in range(m):
                        for jj in range(n):
                            A[ii, jj] = x[ii] ** (poly_order - jj)
                    # normal equations: ATA · coef = ATy
                    AT = A.T
                    ATA = AT.dot(A)
                    ATy = AT.dot(y)
                    coef = np.linalg.solve(ATA, ATy)
                    # evaluate on full local grid
                    Nloc = t_loc.shape[0]
                    model_vals = np.empty(Nloc)
                    for ii in range(Nloc):
                        acc = 0.0
                        for jj in range(n):
                            acc += coef[jj] * (t_loc[ii] ** (poly_order - jj))
                        model_vals[ii] = acc
                    
                    # Subtract the polynomial from all data in the local window
                    f_local_corrected = f_loc - model_vals

                    # copy local blocks
                    nloc = t_loc.shape[0]
                    for ii in range(nloc):
                        local_time[pl] = t_loc[ii]
                        local_flux[pl] = f_loc[ii]
                        model_flux[pl] = model_vals[ii]
                        flux_resid[pl] = f_local_corrected[ii]
                        pl += 1
                    # split in/out
                    for jj in range(in_idx.shape[0]):
                        all_in_flux[pi] = f_local_corrected[in_idx[jj]]
                        pi += 1
                    # out: any index not in in_idx
                    for ii in range(nloc):
                        is_in = False
                        for jj in range(in_idx.shape[0]):
                            if ii == in_idx[jj]:
                                is_in = True
                                break
                        if not is_in:
                            all_out_flux[po] = f_local_corrected[ii]
                            po += 1

                # now use all_in_flux, all_out_flux, local_time/flux/model_flux/flux_resid
                depth = np.mean(all_out_flux) - np.mean(all_in_flux)
                n_in  = tot_in
                n_out = tot_out
                var_in  = np.var(all_in_flux)
                var_out = np.var(all_out_flux)
                snr = depth / np.sqrt(var_in/n_in + var_out/n_out)

                # update period_max_snr and best_* as before using these flat arrays
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
                    
                    best_local_time = local_time
                    best_local_flux = local_flux
                    best_model_flux = model_flux
                    best_flux_resid = flux_resid
                    best_all_in_transit_flux = all_in_flux
                    best_all_out_transit_flux = all_out_flux
                # --- end replacement ---

        power_list[i] = period_max_snr
    
    # instead of building a nested dict, return all components
    return (
        best_period, best_duration, best_epoch, best_depth, best_snr,
        power_list, periods,
        best_local_time, best_local_flux, best_model_flux, best_flux_resid,
        best_all_in_transit_flux, best_all_out_transit_flux
    )

# Python wrapper to assemble the final dict
def fast_pbls_search(time, flux, periods, durations, epoch_steps=50, poly_order=2):
    bp, bd, be, bdepth, bsnr, power, per, tloc, floc, mflux, fresid, influx, outflux = \
        fast_pbls_search_jit(time, flux, periods, durations, epoch_steps, poly_order)
    return {
        'best_params': {
            'period': bp,
            'duration': bd,
            'epoch': be,
            'depth': bdepth,
            'snr': bsnr
        },
        'power': power,
        'periods': per,
        'best_model': {
            'time': tloc,
            'flux': floc,
            'model_flux': mflux,
            'flux_resid': fresid,
            'all_in_transit_flux': influx,
            'all_out_transit_flux': outflux
        }
    }