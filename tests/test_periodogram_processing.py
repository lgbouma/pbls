import os
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time as timemodule

from pbls.paths import TESTRESULTSDIR
from pbls.periodogram_processing import (
    iterative_gaussian_whitening, trimmean_whitening
)
from pbls.pbls import pbls_search
from pbls.visualization import plot_summary_figure

def test_periodogram_processing(Porb=3.1666, Prot=1.4, method='itergaussian'):

    csv_path = os.path.join(TESTRESULTSDIR, 'csv', f"pbls_search_periodogram_Porb{Porb:.3f}_Prot{Prot:.3f}.csv")
    lc_path = os.path.join(TESTRESULTSDIR, 'csv', f"pbls_search_lightcurve_Porb{Porb:.3f}_Prot{Prot:.3f}.csv")

    df = pd.read_csv(csv_path)
    x, y = df['period'].values, df['power'].values
    x_start, y_start = x.copy(), y.copy()
    df = pd.read_csv(lc_path)
    time, flux = df['time'].values, df['flux'].values

    if method == 'itergaussian':
        pg_results = iterative_gaussian_whitening(x, y)
    elif method == 'trimmean':
        pg_results = trimmean_whitening(x, y)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'itergaussian' or 'trimmean'.")

    # read the whitened periodogram results; recalculate best-fit model params
    max_key = max(np.array(list(pg_results.keys())))
    peak_period = pg_results[max_key]['peak_period']
    durations_hr = np.array([1,2,3,4])
    epoch_steps = 50
    poly_order = 3
    res = pbls_search(time, flux, np.array([peak_period]), durations_hr, epoch_steps, poly_order)

    # Extract period-level max SNR and corresponding best model params
    power0 = res['power'][0]
    bp = res['best_params']
    bm = res['best_model']

    # Plot summary figure (based on the peak found after gaussian peak whitening)
    fig = plot_summary_figure(time, flux, x_start, y_start, bp, bm)

    plot_path = os.path.join(TESTRESULTSDIR, 'png', f"test_pbls_search_result_pgproc{method}_Porb{Porb:.3f}_Prot{Prot:.3f}.png")
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    # Animated periodogram fitting/subtraction
    fig_anim, ax_anim = plt.subplots(figsize=(10, 6))

    def animate(i):

        ax_anim.clear()
        data = pg_results[i]
        mask = data['subtract_mask']
        ax_anim.plot(data['x'], data['y_start'], c='k', lw=0.5, zorder=1)
        
        if method == 'itergaussian':
            ax_anim.plot(data['x'][mask], data['model'] + data['offset'],
            c='C1', lw=2, zorder=-1, alpha=0.5)
        elif method == 'trimmean':
            ax_anim.plot(data['x'], data['model'],
            c='C1', lw=2, zorder=-1, alpha=0.5)
            
        ax_anim.set_title(f"Iteration {i} - Peak Period: {data['peak_period']:.3f} days")
        ax_anim.set_xlabel("Period (days)")
        ax_anim.set_ylabel("Power")

    frames = sorted(pg_results.keys())
    ani = animation.FuncAnimation(fig_anim, animate, frames=frames,
                                interval=800, blit=False, repeat=False)

    anim_path = os.path.join(TESTRESULTSDIR, 'mp4',
        f"periodogram_animation_{method}_Porb{Porb:.3f}_Prot{Prot:.3f}.mp4")
    ani.save(anim_path, writer='ffmpeg', dpi=300)
    plt.close(fig_anim)

if __name__ == "__main__":
    test_periodogram_processing(Porb=3.1666, Prot=3.3)
    print("Test completed successfully.")