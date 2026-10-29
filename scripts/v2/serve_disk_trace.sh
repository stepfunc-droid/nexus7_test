#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
TRACE_MAP="${TRACE_MAP:-$OUT/phase6-r2-trace-map.json}"
TRACE_LOG="${TRACE_LOG:-$HOME/phase6-r2-nbd-trace.jsonl}"
BIND="${BIND:-0.0.0.0}"
PORT="${PORT:-10810}"

for f in "$DISK" "$TRACE_MAP"; do
    [[ -f "$f" ]] || { echo "ERROR: required trace input not found: $f" >&2; exit 1; }
done

rm -f "$TRACE_LOG"

echo "Phase6 R2/R3 traced single-NBD export"
echo "  bind: $BIND:$PORT"
echo "  disk: $DISK"
echo "  trace map: $TRACE_MAP"
echo "  trace log: $TRACE_LOG"
echo "  mode: read-write"
echo

exec python3 "$ROOT/scripts/v2/nbd_trace_server.py" \
    --bind "$BIND" \
    --port "$PORT" \
    --trace-map "$TRACE_MAP" \
    --trace-log "$TRACE_LOG" \
    "$DISK"
