#!/bin/bash

#arguments           = $(star_id) $(iter_ix) $(threshold) $(maxiter)

echo 'Running the masking locally...'

# Transfer merged periodogram to where apptainer will see it.
cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/$1_merged_pbls_periodogram_iter$2.pkl .

# Ditto light curve 
cp /ospool/ap21/data/ekul/Kepler/$1.tar.gz .

# TODO TODO TODO FIXME LEFT OFF HERE!

IMAGE=/ospool/ap21/data/ekul/python_311_f3c839.sif

apptainer exec "${IMAGE}" python run_pbls_mask.py $1 $2 $3 $4

# Output masked CSV light curve file is written by run_pbls_mask.py to top level
# directory for condor to return.  Nothing required here, but remap in .sub
# script.

# Clean copied scratch.
rm ./$1_merged_pbls_periodogram_iter$2.pkl
rm ./$1.tar.gz