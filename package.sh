#!/bin/bash
# 
# This script makes the environments needed to run `pbls` on OSG infrastructure.
# It is a wrapper to `_package.sh`.
#
# Usage (from standard outer node bash): `./package.sh`

# Path to the Singularity container image
IMAGE="/cvmfs/singularity.opensciencegrid.org/opensciencegrid/osgvo-ubuntu-20.04:latest"

# Commands to run inside the container (separated by spaces)
COMMANDS="./_package.sh"

# Enter the container and execute the commands
singularity exec $IMAGE /bin/bash -c "$COMMANDS"
