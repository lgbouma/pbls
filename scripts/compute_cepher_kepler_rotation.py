#!/usr/bin/env python3
"""
Batch Kepler rotation period analysis for CepHer targets.

What it does per KIC ID:
- Loads Kepler light curves via lightkurve (mission="Kepler").
- For each quarter, measures rotation period using astropy's Lomb–Scargle.
- Produces a per-target vetting plot with quarter-stacked scatter points.
- Writes a CSV caching the median rotation period and TEFF.

If a result CSV already exists for a KIC, that target is skipped.

Inputs:
- tab_supp_CepHer_X_Kepler.csv in the current directory (or provide via --csv).

Outputs (created under ./cepher_target_vetting/):
- KIC_{kicid}_vetplot.png
- KIC_{kicid}_prot.csv

Requirements: pandas, numpy, matplotlib, lightkurve, astropy
"""

from __future__ import annotations

import os
import sys
import warnings
from typing import Iterable, Optional, Tuple, Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from astropy.timeseries import LombScargle
from astropy.io import fits

try:
    import lightkurve as lk
except Exception as e:
    print("Error: lightkurve is required. Install via `pip install lightkurve`.", file=sys.stderr)
    raise


VET_DIR = os.path.join(os.getcwd(), "cepher_target_vetting")


def ensure_outdir(path: str = VET_DIR) -> None:
    os.makedirs(path, exist_ok=True)


def find_kepid_column(df: pd.DataFrame) -> str:
    """Guess the kepid column name in a flexible way."""
    priorities = [
        "kepid",
        "kic",
        "kicid",
        "kepler_id",
        "keplerid",
        "id",
    ]
    lower_map = {c.lower(): c for c in df.columns}
    for p in priorities:
        if p in lower_map:
            return lower_map[p]
    # fallback: any column containing 'kic'
    for lc, orig in lower_map.items():
        if "kic" in lc:
            return orig
    raise ValueError("Could not infer KIC ID column from CSV columns: " + ", ".join(df.columns))


def to_int_kepid(val) -> Optional[int]:
    try:
        if pd.isna(val):
            return None
        # handle floats stored as 12345.0
        ival = int(np.round(float(val)))
        if ival <= 0:
            return None
        return ival
    except Exception:
        return None


def extract_teff_from_lc(lc) -> Optional[float]:
    """Try to get TEFF from a LightCurve's metadata or its original FITS header."""
    # Common header keys
    for key in ("TEFF", "KEP_TEFF"):
        v = lc.meta.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    # Try to locate the original FITS file path in meta
    for key in ("FILENAME", "FILEPATH", "PATH", "FITSFILE"):
        fp = lc.meta.get(key)
        if isinstance(fp, (bytes, bytearray)):
            fp = fp.decode(errors="ignore")
        if isinstance(fp, str) and os.path.exists(fp):
            try:
                with fits.open(fp) as hdul:
                    hdr = hdul[0].header
                    for k in ("TEFF", "KEP_TEFF"):
                        v = hdr.get(k)
                        if v is not None:
                            return float(v)
            except Exception:
                pass
    return None


def ls_rotation_period(time: np.ndarray, flux: np.ndarray) -> Optional[float]:
    """Estimate rotation period (days) using Lomb–Scargle on a single quarter.

    Returns the best period in days, or None if it cannot be measured.
    """
    # Clean NaNs
    m = np.isfinite(time) & np.isfinite(flux)
    t = np.array(time[m], dtype=float)
    y = np.array(flux[m], dtype=float)
    if t.size < 10:
        return None
    # Detrend/normalize lightly to help LS
    y = y - np.nanmedian(y)

    baseline = np.nanmax(t) - np.nanmin(t)
    if not np.isfinite(baseline) or baseline <= 1.0:  # need at least ~1 day baseline
        return None

    # Period search range: 0.1 day up to ~90% of the baseline, capped at 90 days
    min_period = 0.1
    max_period = float(min(0.9 * baseline, 90.0))
    if max_period <= min_period:
        return None

    fmin = 1.0 / max_period
    fmax = 1.0 / min_period

    # Reasonable resolution for per-quarter search
    nfreq = int(5000)
    freq = np.linspace(fmin, fmax, nfreq)

    try:
        ls = LombScargle(t, y)
        power = ls.power(freq)
        if not np.any(np.isfinite(power)):
            return None
        best = float(1.0 / freq[np.nanargmax(power)])
        if not np.isfinite(best):
            return None
        return best
    except Exception:
        return None


def analyze_kic(kepid: int) -> None:
    ensure_outdir(VET_DIR)
    out_csv = os.path.join(VET_DIR, f"KIC_{kepid}_prot.csv")
    out_png = os.path.join(VET_DIR, f"KIC_{kepid}_vetplot.png")

    if os.path.exists(out_csv):
        print(f"KIC {kepid}: cached CSV exists; skipping.")
        return

    target = f"KIC {kepid}"
    print(f"KIC {kepid}: searching Kepler light curves…")

    try:
        sr = lk.search_lightcurve(target, mission="Kepler", exptime='long')
    except Exception as e:
        print(f"KIC {kepid}: search failed: {e}")
        return

    if sr is None or len(sr) == 0:
        print(f"KIC {kepid}: no light curves found.")
        return

    # Download all using default lightkurve cache
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            lcc = sr.download_all()
        except Exception as e:
            print(f"KIC {kepid}: download failed: {e}")
            return

    if lcc is None or len(lcc) == 0:
        print(f"KIC {kepid}: no light curves after download.")
        return

    # Sort by quarter if available for a cleaner plot
    def quarter_key(lc):
        q = getattr(lc, "quarter", None)
        if q is None:
            q = lc.meta.get("QUARTER")
        try:
            return int(q)
        except Exception:
            return 9999

    lcs = sorted(list(lcc), key=quarter_key)

    # TEFF from the first available LC
    teff = extract_teff_from_lc(lcs[0])

    # Analysis per quarter
    q_labels: List[str] = []
    q_prots: List[float] = []
    quarters: List[Optional[int]] = []

    # Plot setup
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    y_offset = 0.0

    for idx, lc in enumerate(lcs, start=1):
        # Prefer PDCSAP flux when available
        try:
            work_lc = lc.remove_nans()
        except Exception:
            work_lc = lc

        # Extract arrays; lightkurve time may be an astropy Time-like
        try:
            t = np.asarray(work_lc.time.value, dtype=float)
        except Exception:
            # fallback if time is already ndarray
            t = np.asarray(work_lc.time, dtype=float)
        try:
            f = np.asarray(work_lc.flux.value, dtype=float)
        except Exception:
            f = np.asarray(work_lc.flux, dtype=float)

        if t.size < 10 or f.size < 10:
            continue

        # Lomb–Scargle period for this quarter
        prot = ls_rotation_period(t, f)
        if prot is not None and np.isfinite(prot):
            q_prots.append(float(prot))
        else:
            q_prots.append(np.nan)

        # Quarter label (if available)
        q = getattr(lc, "quarter", None)
        if q is None:
            q = lc.meta.get("QUARTER")
        try:
            qint: Optional[int] = int(q)
        except Exception:
            qint = None
        quarters.append(qint)
        q_label = f"Q{qint:02d}" if qint is not None else f"Q{idx:02d}"
        q_labels.append(q_label)

        # Prepare plotting: offset rows, time from quarter start
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x = t - np.nanmin(t)
            f_norm = (f - np.nanmedian(f))
            # Scale/offset row to avoid overlap
            row_height = 3.5 * float(np.nanstd(f_norm)) if np.isfinite(np.nanstd(f_norm)) else 1.0
            y = f_norm + y_offset
            ax.scatter(x, y, s=1, alpha=0.8, rasterized=True)
            # Add small label at the left
            try:
                ax.text(0.02 * np.nanmax(x), y_offset + 0.8 * row_height, q_label, fontsize=8)
            except Exception:
                pass
            y_offset -= row_height

    # Compute median Prot ignoring NaNs
    prots = np.array(q_prots, dtype=float)
    median_prot = float(np.nanmedian(prots)) if np.any(np.isfinite(prots)) else np.nan

    # Finalize plot
    ax.set_xlabel("Days from quarter start")
    ax.set_ylabel("Flux (offset rows)")
    title_prot = f"Prot={median_prot:.2f} d" if np.isfinite(median_prot) else "Prot=NaN"
    ax.set_title(f"KIC {kepid}  {title_prot}")
    try:
        fig.savefig(out_png, dpi=200)
    finally:
        plt.close(fig)

    # Write cache CSV
    result = {
        "kepid": kepid,
        "teff": teff if (teff is None or np.isfinite(teff)) else None,
        "prot_median_days": median_prot if np.isfinite(median_prot) else None,
        "n_quarters": int(np.sum(np.isfinite(prots))),
        "prots_by_quarter_days": ";".join(
            [f"{p:.5f}" if np.isfinite(p) else "" for p in prots]
        ),
        "quarters": ";".join([str(q) if q is not None else "" for q in quarters]),
    }
    df_out = pd.DataFrame([result])
    df_out.to_csv(out_csv, index=False)
    print(f"KIC {kepid}: wrote {out_csv} and {out_png}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Measure Kepler rotation periods for CepHer targets.")
    parser.add_argument(
        "--csv",
        default="tab_supp_CepHer_X_Kepler.csv",
        help="Input CSV containing KIC IDs (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N targets (for quick tests)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not os.path.exists(args.csv):
        print(f"Input CSV not found: {args.csv}", file=sys.stderr)
        return 2

    df = pd.read_csv(args.csv)
    kcol = find_kepid_column(df)
    kepids = [to_int_kepid(v) for v in df[kcol].values]
    kepids = [k for k in kepids if k is not None]

    if args.limit is not None:
        kepids = kepids[: args.limit]

    if len(kepids) == 0:
        print("No valid KIC IDs found in the CSV.", file=sys.stderr)
        return 1

    print(f"Found {len(kepids)} KIC IDs in {args.csv}")
    for i, kic in enumerate(kepids, start=1):
        print(f"[{i}/{len(kepids)}]")
        try:
            analyze_kic(kic)
        except KeyboardInterrupt:
            print("Interrupted by user.")
            return 130
        except Exception as e:
            print(f"KIC {kic}: unexpected error: {e}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

