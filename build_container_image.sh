#!/bin/bash
# Build the Apptainer container image for Python 3.11.
# Name it with a short random hash because OSG's auto-caching of container
# images results in version conflicts when jobs are run across the grid.
# Auto-updates `condor_submit.sub` with the new hash.

# Generate a 6-character hex hash
HASH=$(openssl rand -hex 3)
SIF_NAME="python_311_${HASH}.sif"

# Clean up any previous images matching the pattern
rm -f python_311_*.sif "$DATA"/python_311_*.sif

# Build and copy
apptainer build "${SIF_NAME}" python_311.def
cp "${SIF_NAME}" "$DATA/."

# Update python environment name line in condor submission scripts and make backups.
sed -i.bak -E \
  "s#\+SingularityImage = \".*\"#\+SingularityImage = \"osdf:///ospool/ap21/data/ekul/${SIF_NAME}\"#" \
  drivers/condor_submit.sub
sed -i.bak -E \
  "s#\+SingularityImage = \".*\"#\+SingularityImage = \"osdf:///ospool/ap21/data/ekul/${SIF_NAME}\"#" \
  drivers/scatter_single_pbls.sub
sed -i.bak -E \
  "s#python_311_[[:alnum:]]+\.sif#${SIF_NAME}#g" \
  drivers/run_pbls_mask.sh

echo
echo "Built ${SIF_NAME}, copied to \$DATA/, and updated condor submit scripts (and shell wrappers)."
echo "Backups of originals also written."
echo

echo
echo "Python 3.11 container image ${SIF_NAME} built and copied to $DATA."
echo