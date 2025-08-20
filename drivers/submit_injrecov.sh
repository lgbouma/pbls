#!/bin/bash

# Purpose:
#   Submit and manage injection-recovery DAG jobs on OSG.
#   For a given star, generate random injection parameters per run,
#   create a DAG via generate_iterative_pbls_DAG.py, and submit
#   while keeping total jobs under the queue cap.
#
# Usage:
#
#   ./submit_injrecov.sh --star kplr008653134 \
#       [--n 20] [--ntotchunks 200] [--snr 8] [--maxiter 2]
#
#   ./submit_injrecov.sh --star kplr008653134 &> injrecov_kplr008653134.log &

set -euo pipefail

# Timestamped logging helpers
log() { echo "$(date -Is) $*"; }
log_err() { echo "$(date -Is) $*" >&2; }

STAR_ID_BASE=""
N_INJRECOVS=20 # Number of injection recovery experiments to run for this star.
NTOTCHUNKS=200 # Do not lower below 200 at risk of medium runtime cap.
SNRTHRESH=8
MAXITER=2 # Number of PBLS iterations per experiment.
LOG_FILE="injrecov_submissions.csv" # Pipe-delimited CSV log

function usage() {
  log_err "Usage: $0 --star <kplr#########> [--n 50] [--ntotchunks 200] [--snr 8] [--maxiter 2]"
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --star)
      STAR_ID_BASE="$2"; shift 2 ;;
    --n)
      N_INJRECOVS="$2"; shift 2 ;;
    --ntotchunks)
      NTOTCHUNKS="$2"; shift 2 ;;
    --snr)
      SNRTHRESH="$2"; shift 2 ;;
    --maxiter)
      MAXITER="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      log_err "Unknown argument: $1"
      usage; exit 1 ;;
  esac
done

if [[ -z "$STAR_ID_BASE" ]]; then
  log_err "Error: --star is required (e.g., --star kplr008653134)."
  usage
  exit 1
fi

# Ensure CSV log exists with header
ensure_log() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "STAR_ID|P|Rp|T|E|first_submission_time|resubmission_times" > "$LOG_FILE"
  fi
}

# Append a new submission row if STAR_ID not already present
log_new_submission() {
  local sid="$1" p="$2" rp="$3" t="$4" e="$5" tfirst="$6"
  if ! grep -Fq "^${sid}|" "$LOG_FILE"; then
    printf "%s|%s|%s|%s|%s|%s|%s\n" "$sid" "$p" "$rp" "$t" "$e" "$tfirst" "" >> "$LOG_FILE"
  fi
}

# Append a resubmission timestamp to the row for STAR_ID
log_resubmission() {
  local sid="$1" tstamp="$2"
  local tmp
  tmp="${LOG_FILE}.tmp$$"
  awk -F'|' -v OFS='|' -v sid="$sid" -v ts="$tstamp" '
    NR==1 { print; next }
    $1==sid {
      if (NF<7) { $7 = ts }
      else if ($7=="" || $7=="\r") { $7 = ts }
      else { $7 = $7 "," ts }
    }
    { print }
  ' "$LOG_FILE" > "$tmp" && mv "$tmp" "$LOG_FILE"
}

# Generate random injection parameters and formatted star_id
gen_random() {
  python3 - "$STAR_ID_BASE" <<'PY'
import math, os, random, sys

star_base = sys.argv[1]

def log_uniform(low, high):
    u = random.uniform(math.log10(low), math.log10(high))
    return 10**u

def truncate(x, ndp):
    factor = 10**ndp
    return math.trunc(x * factor) / factor

def fmt_pstr(x, ndp):
    v = truncate(x, ndp)
    s = f"{v:.{ndp}f}"
    i, f = s.split('.')
    f = f.rstrip('0')
    if f == '':
        f = '0'
    return f"{i}p{f}"

# Draws per instructions
P = log_uniform(10**0.5, 10**1.5)  # days
Rp = log_uniform(1.0, 10.0)         # earth radii
T = random.uniform(1.0, 4.0)        # hours
E = random.uniform(0.0, P)          # days

pstr = fmt_pstr(P, 6)
rstr = fmt_pstr(Rp, 3)
tstr = fmt_pstr(T, 3)
estr = fmt_pstr(E, 5)

star_id = f"{star_base}_inject-P{pstr}-R{rstr}-T{tstr}-E{estr}"

print(f"P={P}")
print(f"RP={Rp}")
print(f"T={T}")
print(f"E={E}")
print(f"STAR_ID={star_id}")
PY
}

ensure_log
username=$(whoami)
declare -g -A RESCUE_SEEN=()
declare -g -a SUBMITTED_STAR_IDS=()

# Scan for new rescue files and re-submit the corresponding DAGs.
check_and_resubmit_rescues() {
  shopt -s nullglob
  # Only consider rescue files for STAR_IDs submitted by this script
  for sid in "${SUBMITTED_STAR_IDS[@]}"; do
    for resc in run_iterative_pbls_"${sid}".dag.rescue00?; do
      if [[ -z "${RESCUE_SEEN[$resc]:-}" ]]; then
        base_dag="${resc%.rescue00?}"
        log "Detected rescue file: $resc. Re-submitting $base_dag ..."
        # Do not fail the whole script if re-submit hiccups; retry next pass
        if condor_submit_dag "$base_dag"; then
          log_resubmission "$sid" "$(date '+%Y-%m-%d %H:%M:%S')"
        else
          log "Warning: re-submit failed for $base_dag; will retry on next scan."
        fi
        RESCUE_SEEN[$resc]=1
      fi
    done
  done
  shopt -u nullglob
}

for (( i=1; i<=N_INJRECOVS; i++ )); do
  # Periodic rescue sweep before each new submission
  check_and_resubmit_rescues
  log "[injrecov $i/$N_INJRECOVS] Generating random properties..."
  mapfile -t lines < <(gen_random)
  # Export vars from Python output
  declare -A KV
  for line in "${lines[@]}"; do
    key="${line%%=*}"
    val="${line#*=}"
    KV[$key]="$val"
  done

  STAR_ID="${KV[STAR_ID]}"
  if [[ -z "$STAR_ID" ]]; then
    log_err "Failed to construct STAR_ID; aborting."
    exit 1
  fi

  log "Drawn: P=${KV[P]} d, Rp=${KV[RP]} Re, T=${KV[T]} hr, E=${KV[E]} d"
  log "STAR_ID: $STAR_ID"

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
    # While waiting, keep an eye on any new rescue files and resubmit them
    check_and_resubmit_rescues || log "Rescue resubmit sweep hiccup; continuing"
    job_count=$(condor_q | grep "Total for $username" | awk '{print $4}') || job_count=0
    if [[ -z "$job_count" ]]; then job_count=0; fi
  done

  log "Submitting DAG: $dag_file"
  if condor_submit_dag "$dag_file"; then
    # Log first submission
    log_new_submission "$STAR_ID" "${KV[P]}" "${KV[RP]}" "${KV[T]}" "${KV[E]}" "$(date '+%Y-%m-%d %H:%M:%S')"
    # Track this STAR_ID so future rescue scans only consider our submissions
    SUBMITTED_STAR_IDS+=("$STAR_ID")
  fi
  sleep 10
  # Quick rescue scan after submitting this DAG
  check_and_resubmit_rescues || log "Rescue resubmit sweep hiccup; continuing"
done

log "All $N_INJRECOVS injection-recovery DAGs submitted for star $STAR_ID_BASE."

# -----------------------------
# Post-submit monitoring loop
# -----------------------------

# Determine completion based on presence of NTOTCHUNKS err files in iter1
is_dag_complete() {
  local sid="$1"
  shopt -s nullglob
  local errs=("logs/${sid}/iter1"/*.err)
  shopt -u nullglob
  local cnt=${#errs[@]}
  if [[ "$cnt" -ge "$NTOTCHUNKS" ]]; then
    return 0
  else
    return 1
  fi
}

if [[ ${#SUBMITTED_STAR_IDS[@]} -gt 0 ]]; then
  # Copy to a working list of pending completions
  PENDING_STAR_IDS=("${SUBMITTED_STAR_IDS[@]}")
  log "Entering monitoring loop for ${#PENDING_STAR_IDS[@]} DAG(s) until completion..."

  # Relax error handling in the monitoring loop to guard
  # against transient failures in helper commands.
  set +e
  set +o pipefail
  while [[ ${#PENDING_STAR_IDS[@]} -gt 0 ]]; do
    # Resubmit any rescues that appeared; do not exit on hiccups
    check_and_resubmit_rescues || log "Rescue resubmit sweep hiccup; continuing"

    # Recompute pending list by filtering out completed DAGs
    NEW_PENDING=()
    for sid in "${PENDING_STAR_IDS[@]}"; do
      if is_dag_complete "$sid"; then
        log "DAG completed for $sid (>= $NTOTCHUNKS err files in logs/$sid/iter1)."
      else
        NEW_PENDING+=("$sid")
      fi
    done
    PENDING_STAR_IDS=("${NEW_PENDING[@]}")

    if [[ ${#PENDING_STAR_IDS[@]} -gt 0 ]]; then
      sleep 120
    fi
  done
  # Restore strict error handling
  set -euo pipefail
  log "All submitted DAGs have completed. Exiting monitor."
fi
