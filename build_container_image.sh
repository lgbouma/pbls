#!/bin/bash
# Build the Apptainer container image for Python 3.11.

if [ -f python_311.sif ]; then
    rm python_311.sif
fi

apptainer build python_311.sif python_311.def

if [ -f python_311.sif ]; then
    cp python_311.sif $DATA/.
fi

echo ""
echo "Python 3.11 container image built and copied to $DATA."
echo ""