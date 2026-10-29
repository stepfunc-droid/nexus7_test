#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
R1_REPORT="${R1_REPORT:-$OUT/phase6-r1-host-audit.txt}"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
MANIFEST="${MANIFEST:-$DISK.manifest.json}"
SYSTEM_IMG="${SYSTEM_IMG:-$HOME/system.raw.img}"
VENDOR_IMG="${VENDOR_IMG:-$OUT/vendor-fstab.raw.img}"
TRACE_MAP="${TRACE_MAP:-$OUT/phase6-r2-trace-map.json}"
REPORT="${REPORT:-$OUT/phase6-r2-host-audit.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 grep sha256sum tee; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$R1_REPORT" "$DISK" "$MANIFEST" "$SYSTEM_IMG" "$VENDOR_IMG"; do
    [[ -f "$f" ]] || fail "required Phase6 R2 input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS$' "$R1_REPORT" || \
    fail "Phase6 R1 report does not contain PASS marker"

mkdir -p "$OUT"
TMP="$(mktemp "${TMPDIR:-/tmp}/phase6-r2-host.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

{
    echo "==> Phase6 R2: resolve ext4 marker files and verify assembled-disk ranges"
    python3 "$ROOT/scripts/v2/prepare_phase6_r2_trace.py" \
        --disk "$DISK" \
        --manifest "$MANIFEST" \
        --system "$SYSTEM_IMG" \
        --vendor "$VENDOR_IMG" \
        --output "$TRACE_MAP"

    echo
    echo "==> Phase6 R2: self-test tracer coverage and marker ordering"
    python3 "$ROOT/scripts/v2/selftest_phase6_r2_trace.py" \
        --trace-map "$TRACE_MAP"

    echo
    echo "==> Phase6 R2: localhost end-to-end oldstyle NBD trace self-test"
    python3 "$ROOT/scripts/v2/selftest_phase6_r2_server.py" \
        --disk "$DISK" \
        --trace-map "$TRACE_MAP"
} | tee "$TMP"

grep -q '^DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS$' "$TMP" || \
    fail "trace-map PASS marker missing"
grep -q '^DISKLESS_V2_PHASE6_R2_TRACE_SELFTEST=PASS$' "$TMP" || \
    fail "trace self-test PASS marker missing"
grep -q '^DISKLESS_V2_PHASE6_R2_SERVER_SELFTEST=PASS$' "$TMP" || \
    fail "end-to-end NBD server self-test PASS marker missing"

{
    cat "$TMP"
    echo
    echo "DISKLESS_V2_PHASE6_R2_HOST_GATE=PASS"
    echo "trace_map=$TRACE_MAP"
    echo "trace_map_sha256=$(sha256sum "$TRACE_MAP" | awk '{print $1}')"
    echo "evidence_source=host-NBD-file-range-trace"
    echo "oldstyle_nbd_protocol_selftest=PASS"
    echo "read_payload_byte_validation=PASS"
    echo "nexus_side_logger=none"
    echo "android_rc_modifications=none"
    echo "real_device_boot=not-performed"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_R2_HOST_GATE=PASS"
echo "trace_map=$TRACE_MAP"
echo "report=$REPORT"
echo "No Nexus boot was performed."
