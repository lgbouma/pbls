import numpy as np
import multiprocessing as mp
from .pbls import pbls_search


def _worker(args):
    time, flux, trial_period, durations, epoch_steps, poly_order = args
    # Run pbls_search for a single period
    res = pbls_search(time, flux, np.array([trial_period]), durations, epoch_steps, poly_order)
    # Extract period-level max SNR and corresponding best model params
    power0 = res['power'][0]
    bp = res['best_params']
    bm = res['best_model']
    return (trial_period, power0, bp['snr'], bp['duration'], bp['epoch'], bp['depth'], bm)


def fast_pbls_search(time, flux, periods, durations, epoch_steps=50, poly_order=2, nworkers = mp.cpu_count()):
    """
    Parallel accelerated variant of pbls_search using multiprocessing over periods.
    """
    maxworkertasks = 1000
    pool = mp.Pool(nworkers, maxtasksperchild=maxworkertasks)
    # Prepare tasks for each trial period
    tasks = [(time, flux, p, durations, epoch_steps, poly_order) for p in periods]
    # Execute tasks in parallel, preserving order
    results = pool.map(_worker, tasks)
    pool.close()
    pool.join()

    # Unpack results
    power_list = [r[1] for r in results]
    snr_list = [r[2] for r in results]
    # Identify global best index
    best_idx = int(np.argmax(snr_list))
    best_period, _, best_snr, best_duration, best_epoch, best_depth, best_model = results[best_idx]

    # Build output matching pbls_search signature
    return {
        'best_params': {
            'period': best_period,
            'duration': best_duration,
            'epoch': best_epoch,
            'depth': best_depth,
            'snr': best_snr
        },
        'power': np.array(power_list),
        'periods': periods,
        'best_model': best_model
    }