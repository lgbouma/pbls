#!/bin/bash

# Purpose:
#   Watch for and submit HTCondor rescue DAGs produced by the real (non-injection)
#   iterative PBLS runs. It detects files matching
#   run_iterative_pbls_kplr[0-9]{9}.dag.rescueXXX and submits the latest rescue DAG
#   per STAR_ID while keeping the total queue count below a cap, mirroring the
#   behavior of submit_cepher_real.sh. Logs each rescue submission.
#
# Behavior:
#   - For each STAR_ID with one or more rescue DAGs present, submit only the
#     highest-numbered rescue file (e.g., .rescue003 over .rescue002).
#   - Respects condor_q capacity (>= 8000 -> wait) and sleeps 10s between
#     submissions to avoid stampedes.
#   - Repeats until no unseen rescue files remain; then exits.
#
# Log:
#   - Pipe-delimited CSV: cepher_real_submissions_rescues.csv
#     Header: STAR_ID|rescue_file|submission_time

set -euo pipefail

log() { echo "$(date -Is) $*"; }
log_err() { echo "$(date -Is) $*" >&2; }

LOG_FILE="cepher_real_submissions_rescues.csv"

usage() {
  log_err "Usage: $0 [--log <path.csv>]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log)
      LOG_FILE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      log_err "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

ensure_log() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "STAR_ID|rescue_file|submission_time" > "$LOG_FILE"
  fi
}

already_logged() {
  local sid="$1" rfile="$2"
  grep -Fq "^${sid}|${rfile}|" "$LOG_FILE" 2>/dev/null || return 1
}

append_log() {
  local sid="$1" rfile="$2"
  printf "%s|%s|%s\n" "$sid" "$rfile" "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
}

ensure_log
username=$(whoami || true)

# Returns space-separated list of latest rescue DAG files (one per STAR_ID)
latest_rescue_files() {
  # Collect all rescue DAGs; if none, return empty
  local files
  # shellcheck disable=SC2012
  files=$(ls -1 run_iterative_pbls_kplr[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].dag.rescue[0-9][0-9][0-9] 2>/dev/null || true)
  if [[ -z "${files:-}" ]]; then
    return 0
  fi

  # Build mapping lines: STAR_ID rescue_num filename, then pick max per STAR_ID
  # Sort by STAR_ID, rescue_num numeric ascending; keep last per STAR_ID
  echo "$files" | awk 'NF>0{print $0}' \
    | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        # Extract STAR_ID and rescue number
        sid=$(echo "$f" | sed -E 's#^run_iterative_pbls_(kplr[0-9]{9})\.dag\.rescue([0-9]+)$#\1#')
        num=$(echo "$f" | sed -E 's#^run_iterative_pbls_kplr[0-9]{9}\.dag\.rescue([0-9]+)$#\1#')
        if [[ -n "$sid" && -n "$num" ]]; then
          printf "%s %d %s\n" "$sid" "$num" "$f"
        fi
      done \
    | sort -k1,1 -k2,2n \
    | awk 'BEGIN{prev=""; lastLine=""} {
             if ($1!=prev) { if (lastLine!="") print lastLine; prev=$1; }
             lastLine=$0
           } END{ if (lastLine!="") print lastLine }' \
    | awk '{print $3}'
}

wait_for_capacity() {
  local job_count
  job_count=$(condor_q | grep "Total for ${username}" | awk '{print $4}') || job_count=0
  [[ -z "$job_count" ]] && job_count=0
  log "condor_q: Total for ${username} = ${job_count} jobs"
  while [[ "$job_count" -ge 8000 ]]; do
    log "Queue at capacity (>=8000). Sleeping 60s..."
    sleep 60
    job_count=$(condor_q | grep "Total for ${username}" | awk '{print $4}') || job_count=0
    [[ -z "$job_count" ]] && job_count=0
  done
}

submitted_any=false
while true; do
  mapfile -t to_submit < <(latest_rescue_files || true)
  # Filter out those already logged
  filtered=()
  for rf in "${to_submit[@]}"; do
    [[ -z "${rf:-}" ]] && continue
    sid=$(echo "$rf" | sed -E 's#^run_iterative_pbls_(kplr[0-9]{9})\.dag\.rescue[0-9]+$#\1#')
    base=$(basename "$rf")
    if already_logged "$sid" "$base"; then
      continue
    fi
    filtered+=("$rf")
  done

  if [[ ${#filtered[@]} -eq 0 ]]; then
    if [[ "$submitted_any" == true ]]; then
      log "All rescue DAGs present have been submitted. Exiting."
    else
      log "No unsubmitted rescue DAGs found. Exiting."
    fi
    exit 0
  fi

  for rf in "${filtered[@]}"; do
    sid=$(echo "$rf" | sed -E 's#^run_iterative_pbls_(kplr[0-9]{9})\.dag\.rescue[0-9]+$#\1#')
    base=$(basename "$rf")
    log "Preparing submission for STAR_ID=$sid rescue=$base"
    wait_for_capacity
    log "Submitting rescue DAG: $rf"
    if condor_submit_dag "$rf"; then
      append_log "$sid" "$base"
      submitted_any=true
    else
      log_err "condor_submit_dag failed for $rf"
    fi
    # Same pacing as submit_cepher_real.sh
    sleep 10
  done
done
