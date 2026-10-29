#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BASE_URL="${BASE_URL:-http://172.16.42.1:2325}"
OUTDIR="${OUTDIR:-$HOME/phase6-v2-run1-crash-capture}"
LAST_KMSG="$OUTDIR/last_kmsg.txt"
DIAG="$OUTDIR/diag.txt"
STATUS="$OUTDIR/status.txt"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

command -v curl >/dev/null 2>&1 || fail "curl is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"

bash "$ROOT/scripts/v2/phase6_v2_crash_capture_preflight.sh"
mkdir -p "$OUTDIR"

# These GETs are observation-only.  The accepted transport recovery image
# snapshots /proc/last_kmsg before usb0/httpd/NBD activity.
curl -fsS --connect-timeout 2 --max-time 5 "$BASE_URL/status.txt" -o "$STATUS" || true
curl -fsS --connect-timeout 2 --max-time 5 "$BASE_URL/diag.txt" -o "$DIAG" || true

if curl -fsS --connect-timeout 2 --max-time 10 "$BASE_URL/last_kmsg.txt" -o "$LAST_KMSG"; then
    if [[ -s "$LAST_KMSG" ]]; then
        echo "DISKLESS_V2_PHASE6_V2_LAST_KMSG_CAPTURE=PASS"
        echo "last_kmsg=$LAST_KMSG"
        echo "last_kmsg_bytes=$(wc -c < "$LAST_KMSG" | tr -d ' ')"
        echo "last_kmsg_sha256=$(sha256sum "$LAST_KMSG" | awk '{print $1}')"
        [[ -f "$DIAG" ]] && echo "diag=$DIAG"
        [[ -f "$STATUS" ]] && echo "status=$STATUS"
        exit 0
    fi
fi

rm -f "$LAST_KMSG"
echo "DISKLESS_V2_PHASE6_V2_LAST_KMSG_CAPTURE=NOT_AVAILABLE"
[[ -f "$DIAG" ]] && echo "diag=$DIAG"
[[ -f "$STATUS" ]] && echo "status=$STATUS"
echo "classification=UNKNOWN"
echo "note=absence-of-last_kmsg-is-not-proof-of-userspace-reboot"
exit 2
