"""
Contents:
    join_tarball_chunks_to_periodogram
"""
from pbls.pipeline_utils import extract_tarball
from glob import glob
import os, pickle, socket
from os.path import join
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from pbls.visualization import plot_periodogram

def join_tarball_chunks_to_periodogram(star_id, iter_ix=0):
    """
    NOTE: this function is probably deprecated by drivers/run_pbls_merge.py.
    """
    raise DeprecationWarning(
        "This function is deprecated. "
        "Please use drivers/run_pbls_merge.py instead."
    )

    hostname = socket.gethostname()

    if hostname in ['wh1', 'wh2', 'wh3']:
        receivingdir = f'/ar0/RECEIVING/{star_id}'
        processingdir = f'/ar0/PROCESSING/{star_id}'
        outprocessingdir = f'/ar0/PROCESSING/merged_periodograms'
    elif 'osg' in hostname:
        receivingdir = f'/ospool/ap21/data/ekul/pbls_results/{star_id}'
        processingdir = f'/ospool/ap21/data/ekul/pbls_results/PROCESSING/{star_id}'
        outprocessingdir = f'/ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms'
    else:
        raise NotImplementedError(
            f"Hostname {hostname} not recognized. "
            "Please implement the logic for this hostname."
        )

    if not os.path.exists(processingdir):
        os.mkdir(processingdir)
    if not os.path.exists(outprocessingdir):
        os.mkdir(outprocessingdir)

    tar_paths = glob(join(receivingdir, f'joboutput_{star_id}*iter{iter_ix}.tar.gz'))
    N_tars = len(tar_paths)
    print(f'Found {N_tars} tarballs for {star_id} in {receivingdir}')

    for ix, tar_path in enumerate(tar_paths):
        if ix % int(N_tars/10) == 0:
            print(f"{ix}/{N_tars}...")
        extract_tarball(tar_path, processingdir, verbose=0)

    pklpaths = np.sort(glob(join(processingdir, 'srv', '*', f'{star_id}*iter{iter_ix}.pkl')))

    powers = []
    periods = []
    coeffs = []
    best_params = None
    best_model = None

    max_power = None

    for pklpath in np.sort(pklpaths):
        with open(pklpath, 'rb') as f:
            data = pickle.load(f)

            N = len(data['power'])

            if N == 0:
                print(f"Warning: {pklpath} has no data, skipping.")
                continue

            powers.append(data['power'])
            periods.append(data['periods'])
            coeffs.append(data['coeffs'])

            this_max_power = np.nanmax(data['power'])
            if max_power is None or this_max_power > max_power:
                max_power = this_max_power
                best_params = data['best_params']
                best_model = data['best_model']

    periods = np.concatenate(periods)
    powers = np.concatenate(powers)
    inds = np.argsort(periods)

    periods = periods[inds]
    powers = powers[inds]

    flat_coeffs = [arr for sublist in coeffs for arr in sublist]
    coeffs = [flat_coeffs[ind] for ind in inds]

    # Cache the resulting merged periodogram
    result = {
        'best_params': best_params,
        'power': powers,
        'periods': periods,
        'best_model': best_model,
        'coeffs': coeffs
    }

    outdf = pd.DataFrame({'period': periods, 'power': powers})
    outcsv = join(outprocessingdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.csv')
    outdf.to_csv(outcsv, index=False)
    print(f"Wrote merged periodogram to {outcsv}")

    outpickle = join(outprocessingdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.pkl')
    with open(outpickle, 'wb') as f:
        pickle.dump(result, f)
    print(f"Wrote merged periodogram to {outpickle}")

    outpng = join(outprocessingdir, f'{star_id}_merged_pbls_periodogram_iter{iter_ix}.png')
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_periodogram(ax, periods, powers, title=f'PBLS {star_id}')
    fig.savefig(outpng, dpi=300, bbox_inches='tight')
    print(f"Wrote merged periodogram plot to {outpng}")

    print(best_params)


if __name__ == '__main__':
    #join_tarball_chunks_to_periodogram(star_id='kplr006184894')  # kepler-1627
    join_tarball_chunks_to_periodogram(star_id='kplr008653134') # kepler-1643
