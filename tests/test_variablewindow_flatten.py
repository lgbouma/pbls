import os
import numpy as np
from pbls.sliders import variablewindow_flatten
import matplotlib.pyplot as plt
from pbls.paths import TESTRESULTSDIR

def test_variablewindow_flatten_sine_alternating_windows():
    # synthetic sinusoid: period 0.5 d, 10 d baseline, 30 min cadence
    dt = 0.5 / 24
    x = np.arange(0, 10, dt)
    y = np.sin(2 * np.pi * x / 0.5)

    # alternating 2 d / 0.2 d windows in 2 d chunks
    window_length = np.where((np.floor(x / 2) % 2) == 0, 2.0, 0.2)

    flat, trend = variablewindow_flatten(
        x, y,
        method='trim_mean',
        window_length=window_length,
        return_trend=True,
        proportiontocut=0.1
    )

    # shapes and perfect reconstruction
    assert flat.shape == x.shape == trend.shape
    assert np.allclose(flat + trend, y, atol=1e-6)

    # produce plot of raw, trend, and detrended signals
    plt.figure()
    plt.plot(x, y, label='raw')
    plt.plot(x, trend - 2, label='trend')
    plt.plot(x, flat - 4, label='detrended')
    plt.xlabel('Time [d]')
    plt.ylabel('Signal')
    plt.legend()
    plt.title('Variable Window Flatten')
    plot_path = os.path.join(TESTRESULTSDIR, 'png', f"test_variablewindow_flatten.png")
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")

if __name__ == "__main__":
    test_variablewindow_flatten_sine_alternating_windows()