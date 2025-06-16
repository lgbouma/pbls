import numpy as np

def variablewindow_flatten(
    x: np.ndarray,
    y: np.ndarray,
    method: str = 'trim_mean',
    window_length=None,
    edge_cutoff: float = 0.,
    break_tolerance: float = 0.5,
    return_trend: bool = True,
    proportiontocut: float = 0.1
):
    """
    Like wotan.flatten but allows window_length to be an array of per-point widths.
    """
    N = len(x)
    # build per-point window widths
    if np.isscalar(window_length):
        wld = np.full(N, window_length)
    else:
        wld = np.asarray(window_length)
        if wld.shape != x.shape:
            raise ValueError("window_length must be scalar or same shape as x")
    trend = np.zeros(N)
    for i in range(N):
        half = wld[i] / 2
        mask = np.abs(x - x[i]) <= half
        vals = y[mask]
        if method == 'trim_mean':
            n = len(vals)
            k = int(np.floor(proportiontocut * n))
            if 2*k >= n:
                # too much trimming → simple mean
                trend[i] = np.nanmean(vals)
            else:
                s = np.sort(vals)
                trend[i] = np.mean(s[k:n-k])
        else:
            raise NotImplementedError(f"method {method} not implemented")
    flat = y - trend
    if return_trend:
        return flat, trend
    return flat
