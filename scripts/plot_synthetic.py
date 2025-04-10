import os
import numpy as np
from STR.synthetic import generate_transit_rotation_light_curve
from STR.paths import TESTRESULTSDIR

import matplotlib.pyplot as plt

def test_generate_transit_rotation_light_curve():
    # Define time array
    total_time = 30.0  # days
    cadence = 0.01     # days
    time = np.arange(0, total_time, cadence)

    # Define transit parameters
    transit_dict = {
        'period': 3.14,       # days
        't0': 2.5,           # central transit time
        'depth': 0.02,       # fractional flux drop
        'duration': 0.1      # days
    }

    # Define rotation parameters
    rotation_dict = {
        'prot': 10.0,        # stellar rotation period in days
        'a1': 0.005,         # amplitude of primary sinusoid
        'a2': 0.002,         # amplitude of secondary sinusoid
        'phi1': 0.0,         # phase offset for primary sinusoid
        'phi2': np.pi / 4    # phase offset for secondary sinusoid
    }

    # Generate the light curve
    flux = generate_transit_rotation_light_curve(time, transit_dict, rotation_dict)

    # Assert the output shape matches the input time array
    assert flux.shape == time.shape, "Flux array shape does not match time array shape."

    # Plot the light curve
    plt.figure(figsize=(10, 6))
    plt.plot(time, flux, label="Synthetic Light Curve", color="blue", lw=0.5)
    plt.xlabel("Time (days)")
    plt.ylabel("Flux")
    plt.title("Synthetic Light Curve with Transit and Stellar Rotation")
    plt.legend()
    plt.grid()

    # Save the plot
    plot_path = os.path.join(TESTRESULTSDIR, "test_generate_transit_rotation_light_curve.png")
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    # Assert that the plot file was created
    assert os.path.exists(plot_path), f"Plot was not saved to {plot_path}"

if __name__ == "__main__":
    test_generate_transit_rotation_light_curve()