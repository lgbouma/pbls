#!/bin/bash

# Unpack the envvironment (with the pbls package), and activate it
echo 'hi'

# Main Python script; run_pbls_chunk.py <star_id> <periodgrid_chunk_id> <N_total_chunks> <iter_ix>.
python3 run_pbls_chunk.py $1 $2 $3 $4

# Move and tarball output (log  files, pkl files, anything downloaded from
# MAST) to top level directory for condor to return.  Everything will be tar'd.
save_log=false
save_pkl=true

mkdir $_CONDOR_SCRATCH_DIR/joboutput_$1_$2_$3_$4

if [ "$save_log" = true ]; then
    mv /srv/.pbls_cache/*$1*$2*$3*$4*log $_CONDOR_SCRATCH_DIR/joboutput_$1_$2_$3_$4/.
fi
if [ "$save_pkl" = true ]; then
    mv /srv/.pbls_cache/*$1*$2*$3*$4*pkl $_CONDOR_SCRATCH_DIR/joboutput_$1_$2_$3_$4/.
fi

tar czf joboutput_$1_$2_$3_$4.tar.gz $_CONDOR_SCRATCH_DIR/joboutput_$1_$2_$3_$4
