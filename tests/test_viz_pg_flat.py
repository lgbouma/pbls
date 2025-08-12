import matplotlib.pyplot as plt; import numpy as np; import pandas as pd
from pbls.lc_processing import get_LS_Prot
from pbls.periodogram_processing import trimmean_whitening

star_ids = [
    'kplr010736489', # kep1974
    'kplr006184894', # kep1627
    'kplr008653134', # kep1643
]

for star_id in star_ids:

    lcpath = f'/Users/luke/Dropbox/proj/pbls/results/masked_lightcurves/{star_id}_masked_lightcurve_iter0.csv'
    pgpath = f'/Users/luke/Dropbox/proj/pbls/results/merged_periodograms/{star_id}_merged_pbls_periodogram_iter0.csv'

    df = pd.read_csv(pgpath)
    lcdf = pd.read_csv(lcpath)

    LS_Prot = get_LS_Prot(lcdf.time, lcdf.flux_original)
    print(LS_Prot)

    x = np.array(df.period)
    y = np.array(df.power)
    pg_results = trimmean_whitening(x, y, Prot=LS_Prot)

    max_key = max(np.array(list(pg_results.keys())))

    merged_harmonics = pg_results[max_key]['merged_harmonics']
    window_widths = pg_results[max_key]['window_widths']

    plt.close("all")
    fig, axs = plt.subplots(figsize=(12,3), nrows=2, sharex=True)

    axs[0].plot(df.period, df.power, c='k', lw=0.5)
    axs[1].plot(df.period, pg_results[max_key]['residual'], c='k', lw=0.5)

    if LS_Prot < 3:
        for harmonic, width in zip(merged_harmonics, window_widths):
            if harmonic < 50:
                left  = harmonic - width/2
                right = harmonic + width/2
                axs[0].axvspan(left, right, color='C2', alpha=0.3, zorder=-1)

    axs[0].update({'ylabel':'SNR'})
    axs[1].update({'ylabel':'postSNR', 'xlabel':'period [days]'})

    outpath = f'/Users/luke/Dropbox/proj/pbls/results/periodogram_cleaning/{star_id}_pg_cleaning.png'
    fig.savefig(outpath, bbox_inches='tight', dpi=300)
    print(f'made {outpath}')
