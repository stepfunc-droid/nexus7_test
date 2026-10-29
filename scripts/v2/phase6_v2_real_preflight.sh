#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
MANIFEST="${MANIFEST:-$DISK.manifest.json}"
LAYOUT="${LAYOUT:-$ROOT/diskless-v2/layout.json}"
IMAGE="${IMAGE:-$OUT/phase6-v2-continuation.img}"
CONTINUATION_WRAPPER="$ROOT/initramfs/diskless-v2-android-continuation-init"
CONTINUATION_REPORT="${CONTINUATION_REPORT:-$OUT/phase6-v2-continuation-host-audit.txt}"
TRACER_REPORT="${TRACER_REPORT:-$OUT/phase6-v2-tracer-host-audit.txt}"
TRACE_MAP="${TRACE_MAP:-$OUT/phase6-v2-partition-trace-map.json}"
TRACED_SERVER="$ROOT/scripts/v2/nbd_partition_trace_server.py"
ACCEPTED_SERVER="$ROOT/scripts/nbd_test_server.py"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 cmp sha256sum grep git awk mktemp; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in \
    "$DISK" "$MANIFEST" "$LAYOUT" "$IMAGE" "$CONTINUATION_WRAPPER" \
    "$CONTINUATION_REPORT" "$TRACER_REPORT" "$TRACE_MAP" \
    "$TRACED_SERVER" "$ACCEPTED_SERVER"; do
    [[ -f "$f" ]] || fail "required 6V2-D preflight input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS$' "$CONTINUATION_REPORT" || \
    fail "6V2-B continuation host gate is not PASS"
grep -q '^DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS$' "$TRACER_REPORT" || \
    fail "6V2-C tracer host gate is not PASS"
grep -q '^new_executable_lines=0$' "$CONTINUATION_REPORT" || \
    fail "6V2-B report does not preserve zero-new-executable-lines contract"
grep -q '^p3_p5_p6_content_io_by_supervisor=absent$' "$CONTINUATION_REPORT" || \
    fail "6V2-B report does not preserve partition-I/O evidence boundary"

EXPECTED_IMAGE_SHA="$(awk -F= '/^reproducible_sha256=/{print $2; exit}' "$CONTINUATION_REPORT")"
[[ -n "$EXPECTED_IMAGE_SHA" ]] || fail "continuation report missing reproducible_sha256"
ACTUAL_IMAGE_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
[[ "$ACTUAL_IMAGE_SHA" == "$EXPECTED_IMAGE_SHA" ]] || \
    fail "continuation image changed since 6V2-B: actual=$ACTUAL_IMAGE_SHA expected=$EXPECTED_IMAGE_SHA"

EXPECTED_WRAPPER_SHA="$(awk -F= '/^replacement_sha256=/{print $2; exit}' "$CONTINUATION_REPORT")"
[[ -n "$EXPECTED_WRAPPER_SHA" ]] || fail "continuation report missing replacement_sha256"
ACTUAL_WRAPPER_SHA="$(sha256sum "$CONTINUATION_WRAPPER" | awk '{print $1}')"
[[ "$ACTUAL_WRAPPER_SHA" == "$EXPECTED_WRAPPER_SHA" ]] || \
    fail "continuation wrapper changed since 6V2-B: actual=$ACTUAL_WRAPPER_SHA expected=$EXPECTED_WRAPPER_SHA"

EXPECTED_TRACED_BLOB="$(awk -F= '/^traced_nbd_server_git_blob=/{print $2; exit}' "$TRACER_REPORT")"
EXPECTED_ACCEPTED_BLOB="$(awk -F= '/^accepted_nbd_server_git_blob=/{print $2; exit}' "$TRACER_REPORT")"
[[ -n "$EXPECTED_TRACED_BLOB" ]] || fail "tracer report missing traced_nbd_server_git_blob"
[[ -n "$EXPECTED_ACCEPTED_BLOB" ]] || fail "tracer report missing accepted_nbd_server_git_blob"
ACTUAL_TRACED_BLOB="$(git hash-object "$TRACED_SERVER")"
ACTUAL_ACCEPTED_BLOB="$(git hash-object "$ACCEPTED_SERVER")"
[[ "$ACTUAL_TRACED_BLOB" == "$EXPECTED_TRACED_BLOB" ]] || \
    fail "traced NBD server changed since 6V2-C: actual=$ACTUAL_TRACED_BLOB expected=$EXPECTED_TRACED_BLOB"
[[ "$ACTUAL_ACCEPTED_BLOB" == "$EXPECTED_ACCEPTED_BLOB" ]] || \
    fail "accepted NBD server changed since 6V2-C: actual=$ACTUAL_ACCEPTED_BLOB expected=$EXPECTED_ACCEPTED_BLOB"

TMP_MAP="$(mktemp "${TMPDIR:-/tmp}/phase6-v2-map.XXXXXX.json")"
trap 'rm -f "$TMP_MAP"' EXIT
python3 "$ROOT/scripts/v2/prepare_phase6_v2_partition_trace.py" \
    --disk "$DISK" \
    --manifest "$MANIFEST" \
    --layout "$LAYOUT" \
    --output "$TMP_MAP" >/dev/null
cmp -s "$TRACE_MAP" "$TMP_MAP" || \
    fail "partition trace map no longer matches deterministic disk/layout reconstruction"
rm -f "$TMP_MAP"
trap - EXIT

echo "DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS"
echo "continuation_image_sha256=$ACTUAL_IMAGE_SHA"
echo "continuation_wrapper_sha256=$ACTUAL_WRAPPER_SHA"
echo "accepted_nbd_server_git_blob=$ACTUAL_ACCEPTED_BLOB"
echo "traced_nbd_server_git_blob=$ACTUAL_TRACED_BLOB"
echo "partition_trace_map=deterministic-match"
echo "6V2_B_report=PASS"
echo "6V2_C_report=PASS"
echo "hardware_boot_permitted=controlled-6V2-D-only"
