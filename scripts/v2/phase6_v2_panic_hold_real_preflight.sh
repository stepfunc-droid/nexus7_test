#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
HOST_GATE="$ROOT/scripts/v2/phase6_v2_panic_hold_host_gate.sh"
BASE_PREFLIGHT="$ROOT/scripts/v2/phase6_v2_real_preflight.sh"
IMAGE="${IMAGE:-$OUT/phase6-v2-panic-hold.img}"
REPORT="${REPORT:-$OUT/phase6-v2-panic-hold-host-gate.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in bash sha256sum awk grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$HOST_GATE" "$BASE_PREFLIGHT"; do
    [[ -f "$f" ]] || fail "required preflight input missing: $f"
done

# First prove all accepted 6V2-A/B/C identities are still intact.
BASE_OUT="$(bash "$BASE_PREFLIGHT")"
printf '%s\n' "$BASE_OUT"
grep -q '^DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS$' <<<"$BASE_OUT" || \
    fail "base Audit-V2 real preflight did not pass"

# Rebuild/re-audit the diagnostic artifact immediately before hardware use.
HOLD_OUT="$(bash "$HOST_GATE")"
printf '%s\n' "$HOLD_OUT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS$' <<<"$HOLD_OUT" || \
    fail "panic-hold host gate did not pass"

[[ -f "$IMAGE" ]] || fail "panic-hold diagnostic image missing: $IMAGE"
[[ -f "$REPORT" ]] || fail "panic-hold report missing: $REPORT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS$' "$REPORT" || \
    fail "panic-hold report does not contain PASS marker"

grep -q '^runtime_delta=kernel.panic:5->0$' "$REPORT" || \
    fail "panic-hold report does not prove the intended single runtime delta"
grep -q '^panic_on_oops=unchanged:1$' "$REPORT" || \
    fail "panic_on_oops changed unexpectedly"
grep -q '^transport_setup=unchanged$' "$REPORT" || \
    fail "transport setup is not proven unchanged"
grep -q '^android_init=unchanged$' "$REPORT" || \
    fail "Android init is not proven unchanged"
grep -q '^android_rc_modifications=none$' "$REPORT" || \
    fail "Android rc modifications detected"

EXPECTED_IMAGE_SHA="$(awk -F= '/^diagnostic_image_sha256=/{print $2; exit}' "$REPORT")"
[[ -n "$EXPECTED_IMAGE_SHA" ]] || fail "diagnostic image SHA missing from report"
ACTUAL_IMAGE_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
[[ "$ACTUAL_IMAGE_SHA" == "$EXPECTED_IMAGE_SHA" ]] || \
    fail "diagnostic image SHA mismatch: actual=$ACTUAL_IMAGE_SHA expected=$EXPECTED_IMAGE_SHA"

echo
echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_REAL_PREFLIGHT=PASS"
echo "diagnostic_image=$IMAGE"
echo "diagnostic_image_sha256=$ACTUAL_IMAGE_SHA"
echo "runtime_delta=kernel.panic:5->0"
echo "panic_on_oops=1"
echo "accepted_continuation=unchanged"
echo "transport=accepted-6V2-path"
echo "binary_question=does-disabling-panic-auto-restart-convert-the-observed-reboot-into-a-persistent-hold"
echo "hardware_scope=one-controlled-run-only"
