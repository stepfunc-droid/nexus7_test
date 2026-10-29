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

# First prove all accepted 6V2-A/B/C identities are still intact and refresh
# the frozen-fact report used by the accepted-image writer audit.
BASE_OUT="$(bash "$BASE_PREFLIGHT")"
printf '%s\n' "$BASE_OUT"
grep -q '^DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS$' <<<"$BASE_OUT" || \
    fail "base Audit-V2 real preflight did not pass"

# Rebuild and independently re-audit the diagnostic artifact immediately before
# any possible hardware use. This still does NOT authorize a hardware boot.
HOLD_OUT="$(bash "$HOST_GATE")"
printf '%s\n' "$HOLD_OUT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS$' <<<"$HOLD_OUT" || \
    fail "panic-hold host gate did not pass"

[[ -f "$IMAGE" ]] || fail "panic-hold diagnostic image missing: $IMAGE"
[[ -f "$REPORT" ]] || fail "panic-hold report missing: $REPORT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS$' "$REPORT" || \
    fail "panic-hold report does not contain PASS marker"

grep -q '^causal_variable=kernel.panic:5->0$' "$REPORT" || \
    fail "panic-hold report does not prove the intended causal variable"
grep -q '^panic_on_oops_target=1$' "$REPORT" || \
    fail "panic_on_oops target changed unexpectedly"
grep -q '^runtime_precondition=fail-closed-readback-before-usb0-and-nbd$' "$REPORT" || \
    fail "runtime panic sysctl readback is not fail-closed before transport"
grep -q '^accepted_image_direct_panic_timeout_literals=0$' "$REPORT" || \
    fail "accepted Android image writer audit is missing or failed"
grep -q '^writer_audit_limit=nonliteral-programmatic-sysctl-access-not-proven-absent$' "$REPORT" || \
    fail "writer-audit limitation is not recorded"
grep -q '^transport_setup=unchanged$' "$REPORT" || \
    fail "transport setup is not proven unchanged"
grep -q '^android_init=unchanged$' "$REPORT" || \
    fail "Android init is not proven unchanged"
grep -q '^android_rc_modifications=none$' "$REPORT" || \
    fail "Android rc modifications detected"
grep -q '^selinux_policy=stock-enforcing-baseline$' "$REPORT" || \
    fail "SELinux baseline changed"
grep -q '^hardware_authorized=no$' "$REPORT" || \
    fail "host gate must not self-authorize hardware"

EXPECTED_IMAGE_SHA="$(awk -F= '/^diagnostic_image_sha256=/{print $2; exit}' "$REPORT")"
[[ -n "$EXPECTED_IMAGE_SHA" ]] || fail "diagnostic image SHA missing from report"
ACTUAL_IMAGE_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
[[ "$ACTUAL_IMAGE_SHA" == "$EXPECTED_IMAGE_SHA" ]] || \
    fail "diagnostic image SHA mismatch: actual=$ACTUAL_IMAGE_SHA expected=$EXPECTED_IMAGE_SHA"

echo
echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_REAL_PREFLIGHT=PASS"
echo "diagnostic_image=$IMAGE"
echo "diagnostic_image_sha256=$ACTUAL_IMAGE_SHA"
echo "causal_variable=kernel.panic:5->0"
echo "panic_on_oops_target=1"
echo "runtime_precondition=fail-closed-readback-before-usb0-and-nbd"
echo "accepted_image_direct_panic_timeout_literals=0"
echo "writer_audit_limit=nonliteral-programmatic-sysctl-access-not-proven-absent"
echo "accepted_continuation=unchanged"
echo "transport=accepted-6V2-path"
echo "binary_question=did-run1-like-reboot-depend-on-linux-panic-timeout-auto-restart"
echo "hardware_scope=one-controlled-run-only-if-separately-authorized-by-design-doc"
echo "hardware_authorized=no"
