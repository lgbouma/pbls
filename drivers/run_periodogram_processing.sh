#!/bin/bash

# Args: $(star_id) $(iter_ix)
# Example:
#   ./run_periodogram_processing.sh kplr006184894 0

echo 'Running the periodogram post-processing locally...'

# Transfer merged periodogram to where apptainer will see it.  Made by merge.sub.
cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_pbls_periodogram_iter$2.csv .

# Transfer the appropriate stage of light curve 
if [ "$2" -eq 0 ]; then
    cp /ospool/ap21/data/ekul/Kepler/"$1".tar.gz .
else
    prev_iter=$(( $2 - 1 ))
    cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/masked_lightcurves/"${1}_masked_lightcurve_iter${prev_iter}.csv" .
fi

# Run the periodogram post-processing to identify sharp peaks.
IMAGE=/ospool/ap21/data/ekul/python_311_e37d1d.sif
apptainer exec "${IMAGE}" python run_periodogram_processing.py $1 $2

# Move the newly-made processing periodogram to the results directory.
# because transfer_output_remaps doesn't work for local universe.
mv $1_merged_postprocessed_pbls_periodogram_iter$2.pkl /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_postprocessed_pbls_periodogram_iter$2.pkl
mv $1_merged_postprocessed_pbls_periodogram_iter$2.csv /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_postprocessed_pbls_periodogram_iter$2.csv
mv $1_pbls_pgproc*_iter$2.png /ospool/ap21/data/ekul/pbls_results/PROCESSING/viz/.

# Clean copied scratch.
rm ./$1_merged_pbls_periodogram_iter$2.csv
rm ./$1.tar.gz
if [ "$2" -gt 0 ]; then
    prev_iter=$(( $2 - 1 ))
    prev_file="${1}_masked_lightcurve_iter${prev_iter}.csv"
    if [ -f "$prev_file" ]; then
        rm "$prev_file"
        echo "Removed (local) previous masked light curve: $prev_file"
    fi
fi