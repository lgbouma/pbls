#!/bin/bash

# Purpose:
#   Submit real (non-injection) iterative PBLS DAG jobs on OSG.
#   Reads KIC IDs from a CSV (one per line), generates a DAG via
#   generate_iterative_pbls_DAG.py, and submits while keeping the
#   total job count under a queue cap. Logs each submission.
#
# Defaults:
#   - CSV file: cepher_x_kepler_prot_1-10_nquarters_geq_5.csv
#   - NTOTCHUNKS: 200
#   - SNRTHRESH: 8
#   - MAXITER: 3
#   - LOG_FILE: cepher_real_submissions.csv (pipe-delimited)

set -euo pipefail

# Timestamped logging helpers
log() { echo "$(date -Is) $*"; }
log_err() { echo "$(date -Is) $*" >&2; }

CSV_FILE="cepher_x_kepler_prot_1-10_nquarters_geq_5.csv"
NTOTCHUNKS=200
SNRTHRESH=8
MAXITER=3
LOG_FILE="cepher_real_submissions.csv" # Pipe-delimited CSV log

function usage() {
  log_err "Usage: $0 [--csv <path.csv>] [--ntotchunks 200] [--snr 8] [--maxiter 3] [--log <path.csv>]"
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --csv)
      CSV_FILE="$2"; shift 2 ;;
    --ntotchunks)
      NTOTCHUNKS="$2"; shift 2 ;;
    --snr)
      SNRTHRESH="$2"; shift 2 ;;
    --maxiter)
      MAXITER="$2"; shift 2 ;;
    --log)
      LOG_FILE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      log_err "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -f "$CSV_FILE" ]]; then
  log_err "Error: CSV file not found: $CSV_FILE"
  exit 1
fi

# Ensure CSV log exists with header
ensure_log() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "STAR_ID|first_submission_time" > "$LOG_FILE"
  fi
}

# Append a new submission row if STAR_ID not already present
log_new_submission() {
  local sid="$1" tfirst="$2"
  if ! grep -Fq "^${sid}|" "$LOG_FILE"; then
    printf "%s|%s\n" "$sid" "$tfirst" >> "$LOG_FILE"
  fi
}

ensure_log
username=$(whoami)

# Read KIC IDs (one per line) and submit
lineno=0
while IFS= read -r kic || [[ -n "$kic" ]]; do
  lineno=$((lineno+1))
  # Skip empty lines and comments
  if [[ -z "${kic//[[:space:]]/}" ]] || [[ "$kic" =~ ^# ]]; then
    continue
  fi

  STAR_ID="${kic}"
  log "[${lineno}] Preparing STAR_ID: $STAR_ID"

  log "Generating DAG for $STAR_ID ..."
  python3 generate_iterative_pbls_DAG.py \
    --ntotchunks "$NTOTCHUNKS" \
    --star_id "$STAR_ID" \
    --snrthreshold "$SNRTHRESH" \
    --maxiter "$MAXITER"

  dag_file="run_iterative_pbls_${STAR_ID}.dag"
  if [[ ! -f "$dag_file" ]]; then
    log_err "Expected DAG not found: $dag_file"
    exit 1
  fi

  # Check current job count and wait if at/above threshold
  job_count=$(condor_q | grep "Total for $username" | awk '{print $4}') || job_count=0
  if [[ -z "$job_count" ]]; then job_count=0; fi
  log "condor_q: Total for $username = $job_count jobs"

  while [[ "$job_count" -ge 8000 ]]; do
    log "Queue at capacity (>=8000). Sleeping 60s..."
    sleep 60
    job_count=$(condor_q | grep "Total for $username" | awk '{print $4}') || job_count=0
    if [[ -z "$job_count" ]]; then job_count=0; fi
  done

  log "Submitting DAG: $dag_file"
  if condor_submit_dag "$dag_file"; then
    log_new_submission "$STAR_ID" "$(date '+%Y-%m-%d %H:%M:%S')"
  fi

  # Small delay between submissions to avoid stampedes
  sleep 5
done < "$CSV_FILE"

log "All DAGs submitted from CSV: $CSV_FILE"

