"""
Contents:
    
Big plots:
    plot_summary_figure
    plot_pbls_coeffs

Small helper functions:
    plot_raw_light_curve
    plot_periodogram
    plot_best_model
    plot_phase_folded_best
    plot_detrended_flux
    plot_summary_text
"""
import matplotlib.pyplot as plt
import numpy as np
from pbls.lc_processing import transit_mask

def plot_raw_light_curve(ax, time, flux):
    """
    Plot the raw light curve on the provided Axes.
    """
    ax.plot(time, flux, 'k.', markersize=2)
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Flux")
    ax.set_title("Raw Light Curve")

def plot_periodogram(ax, periods, power, title=None):
    """
    Plot the periodogram on the provided Axes.
    """
    ax.plot(periods, power, c='k', lw=0.5)
    ax.set_xlabel("Trial Period (days)")
    ax.set_ylabel("Detection Statistic")
    if title is not None:
        ax.set_title(title)

def plot_best_model(ax, best_model):
    """
    Plot the best-model raw data on the provided Axes.
    The plot shows the raw data (best_model['flux'] vs best_model['time'])
    with the best-fit polynomial model (best_model['model_flux']) underplotted.
    """
    ax.plot(best_model['time'], best_model['flux'], 'k.', markersize=2, label="Data")

    # Split best_model['time'] and best_model['model_flux'] into segments at gaps > 0.5 days.
    time_arr = np.array(best_model['time'])
    model_flux = np.array(best_model['model_flux'])

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

def plot_detrended_flux(ax, best_model, best_params):
    """
    Plot the detrended flux (flux_resid vs time) on the provided Axes.
    """
    t = np.array(best_model['time'])
    flux_resid = np.array(best_model['flux_resid'])

    ax.plot(t, flux_resid, 'k.', markersize=2)

    P = best_params['period']
    Tdur = best_params['duration_hr'] / 24
    t0 = best_params['epoch_days']
    in_tra = transit_mask(t, P, Tdur, t0)
    ax.plot(t[in_tra], flux_resid[in_tra], marker='.', c='red',  markersize=2, linewidth=0)

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Detrended Flux")
    ax.set_title("Detrended Flux (Residuals)")

def plot_phase_folded_best(ax, best_model, best_params):
    """
    Plot the phase-folded recovered signal on the provided Axes.
    The best_model['time'] and best_model['flux_resid'] are folded using best_params['period'].
    """

    t = np.array(best_model['time'])
    flux_resid = np.array(best_model['flux_resid'])

    t0 = best_params['epoch_days']
    period = best_params['period']
    phase = ( (t-t0) % period) / period
    phase[phase > 0.5] -= 1.0  # shift phase to [-0.5, 0.5]
    phase_ingr = - 0.5 * (best_params['duration_hr']/24)/period # 0.  # let time = t0 above
    phase_egr  = 0.5 * (best_params['duration_hr']/24)/period

    ax.plot(phase, flux_resid, 'k.', markersize=2)
    ax.set_xlabel("Phase")
    ax.set_ylabel("Detrended Flux")
    ax.set_title("Phase-Folded Recovered Signal")
    # Highlight the transit region using best_params (epoch and duration are in phase units)
    ax.axvspan(
        phase_ingr,
        phase_egr,
        color='red', alpha=0.1
    )
    
def plot_summary_text(ax, best_params, known_params=None):
    """
    Plot a text summary of the best pbls_search results on the provided Axes.
    """
    period = best_params['period']
    t0 = best_params['epoch_days']
    duration_hr = best_params['duration_hr']
    depth = best_params['depth']
    snr = best_params['snr']
    
    # Convert phase to days for epoch and transit duration.
    duration_days = duration_hr * 24
    duration = duration_days / period
    depth_ppt = depth * 1000
    
    summary = (
        f"Best pbls_search Results:\n"
        f"Period: {period:.3f} days\n"
        f"t0: {t0:.3f} \n"
        f"Duration: {duration_hr:.1f} hours\n"
        f"Depth: {depth_ppt:.1f} ppt\n"
        f"SNR: {snr:.1f}"
    )
    if known_params is not None:
        known_period = known_params['period']
        LS_Prot = known_params['LS_Prot']
        summary += f"\nKnown P: {known_period:.3f} days"
        summary += f"\nLS Prot: {LS_Prot:.3f} days"

    ax.text(0.05, 0.95, summary, transform=ax.transAxes,
            fontsize=12, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    ax.axis('off')

def plot_summary_figure(time, flux, periods, power, best_params, best_model, post_power=None, known_params=None):
    """
    Create a summary figure with the following panels:
      A: Raw light curve (time vs flux)
      B: Periodogram (trial periods vs detection statistic)
      C: Best-model raw data (best_model['time'] and best_model['flux'] with best_model['model_flux'] underplotted)
      D: Detrended flux (best_model['flux_resid'] vs best_model['time'])
      E: Phase-folded recovered signal (fold best_model['time'] and best_model['flux_resid'] using best_params)
      F: Text summary of best pbls_search results
    
    Optionally, include the periodogram pre- and post-processing.
    """

    if post_power is None:
        mosaic = """
                 AAAAAA
                 BBBBBB
                 CCCCCC
                 DDEEFF
                 DDEEFF
                 """.strip()
    else:
        mosaic = """
                 AAAAAAAA
                 BBBBBBBB
                 CCCCCCCC
                 DDGGEEFF
                 DDGGEEFF
                 """.strip()
        
    try:
        from aesthetic.plot import set_style
        set_style("science")
    except:
        # silently ignore if aesthetic is not installed
        pass

    fig, axd = plt.subplot_mosaic(mosaic, figsize=(14, 10))
    
    # Panel A: Raw light curve
    plot_raw_light_curve(axd['A'], time, flux)
    
    # Panel B: Periodogram
    plot_periodogram(axd['D'], periods, power)
    
    # Panel C: Best-model raw data
    plot_best_model(axd['B'], best_model)
    
    # Panel D: Detrended flux (residuals)
    plot_detrended_flux(axd['C'], best_model, best_params)

    tmin, tmax = np.nanmin(time), np.nanmax(time)
    for ax in [axd['A'], axd['B'], axd['C']]:
        ax.set_xlim((tmin, tmax))
    
    # Panel E: Phase-folded recovered signal
    plot_phase_folded_best(axd['E'], best_model, best_params)
    
    # Panel F: Text summary of best pbls_search results
    plot_summary_text(axd['F'], best_params, known_params=known_params)

    if post_power is not None:
        # Panel B: Periodogram
        plot_periodogram(axd['G'], periods, post_power)

    
    plt.tight_layout()
    return fig


def plot_pbls_coeffs(pbls_result, known_params, png_path):
    """
    As-implemented, for each period this function takes the coefficients from
    each window of the highest-SNR model, averages them, and constructs a
    "penalty" (L1-norm analog) to weight against solutions for which all the
    coefficients are far from zero.

    This is a totally made-up heuristic, and should be revisited before
    implementing it in any kind of real pipeline.
    """

    result = pbls_result
    Porb, Prot = known_params['orbital_period'], known_params['Prot']
    
    coeff_summstat = np.array([result['coeffs'][i].mean(axis=0) for i in range(len(result['coeffs']))])
    # optional...
    #coeff_summstat = np.array([result['coeffs'][i].sum(axis=0) for i in range(len(result['coeffs']))])

    scales = [
        (np.nanmax(np.abs(coeff_summstat[:,i])) - np.nanmin(np.abs(coeff_summstat[:,i])))
        /
        (np.nanmax(result['power']) - np.nanmin(result['power']))
        for i in range(2)
    ]
    penalty = (
        0.5 * np.abs(coeff_summstat[:,1]) / scales[1]
        +
        0.5 * np.abs(coeff_summstat[:,0]) / scales[0]
    )

    plt.close("all")
    mosaic = """
            AAAAAA..
            BBBBBBDD
            CCCCCCEE
            FFFFFF..
            GGGGGG..
            """.strip()
    fig, axs = plt.subplot_mosaic(mosaic, figsize=(12, 10))
    axs['A'].plot(result['periods'], result['power'], lw=0.5, color='k')
    axs['B'].plot(result['periods'], np.abs(coeff_summstat[:,0]), lw=0.5, color='k')
    axs['C'].plot(result['periods'], np.abs(coeff_summstat[:,1]), lw=0.5, color='k')
    axs['F'].plot(result['periods'], penalty, lw=0.5, color='k')
    axs['G'].plot(result['periods'], result['power'] - penalty, lw=0.5, color='k')

    _axs = [axs['A'], axs['B'], axs['C'], axs['F'], axs['G']]

    for ax in _axs:
        ylim = ax.get_ylim()
        ax.vlines(Porb, ylim[0], ylim[1], color='C0', lw=0.5, ls='--', zorder=-1)
        ax.vlines(Prot, ylim[0], ylim[1], color='C1', lw=0.5, ls=':', zorder=-1)
        ax.set_ylim(ylim)

    axs['A'].set_ylabel('Power')
    axs['B'].set_ylabel('|Quad coeff|')
    axs['C'].set_ylabel('|Lin coeff|')
    axs['F'].set_ylabel('Penalty')
    axs['G'].set_ylabel('Power - Penalty')
    axs['G'].set_xlabel('Period (days)')

    axs['D'].hist(np.abs(coeff_summstat[:,0]), bins=100, color='k', histtype='step')
    axs['D'].set_yscale('log')
    axs['E'].hist(np.abs(coeff_summstat[:,1]), bins=100, color='k', histtype='step')
    axs['E'].set_yscale('log')
    axs['G'].set_ylim([0, np.nanmax(result['power'])])
    fig.tight_layout()
    fig.savefig(png_path, dpi=300, bbox_inches='tight')