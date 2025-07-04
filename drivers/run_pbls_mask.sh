#!/bin/bash

# Argument order: $(star_id) $(iter_ix) $(threshold) $(maxiter)

echo 'Running the masking locally...'

# Transfer merged periodogram to where apptainer will see it.
cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_pbls_periodogram_iter$2.pkl .

# Ditto light curve 
cp /ospool/ap21/data/ekul/Kepler/$1.tar.gz .

# TODO TODO TODO FIXME LEFT OFF HERE!

IMAGE=/ospool/ap21/data/ekul/python_311_3f829b.sif

apptainer exec "${IMAGE}" python run_pbls_mask.py $1 $2 $3 $4

# Clean copied scratch.
rm ./$1_merged_pbls_periodogram_iter$2.pkl
rm ./$1.tar.gz

# Move the masked light curve to the results directory.
# because transfer_output_remaps doesn't work for local universe.
mv $1_masked_lightcurve_iter$2.csv /ospool/ap21/data/ekul/pbls_results/PROCESSING/masked_lightcurves/$1_masked_lightcurve_iter$2.csv