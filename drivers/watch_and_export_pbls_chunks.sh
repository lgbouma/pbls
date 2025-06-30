#!/usr/bin/env bash
#
# watch_and_export_pbls_chunks.sh
#
# Monitors PBLS chunk‐output tar files and, once all chunks are present,
# rsyncs them to the remote server and cleans up local copies.
#
# Usage:
#   watch_and_export_pbls_chunks.sh [path/to/debug_jobs.joblist]
# Example:
#   ./watch_and_export_pbls_chunks.sh debug_jobs.joblist
#

set -euo pipefail

# Usage and input
joblist_path="${1:-debug_jobs.joblist}"
if [[ ! -f "$joblist_path" ]]; then
  echo "ERROR: joblist file not found: $joblist_path" >&2
  echo "Usage: $0 path/to/debug_jobs.joblist" >&2
  exit 1
fi

# read first line to get reference star_id and total chunks
IFS=',' read -r star_id _ N_total_chunks < "$joblist_path"

# verify all lines agree on star_id and N_total_chunks
while IFS=',' read -r sid idx ntotal; do
  if [[ "$sid" != "$star_id" ]]; then
    echo "ERROR: mismatched star_id in joblist: expected $star_id, got $sid" >&2
    exit 1
  fi
  if [[ "$ntotal" != "$N_total_chunks" ]]; then
    echo "ERROR: mismatched N_total_chunks: expected $N_total_chunks, got $ntotal" >&2
    exit 1
  fi
done < "$joblist_path"

# define result directory and remote target
result_dir="/ospool/ap21/data/ekul/pbls_results/${star_id}"
pattern="${result_dir}/joboutput_${star_id}_*_${N_total_chunks}.tar.gz"
remote="luke@wh2.caltech.edu:/ar0/RECEIVING/"

# wait until all chunks have produced a .tar
echo "Waiting for $N_total_chunks chunks of $star_id..."
while true; do
  count=$(ls $pattern 2>/dev/null | wc -l)
  if [[ "$count" -eq "$N_total_chunks" ]]; then
    echo "All $count/$N_total_chunks files present."
    break
  fi
  echo "  $count/$N_total_chunks, retrying in 60s..."
  sleep 60
done

# sync results
echo "Transferring files to $remote"
rsync -av $pattern "$remote"

echo "Done."
