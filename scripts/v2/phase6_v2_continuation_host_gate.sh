#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
PHASE4_ENV="${PHASE4_ENV:-$ROOT/diskless-v2/phase4-accepted.env}"
BASELINE_WRAPPER="$ROOT/initramfs/diskless-v2-android-first-stage-init"
CONTINUATION_WRAPPER="$ROOT/initramfs/diskless-v2-android-continuation-init"
PHASE5_BUILDER="$ROOT/scripts/v2/build_android_first_stage_probe.py"
FACT_REPORT="${FACT_REPORT:-$OUT/phase6-v2-frozen-facts.txt}"
OUTPUT="${OUTPUT:-$OUT/phase6-v2-continuation.img}"
REPORT="${REPORT:-$OUT/phase6-v2-continuation-host-audit.txt}"

EXPECTED_PHASE5D_WRAPPER_GIT_BLOB="4863e82cbaf4cca4ae0544e2fd667c2f9d95317a"
EXPECTED_PHASE5_BUILDER_GIT_BLOB="bdaeebbea1a4c406e7de7d0df3fb58b07ddd74f8"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 cmp sha256sum grep git awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in \
    "$ANDROID_BOOT" "$TRANSPORT_BOOT" "$GENERATED_FSTAB" "$PHASE4_ENV" \
    "$BASELINE_WRAPPER" "$CONTINUATION_WRAPPER" "$PHASE5_BUILDER" "$FACT_REPORT"; do
    [[ -f "$f" ]] || fail "required Audit-V2 continuation input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS$' "$FACT_REPORT" || \
    fail "6V2-A frozen-fact report is not accepted: $FACT_REPORT"

BASELINE_BLOB="$(git hash-object "$BASELINE_WRAPPER")"
[[ "$BASELINE_BLOB" == "$EXPECTED_PHASE5D_WRAPPER_GIT_BLOB" ]] || \
    fail "Phase5D baseline wrapper changed: git-blob=$BASELINE_BLOB expected=$EXPECTED_PHASE5D_WRAPPER_GIT_BLOB"

BUILDER_BLOB="$(git hash-object "$PHASE5_BUILDER")"
[[ "$BUILDER_BLOB" == "$EXPECTED_PHASE5_BUILDER_GIT_BLOB" ]] || \
    fail "accepted Phase5 image builder changed: git-blob=$BUILDER_BLOB expected=$EXPECTED_PHASE5_BUILDER_GIT_BLOB"

mkdir -p "$OUT"
TMP_A="$OUT/.phase6-v2-continuation-a.img"
TMP_B="$OUT/.phase6-v2-continuation-b.img"
rm -f "$TMP_A" "$TMP_B"
trap 'rm -f "$TMP_A" "$TMP_B"' EXIT

echo "==> 6V2-B1: semantic diff against accepted Phase5D wrapper"
WRAPPER_AUDIT="$(python3 "$ROOT/scripts/v2/audit_phase6_v2_continuation_wrapper.py" \
    --baseline "$BASELINE_WRAPPER" \
    --replacement "$CONTINUATION_WRAPPER")"
printf '%s\n' "$WRAPPER_AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_WRAPPER_SEMANTIC_DIFF=PASS$' <<<"$WRAPPER_AUDIT" || \
    fail "wrapper semantic-diff PASS marker missing"
grep -q '^new_executable_lines=0$' <<<"$WRAPPER_AUDIT" || \
    fail "continuation wrapper contains executable lines not inherited from Phase5D"
grep -q '^p3_p5_p6_content_io_by_supervisor=absent$' <<<"$WRAPPER_AUDIT" || \
    fail "continuation wrapper violates later-stage partition-I/O boundary"

build_one() {
    target="$1"
    python3 "$PHASE5_BUILDER" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --wrapper "$CONTINUATION_WRAPPER" \
        --phase4-env "$PHASE4_ENV" \
        --output "$target"
}

echo
echo "==> 6V2-B2: deterministic build A using accepted Phase5D builder"
BUILD_A="$(build_one "$TMP_A")"
printf '%s\n' "$BUILD_A"

grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1$' <<<"$BUILD_A" || \
    fail "accepted Phase5D builder did not emit build marker"
# The legacy builder prints a historical 'intentionally-stopped' description.
# Audit V2 deliberately does NOT accept that text as semantics; the wrapper
# semantic-diff gate above proves SIGSTOP is absent.

echo
echo "==> 6V2-B3: deterministic build B"
BUILD_B="$(build_one "$TMP_B")"
printf '%s\n' "$BUILD_B"

cmp -s "$TMP_A" "$TMP_B" || fail "two continuation builds are not byte-identical"
BUILD_SHA="$(sha256sum "$TMP_A" | awk '{print $1}')"

echo "DISKLESS_V2_PHASE6_V2_CONTINUATION_REPRODUCIBLE=PASS"
echo "reproducible_sha256=$BUILD_SHA"

mv "$TMP_A" "$OUTPUT"
rm -f "$TMP_B"
trap - EXIT

echo
echo "==> 6V2-B4: independent final-image audit"
IMAGE_AUDIT="$(python3 "$ROOT/scripts/v2/audit_phase6_v2_continuation_image.py" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$CONTINUATION_WRAPPER" \
    --image "$OUTPUT")"
printf '%s\n' "$IMAGE_AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS$' <<<"$IMAGE_AUDIT" || \
    fail "continuation final-image audit PASS marker missing"

{
    printf '%s\n' "$WRAPPER_AUDIT"
    printf '%s\n' "$IMAGE_AUDIT"
    echo "DISKLESS_V2_PHASE6_V2_CONTINUATION_REPRODUCIBLE=PASS"
    echo "reproducible_sha256=$BUILD_SHA"
    echo "DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS"
    echo "phase5d_wrapper_git_blob=$BASELINE_BLOB"
    echo "phase5_builder_git_blob=$BUILDER_BLOB"
    echo "runtime_delta=subtract-observers-and-sigstop-only"
    echo "transport_setup=unchanged-from-Phase5D"
    echo "handoff=exec-/init.android"
    echo "android_rc_modifications=none"
    echo "selinux_policy=stock-enforcing-baseline"
    echo "real_device_boot=not-authorized-by-this-gate"
    echo "next_gate=6V2-C-host-tracer-semantic-gate"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS"
echo "image=$OUTPUT"
echo "image_sha256=$BUILD_SHA"
echo "report=$REPORT"
echo "Hardware remains PAUSED. Do not boot this image until 6V2-C host tracer semantic gate passes."
