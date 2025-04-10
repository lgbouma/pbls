import matplotlib.pyplot as plt
import numpy as np

def plot_raw_light_curve(ax, time, flux):
    """
    Plot the raw light curve on the provided Axes.
    """
    ax.plot(time, flux, 'k.', markersize=2)
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Flux")
    ax.set_title("Raw Light Curve")

def plot_periodogram(ax, periods, power):
    """
    Plot the periodogram on the provided Axes.
    """
    ax.plot(periods, power, 'b-')
    ax.set_xlabel("Trial Period (days)")
    ax.set_ylabel("Detection Statistic")
    ax.set_title("pbls_search Periodogram")

def plot_best_model(ax, best_model):
    """
    Plot the best-model raw data on the provided Axes.
    The plot shows the raw data (best_model['flux'] vs best_model['time'])
    with the best-fit polynomial model (best_model['model_flux']) underplotted.
    """
    ax.plot(best_model['time'], best_model['flux'], 'k.', markersize=2, label="Data")

    # Split best_model['time'] and best_model['model_flux'] into segments at gaps > 0.5 days.
    time_arr = best_model['time']
    model_flux = best_model['model_flux']

    # Compute differences between successive time points.
    dt = np.diff(time_arr)

    # Find indices where gap exceeds 0.5 days.
    gap_indices = np.where(dt > 0.5)[0]

    # Build segments as slices.
    segments = []
    start_idx = 0
    for gap_idx in gap_indices:
        segments.append(slice(start_idx, gap_idx + 1))
        start_idx = gap_idx + 1
    segments.append(slice(start_idx, len(time_arr)))

    # Plot each segment separately, labeling only the first segment.
    first_segment = True
    for seg in segments:
        if first_segment:
            ax.plot(time_arr[seg], model_flux[seg], 'r-', linewidth=1.5, zorder=0, label="Model")
            first_segment = False
        else:
            ax.plot(time_arr[seg], model_flux[seg], 'r-', linewidth=1.5, zorder=0)

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Flux")
    ax.set_title("Best-Model Raw Data")
    ax.legend()

def plot_detrended_flux(ax, best_model):
    """
    Plot the detrended flux (flux_resid vs time) on the provided Axes.
    """
    ax.plot(best_model['time'], best_model['flux_resid'], 'k.', markersize=2)
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Detrended Flux")
    ax.set_title("Detrended Flux (Residuals)")

def plot_phase_folded_best(ax, best_model, best_params):
    """
    Plot the phase-folded recovered signal on the provided Axes.
    The best_model['time'] and best_model['flux_resid'] are folded using best_params['period'].
    """
    period = best_params['period']
    phase = (best_model['time'] % period) / period
    ax.plot(phase, best_model['flux_resid'], 'k.', markersize=2)
    ax.set_xlabel("Phase")
    ax.set_ylabel("Detrended Flux")
    ax.set_title("Phase-Folded Recovered Signal")
    # Highlight the transit region using best_params (epoch and duration are in phase units)
    ax.axvspan(best_params['epoch'], best_params['epoch'] + best_params['duration'], color='red', alpha=0.3)

def plot_summary_text(ax, best_params):
    """
    Plot a text summary of the best pbls_search results on the provided Axes.
    """
    period = best_params['period']
    epoch = best_params['epoch']
    duration = best_params['duration']
    depth = best_params['depth']
    snr = best_params['snr']
    
    # Convert phase to days for epoch and transit duration.
    epoch_days = epoch * period
    duration_days = duration * period
    duration_hours = duration_days * 24
    depth_ppt = depth * 1000
    
    summary = (
        f"Best pbls_search Results:\n"
        f"Period: {period:.3f} days\n"
        f"Epoch: {epoch_days:.3f} days\n"
        f"Duration: {duration_hours:.1f} hours\n"
        f"Depth: {depth_ppt:.1f} ppt\n"
        f"SNR: {snr:.1f}"
    )
    ax.text(0.05, 0.95, summary, transform=ax.transAxes,
            fontsize=12, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    ax.axis('off')

def plot_summary_figure(time, flux, periods, power, best_params, best_model):
    """
    Create a summary figure with the following panels:
      A: Raw light curve (time vs flux)
      B: Periodogram (trial periods vs detection statistic)
      C: Best-model raw data (best_model['time'] and best_model['flux'] with best_model['model_flux'] underplotted)
      D: Detrended flux (best_model['flux_resid'] vs best_model['time'])
      E: Phase-folded recovered signal (fold best_model['time'] and best_model['flux_resid'] using best_params)
      F: Text summary of best pbls_search results
      
    The mosaic layout is:
    
        AAAAAA
        BBBBBB
        CCCCCC
        DDEEFF
        DDEEFF
    """
    mosaic = """
AAAAAA
BBBBBB
CCCCCC
DDEEFF
DDEEFF
""".strip()
    
    fig, axd = plt.subplot_mosaic(mosaic, figsize=(14, 10))
    
    # Panel A: Raw light curve
    plot_raw_light_curve(axd['A'], time, flux)
    
    # Panel B: Periodogram
    plot_periodogram(axd['D'], periods, power)
    
    # Panel C: Best-model raw data
    plot_best_model(axd['B'], best_model)
    
    # Panel D: Detrended flux (residuals)
    plot_detrended_flux(axd['C'], best_model)

    tmin, tmax = time.min(), time.max()
    for ax in [axd['A'], axd['B'], axd['C']]:
        ax.set_xlim((tmin, tmax))
    
    # Panel E: Phase-folded recovered signal
    plot_phase_folded_best(axd['E'], best_model, best_params)
    
    # Panel F: Text summary of best pbls_search results
    plot_summary_text(axd['F'], best_params)
    
    plt.tight_layout()
    return fig
