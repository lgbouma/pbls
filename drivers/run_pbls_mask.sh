#!/bin/bash

# Args: $(star_id) $(iter_ix) $(threshold) $(maxiter)
# Example:
#   ./run_pbls_mask.sh kplr006184894 0 8 3

echo 'Running the masking locally...'

use_postprocessed_pg=true

# Derive base star ID (drops any "_inject-..." suffix via bash parameter expansion).
base_star_id="${1%%_inject-*}"

# Transfer the appropriate merged periodogram based on use_postprocessed_pg.
if [ "$use_postprocessed_pg" = true ]; then
    cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_postprocessed_pbls_periodogram_iter$2.pkl .
else
    cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_pbls_periodogram_iter$2.pkl .
fi

# Transfer the appropriate stage of light curve 
if [ "$2" -eq 0 ]; then
    cp /ospool/ap21/data/ekul/Kepler/"$base_star_id".tar.gz .
else
    prev_iter=$(( $2 - 1 ))
    cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/masked_lightcurves/"${1}_masked_lightcurve_iter${prev_iter}.csv" .
fi

# Run the masking to create the new masked light curve.
IMAGE=/ospool/ap21/data/ekul/python_311_8e738c.sif
apptainer exec "${IMAGE}" python run_pbls_mask.py $1 $2 $3 $4

# Move the newly-made masked light curve to the results directory.
# because transfer_output_remaps doesn't work for local universe.
mv $1_masked_lightcurve_iter$2.csv /ospool/ap21/data/ekul/pbls_results/PROCESSING/masked_lightcurves/$1_masked_lightcurve_iter$2.csv

# Clean copied scratch.
rm ./$1_merged_*pbls_periodogram_iter$2.pkl
if [ -f "./$base_star_id.tar.gz" ]; then
    rm "./$base_star_id.tar.gz"
fi
if [ "$2" -gt 0 ]; then
    prev_iter=$(( $2 - 1 ))
    prev_file="${1}_masked_lightcurve_iter${prev_iter}.csv"
    if [ -f "$prev_file" ]; then
        rm "$prev_file"
        echo "Removed (local) previous masked light curve: $prev_file"
    fi
fi