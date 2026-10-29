#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
TRACE_MAP="${TRACE_MAP:-$OUT/phase6-v2-partition-trace-map.json}"
TRACE_LOG="${TRACE_LOG:-$HOME/phase6-v2-nbd-trace.jsonl}"
HOST_REPORT="${HOST_REPORT:-$OUT/phase6-v2-tracer-host-audit.txt}"
BIND="${BIND:-0.0.0.0}"
PORT="${PORT:-10810}"
SERVER="$ROOT/scripts/v2/nbd_partition_trace_server.py"
PREFLIGHT="$ROOT/scripts/v2/phase6_v2_real_preflight.sh"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for f in "$DISK" "$TRACE_MAP" "$HOST_REPORT" "$SERVER" "$PREFLIGHT"; do
    [[ -f "$f" ]] || fail "required Phase6 V2 traced-server input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS$' "$HOST_REPORT" || \
    fail "6V2-C tracer host gate has not passed; refusing real-device export"

# Refuse to expose the disk to hardware unless the exact continuation image,
# wrapper, accepted/traced servers, and trace-map still match the A/B/C reports.
bash "$PREFLIGHT"

echo

echo "Diskless v2 Phase6 Audit-V2 traced single-NBD export"
echo "  bind: $BIND:$PORT"
echo "  disk: $DISK"
echo "  trace map: $TRACE_MAP"
echo "  trace log: $TRACE_LOG"
echo "  mode: read-write"
echo "  acceptance: host-side observation only; no Nexus logger"
echo "  stderr: merged into stdout so tee preserves transport-error summaries"
echo

# Merge stderr into stdout here so a caller using `... | tee server.txt` cannot
# lose the exception-time phase/request/last-request summary again.  This does
# not change the NBD protocol path or traced-server bytes.
exec python3 "$SERVER" \
    --name phase6-v2 \
    --bind "$BIND" \
    --port "$PORT" \
    --trace-map "$TRACE_MAP" \
    --trace-log "$TRACE_LOG" \
    "$DISK" 2>&1
