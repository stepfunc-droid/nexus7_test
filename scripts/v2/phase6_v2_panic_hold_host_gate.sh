#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
PHASE4_ENV="${PHASE4_ENV:-$ROOT/diskless-v2/phase4-accepted.env}"
SYSTEM_IMG="${SYSTEM_IMG:-$HOME/system.raw.img}"
PATCHED_VENDOR="${PATCHED_VENDOR:-$OUT/vendor-fstab.raw.img}"
FACT_REPORT="${FACT_REPORT:-$OUT/phase6-v2-frozen-facts.txt}"
BASELINE_WRAPPER="$ROOT/initramfs/diskless-v2-android-continuation-init"
WRAPPER_AUDITOR="$ROOT/scripts/v2/audit_phase6_v2_panic_hold_wrapper.py"
WRITER_AUDITOR="$ROOT/scripts/v2/audit_phase6_v2_panic_runtime_writers.py"
BUILDER="$ROOT/scripts/v2/build_android_first_stage_probe.py"
IMAGE_AUDITOR="$ROOT/scripts/v2/audit_phase6_v2_continuation_image.py"
OUTPUT="${OUTPUT:-$OUT/phase6-v2-panic-hold.img}"
REPORT="${REPORT:-$OUT/phase6-v2-panic-hold-host-gate.txt}"

EXPECTED_BASELINE_WRAPPER_SHA256="2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc"
EXPECTED_WRAPPER_AUDITOR_GIT_BLOB="255fac3defa51190323109d6371435930a9ce412"
EXPECTED_WRITER_AUDITOR_GIT_BLOB="3c48954f7eb6f1acd26f0c843bb828adaa235add"
EXPECTED_BUILDER_GIT_BLOB="bdaeebbea1a4c406e7de7d0df3fb58b07ddd74f8"
EXPECTED_IMAGE_AUDITOR_GIT_BLOB="c182c52da24b8eb9006ff144f5176672d9d800d1"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 cmp sha256sum git grep awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$ANDROID_BOOT" "$TRANSPORT_BOOT" "$GENERATED_FSTAB" "$PHASE4_ENV" \
         "$SYSTEM_IMG" "$PATCHED_VENDOR" "$FACT_REPORT" \
         "$BASELINE_WRAPPER" "$WRAPPER_AUDITOR" "$WRITER_AUDITOR" "$BUILDER" "$IMAGE_AUDITOR"; do
    [[ -f "$f" ]] || fail "required input missing: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS$' "$FACT_REPORT" || \
    fail "frozen-fact report is not PASS; run accepted base preflight first"

BASELINE_SHA="$(sha256sum "$BASELINE_WRAPPER" | awk '{print $1}')"
[[ "$BASELINE_SHA" == "$EXPECTED_BASELINE_WRAPPER_SHA256" ]] || \
    fail "accepted continuation wrapper changed: actual=$BASELINE_SHA expected=$EXPECTED_BASELINE_WRAPPER_SHA256"

WRAPPER_AUDITOR_BLOB="$(git hash-object "$WRAPPER_AUDITOR")"
[[ "$WRAPPER_AUDITOR_BLOB" == "$EXPECTED_WRAPPER_AUDITOR_GIT_BLOB" ]] || \
    fail "panic-hold wrapper auditor changed: git-blob=$WRAPPER_AUDITOR_BLOB expected=$EXPECTED_WRAPPER_AUDITOR_GIT_BLOB"

WRITER_AUDITOR_BLOB="$(git hash-object "$WRITER_AUDITOR")"
[[ "$WRITER_AUDITOR_BLOB" == "$EXPECTED_WRITER_AUDITOR_GIT_BLOB" ]] || \
    fail "panic runtime writer auditor changed: git-blob=$WRITER_AUDITOR_BLOB expected=$EXPECTED_WRITER_AUDITOR_GIT_BLOB"

BUILDER_BLOB="$(git hash-object "$BUILDER")"
[[ "$BUILDER_BLOB" == "$EXPECTED_BUILDER_GIT_BLOB" ]] || \
    fail "accepted Phase5 builder changed: git-blob=$BUILDER_BLOB expected=$EXPECTED_BUILDER_GIT_BLOB"

IMAGE_AUDITOR_BLOB="$(git hash-object "$IMAGE_AUDITOR")"
[[ "$IMAGE_AUDITOR_BLOB" == "$EXPECTED_IMAGE_AUDITOR_GIT_BLOB" ]] || \
    fail "continuation image auditor changed: git-blob=$IMAGE_AUDITOR_BLOB expected=$EXPECTED_IMAGE_AUDITOR_GIT_BLOB"

# Bind the experiment to the exact accepted Android filesystem artifacts and
# conservatively reject any canonical direct panic-timeout writer literal.
echo "==> Auditing accepted system/vendor images for panic-timeout writers"
WRITER_AUDIT="$(python3 "$WRITER_AUDITOR" \
    --system "$SYSTEM_IMG" \
    --vendor "$PATCHED_VENDOR" \
    --fact-report "$FACT_REPORT")"
printf '%s\n' "$WRITER_AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_RUNTIME_WRITER_AUDIT=PASS$' <<<"$WRITER_AUDIT" || \
    fail "panic runtime writer audit PASS marker missing"
grep -q '^direct_panic_timeout_literals=0$' <<<"$WRITER_AUDIT" || \
    fail "accepted Android images contain a direct panic-timeout writer literal"
grep -q '^claim_limit=does-not-prove-absence-of-a-writer-using-nonliteral-programmatic-sysctl-access$' <<<"$WRITER_AUDIT" || \
    fail "writer audit claim-limit marker missing"

mkdir -p "$OUT"
TMPDIR="$(mktemp -d "$OUT/.phase6-v2-panic-hold.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT
DIAG_WRAPPER="$TMPDIR/init"
IMG_A="$TMPDIR/a.img"
IMG_B="$TMPDIR/b.img"

# Construct the diagnostic wrapper from the accepted continuation. The causal
# variable is panic_timeout 5 -> 0. The additional lines are fail-closed
# precondition observations proving panic=0 and panic_on_oops=1 before usb0/NBD.
python3 - "$BASELINE_WRAPPER" "$DIAG_WRAPPER" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])

base = """[ -w /proc/sys/kernel/panic_on_oops ] && echo 1 > /proc/sys/kernel/panic_on_oops
[ -w /proc/sys/kernel/panic ] && echo 5 > /proc/sys/kernel/panic
"""

diag = """[ -w /proc/sys/kernel/panic_on_oops ] || fail "panic_on_oops sysctl not writable"
echo 1 > /proc/sys/kernel/panic_on_oops || fail "failed to set panic_on_oops=1"
PANIC_ON_OOPS="$($BB cat /proc/sys/kernel/panic_on_oops 2>/dev/null || true)"
[ "$PANIC_ON_OOPS" = "1" ] || fail "panic_on_oops readback=$PANIC_ON_OOPS expected=1"
[ -w /proc/sys/kernel/panic ] || fail "panic sysctl not writable"
echo 0 > /proc/sys/kernel/panic || fail "failed to set panic=0"
PANIC_TIMEOUT="$($BB cat /proc/sys/kernel/panic 2>/dev/null || true)"
[ "$PANIC_TIMEOUT" = "0" ] || fail "panic readback=$PANIC_TIMEOUT expected=0"
"""

if src.count(base) != 1:
    raise SystemExit(f"ERROR: accepted panic block count={src.count(base)} expected=1")
out.write_text(src.replace(base, diag, 1))
PY

echo
echo "==> Auditing exact diagnostic wrapper delta"
WRAPPER_AUDIT="$(python3 "$WRAPPER_AUDITOR" \
    --baseline "$BASELINE_WRAPPER" \
    --replacement "$DIAG_WRAPPER")"
printf '%s\n' "$WRAPPER_AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_PANIC_HOLD_WRAPPER_AUDIT=PASS$' <<<"$WRAPPER_AUDIT" || \
    fail "panic-hold wrapper audit PASS marker missing"
grep -q '^causal_variable=kernel.panic:5->0$' <<<"$WRAPPER_AUDIT" || \
    fail "wrapper audit did not prove the intended causal variable"
grep -q '^runtime_readback=fail-closed$' <<<"$WRAPPER_AUDIT" || \
    fail "wrapper audit did not prove fail-closed runtime readback"
grep -q '^readback_order=before-usb0-and-nbd$' <<<"$WRAPPER_AUDIT" || \
    fail "runtime readback ordering is not proven"
grep -q '^all_bytes_outside_precondition_block=unchanged$' <<<"$WRAPPER_AUDIT" || \
    fail "wrapper audit found an unexpected delta"

build_one() {
    target="$1"
    python3 "$BUILDER" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --wrapper "$DIAG_WRAPPER" \
        --phase4-env "$PHASE4_ENV" \
        --output "$target"
}

echo
echo "==> Building panic-hold image A"
BUILD_A="$(build_one "$IMG_A")"
printf '%s\n' "$BUILD_A"
grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1$' <<<"$BUILD_A" || \
    fail "accepted builder did not emit success marker"

echo
echo "==> Building panic-hold image B"
BUILD_B="$(build_one "$IMG_B")"
printf '%s\n' "$BUILD_B"
cmp -s "$IMG_A" "$IMG_B" || fail "panic-hold diagnostic build is not reproducible"

DIAG_SHA="$(sha256sum "$DIAG_WRAPPER" | awk '{print $1}')"
IMAGE_SHA="$(sha256sum "$IMG_A" | awk '{print $1}')"

echo
echo "==> Auditing final image against exact diagnostic wrapper"
IMAGE_AUDIT="$(python3 "$IMAGE_AUDITOR" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$DIAG_WRAPPER" \
    --image "$IMG_A")"
printf '%s\n' "$IMAGE_AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS$' <<<"$IMAGE_AUDIT" || \
    fail "final panic-hold image audit did not pass"

mv "$IMG_A" "$OUTPUT"
rm -f "$IMG_B"

{
    printf '%s\n' "$WRITER_AUDIT"
    printf '%s\n' "$WRAPPER_AUDIT"
    printf '%s\n' "$IMAGE_AUDIT"
    echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS"
    echo "baseline_wrapper_sha256=$BASELINE_SHA"
    echo "diagnostic_wrapper_sha256=$DIAG_SHA"
    echo "wrapper_auditor_git_blob=$WRAPPER_AUDITOR_BLOB"
    echo "writer_auditor_git_blob=$WRITER_AUDITOR_BLOB"
    echo "builder_git_blob=$BUILDER_BLOB"
    echo "image_auditor_git_blob=$IMAGE_AUDITOR_BLOB"
    echo "causal_variable=kernel.panic:5->0"
    echo "panic_on_oops_target=1"
    echo "runtime_precondition=fail-closed-readback-before-usb0-and-nbd"
    echo "accepted_image_direct_panic_timeout_literals=0"
    echo "writer_audit_limit=nonliteral-programmatic-sysctl-access-not-proven-absent"
    echo "transport_setup=unchanged"
    echo "android_init=unchanged"
    echo "android_rc_modifications=none"
    echo "selinux_policy=stock-enforcing-baseline"
    echo "diagnostic_image=$OUTPUT"
    echo "diagnostic_image_sha256=$IMAGE_SHA"
    echo "binary_question=did-run1-like-reboot-depend-on-linux-panic-timeout-auto-restart"
    echo "interpretation_if_hold=panic-timeout-dependency-supported"
    echo "interpretation_if_reboot=panic-timeout-auto-restart-insufficient-to-explain-reset-subject-to-documented-writer-audit-limit"
    echo "hardware_authorized=no"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS"
echo "image=$OUTPUT"
echo "image_sha256=$IMAGE_SHA"
echo "report=$REPORT"
echo "runtime_precondition=fail-closed-readback-before-usb0-and-nbd"
echo "accepted_image_direct_panic_timeout_literals=0"
echo "NOTE: host PASS does not authorize hardware; see DISKLESS_V2_EXECUTION.md."
