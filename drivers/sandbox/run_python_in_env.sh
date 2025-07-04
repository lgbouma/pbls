#!/usr/bin/env bash

cp /ospool/ap21/data/ekul/pbls_results/PROCESSING/merged_periodograms/kplr006184894_merged_pbls_periodogram_iter0.pkl .

IMAGE=/ospool/ap21/data/ekul/python_311_151551.sif

apptainer exec "${IMAGE}" python python_in_env.py "$1"
