#!/usr/bin/env bash
# load_test.sh — bombardier scenarios for microblog.rafaelviana.com
set -euo pipefail

# --------- Config ---------
BASE="${BASE:-https://microblog.rafaelviana.com}" # override: BASE=https://ip ./load_test.sh
OUT="bombardier_$(date +%Y%m%d_%H%M%S).log"
DUR_SHORT="${DUR_SHORT:-30s}"
DUR_LONG="${DUR_LONG:-60s}"

# Target rates (RPS) for “Reddit pages”
PAGE4_R=1   # ~5k/day (bursty)
PAGE2_R=10  # ~50k/day
PAGE1_R=100 # ~500k/day

# Concurrency per level
PAGE4_C=20
PAGE2_C=60
PAGE1_C=200
# --------------------------

bar() { printf '\n%s\n' "============================================================"; }

health() {
  echo "Health check @ ${BASE}/health"
  curl -fsS "${BASE}/health" || {
    echo "Health check FAILED"
    exit 1
  }
  echo "ok"
}

run_case() {
  local label="$1"
  shift
  echo -e "\n### ${label}" | tee -a "$OUT"
  echo "Command: $*" | tee -a "$OUT"
  "$@" | tee -a "$OUT"
}

# Mixed: run two bombardiers in parallel (90% GET /, 10% POST /add_raw)
run_mixed() {
  local label="$1" rps_total="$2" conc="$3" dur="$4"
  local rps_reads=$((rps_total * 90 / 100))
  local rps_writes=$((rps_total - rps_reads))
  [ "$rps_reads" -lt 1 ] && rps_reads=1
  [ "$rps_writes" -lt 1 ] && rps_writes=1

  echo -e "\n### ${label} (mixed 90% GET /, 10% POST /add_raw)" | tee -a "$OUT"
  echo "Reads RPS: ${rps_reads}, Writes RPS: ${rps_writes}, Concurrency: ${conc}, Duration: ${dur}" | tee -a "$OUT"

  (bombardier -r "${rps_reads}" -c "${conc}" -d "${dur}" "${BASE}/" | sed 's/^/[reads] /') | tee -a "$OUT" &
  PID1=$!
  (bombardier -r "${rps_writes}" -c $((conc / 4 + 1)) -d "${dur}" \
    -m POST -b "content=hello_${RANDOM}" -H "Content-Type: application/x-www-form-urlencoded" \
    "${BASE}/add_raw" | sed 's/^/[writes] /') | tee -a "$OUT" &
  PID2=$!
  wait $PID1
  wait $PID2
}

echo "Bombardier load test @ $(date)" | tee "$OUT"
echo "Target base: ${BASE}" | tee -a "$OUT"
bar
health | tee -a "$OUT"
bar

# A) READ — homepage
run_case "READ / (Page 4)" bombardier -r "${PAGE4_R}" -c "${PAGE4_C}" -d "${DUR_SHORT}" "${BASE}/"
run_case "READ / (Page 2)" bombardier -r "${PAGE2_R}" -c "${PAGE2_C}" -d "${DUR_LONG}" "${BASE}/"
run_case "READ / (Page 1)" bombardier -r "${PAGE1_R}" -c "${PAGE1_C}" -d "${DUR_LONG}" "${BASE}/"

# B) SEARCH — indexed read
run_case "SEARCH /search?q=fastapi (Page 2)" bombardier -r "${PAGE2_R}" -c "${PAGE2_C}" -d "${DUR_LONG}" "${BASE}/search?q=fastapi"
run_case "SEARCH /search?q=fastapi (Page 1)" bombardier -r "${PAGE1_R}" -c "${PAGE1_C}" -d "${DUR_LONG}" "${BASE}/search?q=fastapi"

# C) WRITE — POST /add_raw (no redirect; clean 2xx/204)
run_case "WRITE POST /add_raw (Page 2-ish, 5 rps)" bombardier -r 5 -c 40 -d "${DUR_LONG}" -m POST \
  -b "content=hello_${RANDOM}" -H "Content-Type: application/x-www-form-urlencoded" "${BASE}/add_raw"
run_case "WRITE POST /add_raw (Page 1-ish, 20 rps)" bombardier -r 20 -c 80 -d "${DUR_LONG}" -m POST \
  -b "content=hello_${RANDOM}" -H "Content-Type: application/x-www-form-urlencoded" "${BASE}/add_raw"

# D) MIXED — 90% reads, 10% writes
run_mixed "MIXED (Page 2 total ~10 rps)" 10 "${PAGE2_C}" "${DUR_LONG}"
run_mixed "MIXED (Page 1 total ~100 rps)" 100 "${PAGE1_C}" "${DUR_LONG}"

bar
echo "Done. Results saved to ${OUT}"
