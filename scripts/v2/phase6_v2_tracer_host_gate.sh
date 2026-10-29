#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
MANIFEST="${MANIFEST:-$DISK.manifest.json}"
LAYOUT="${LAYOUT:-$ROOT/diskless-v2/layout.json}"
CONTINUATION_REPORT="${CONTINUATION_REPORT:-$OUT/phase6-v2-continuation-host-audit.txt}"
TRACE_MAP="${TRACE_MAP:-$OUT/phase6-v2-partition-trace-map.json}"
REPORT="${REPORT:-$OUT/phase6-v2-tracer-host-audit.txt}"
TRACED_SERVER="$ROOT/scripts/v2/nbd_partition_trace_server.py"
ACCEPTED_SERVER="$ROOT/scripts/nbd_test_server.py"

EXPECTED_ACCEPTED_SERVER_GIT_BLOB="6e7ce821c98f3c4f7a4ff4c337a20a4297c2bfd8"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 grep git sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$DISK" "$MANIFEST" "$LAYOUT" "$CONTINUATION_REPORT" "$TRACED_SERVER" "$ACCEPTED_SERVER"; do
    [[ -f "$f" ]] || fail "required 6V2-C input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS$' "$CONTINUATION_REPORT" || \
    fail "6V2-B continuation host gate has not passed"
grep -q '^p3_p5_p6_content_io_by_supervisor=absent$' "$CONTINUATION_REPORT" || \
    fail "6V2-B report does not preserve post-first-stage partition-I/O boundary"

ACCEPTED_BLOB="$(git hash-object "$ACCEPTED_SERVER")"
[[ "$ACCEPTED_BLOB" == "$EXPECTED_ACCEPTED_SERVER_GIT_BLOB" ]] || \
    fail "accepted Phase3/4 NBD server changed: git-blob=$ACCEPTED_BLOB expected=$EXPECTED_ACCEPTED_SERVER_GIT_BLOB"
TRACED_BLOB="$(git hash-object "$TRACED_SERVER")"

mkdir -p "$OUT"

echo "==> 6V2-C1: build real-disk partition evidence map"
MAP_OUTPUT="$(python3 "$ROOT/scripts/v2/prepare_phase6_v2_partition_trace.py" \
    --disk "$DISK" \
    --manifest "$MANIFEST" \
    --layout "$LAYOUT" \
    --output "$TRACE_MAP")"
printf '%s\n' "$MAP_OUTPUT"
grep -q '^DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_MAP=PASS$' <<<"$MAP_OUTPUT" || \
    fail "partition trace-map PASS marker missing"
grep -q '^partition_table_traffic_is_not_stage_evidence=PASS$' <<<"$MAP_OUTPUT" || \
    fail "trace map does not explicitly exclude partition-table traffic as stage evidence"

echo
echo "==> 6V2-C2: differential protocol test vs accepted Phase3/4 server"
DIFF_OUTPUT="$(python3 "$ROOT/scripts/v2/selftest_phase6_v2_nbd_differential.py")"
printf '%s\n' "$DIFF_OUTPUT"
grep -q '^DISKLESS_V2_PHASE6_V2_NBD_DIFFERENTIAL=PASS$' <<<"$DIFF_OUTPUT" || \
    fail "NBD differential PASS marker missing"
grep -q '^rw_handshake_and_replies=byte-identical$' <<<"$DIFF_OUTPUT" || \
    fail "read-write protocol differs from accepted server"
grep -q '^readonly_handshake_and_replies=byte-identical$' <<<"$DIFF_OUTPUT" || \
    fail "read-only protocol differs from accepted server"

echo
echo "==> 6V2-C3: partition-stage classifier semantic self-test"
TRACE_TEST_OUTPUT="$(python3 "$ROOT/scripts/v2/selftest_phase6_v2_partition_trace.py" \
    --trace-map "$TRACE_MAP")"
printf '%s\n' "$TRACE_TEST_OUTPUT"
grep -q '^DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_SELFTEST=PASS$' <<<"$TRACE_TEST_OUTPUT" || \
    fail "partition trace semantic self-test PASS marker missing"
grep -q '^superblock_plus_primary_gdt_required=PASS$' <<<"$TRACE_TEST_OUTPUT" || \
    fail "filesystem evidence is not sufficiently discriminating"

{
    printf '%s\n' "$MAP_OUTPUT"
    printf '%s\n' "$DIFF_OUTPUT"
    printf '%s\n' "$TRACE_TEST_OUTPUT"
    echo "DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS"
    echo "accepted_nbd_server_git_blob=$ACCEPTED_BLOB"
    echo "traced_nbd_server_git_blob=$TRACED_BLOB"
    echo "traced_nbd_server_sha256=$(sha256sum "$TRACED_SERVER" | awk '{print $1}')"
    echo "evidence_boundary=cache-or-persist-superblock-plus-primary-gdt"
    echo "late_evidence_boundary=userdata-superblock-plus-primary-gdt"
    echo "same_connection_required=yes"
    echo "real_device_boot=not-performed"
    echo "next_gate=6V2-D-first-real-device-continuation"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS"
echo "trace_map=$TRACE_MAP"
echo "report=$REPORT"
echo "No Nexus boot was performed. Return the 6V2-A/B/C PASS output before starting 6V2-D."
