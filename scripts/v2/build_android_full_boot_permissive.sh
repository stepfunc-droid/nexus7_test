#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
WRAPPER="$ROOT/initramfs/diskless-v2-android-full-init"
PHASE4_ENV="$ROOT/diskless-v2/phase4-accepted.env"
OUTPUT="${OUTPUT:-$OUT/android-full-boot-permissive.img}"
MANIFEST="${MANIFEST:-$OUT/android-full-boot-permissive-manifest.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 sha256sum grep awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

[[ -f "$ANDROID_BOOT" ]] || fail "accepted Phase 5B boot artifact not found: $ANDROID_BOOT"
[[ -f "$TRANSPORT_BOOT" ]] || fail "accepted Phase 4 transport boot not found: $TRANSPORT_BOOT"
[[ -f "$GENERATED_FSTAB" ]] || fail "accepted Phase 5 fstab not found: $GENERATED_FSTAB"
[[ -f "$WRAPPER" ]] || fail "Phase6 full-boot supervisor missing: $WRAPPER"
[[ -f "$PHASE4_ENV" ]] || fail "accepted Phase 4 identity missing: $PHASE4_ENV"

mkdir -p "$OUT"
rm -f "$OUTPUT" "$MANIFEST"

echo "==> Building Phase6 diagnostic-permissive Android boot image"
BUILD_OUTPUT="$(python3 "$ROOT/scripts/v2/build_android_full_boot.py" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$WRAPPER" \
    --phase4-env "$PHASE4_ENV" \
    --selinux-mode permissive \
    --output "$OUTPUT")"
printf '%s\n' "$BUILD_OUTPUT"

grep -q '^DISKLESS_V2_ANDROID_FULL_BOOT_BUILT=1$' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 permissive builder did not emit success marker"
grep -q '^android_init=preserved-as-/init.android$' <<<"$BUILD_OUTPUT" || \
    fail "original Android init preservation was not verified"
grep -q '^supervisor=single-nbd-full-boot$' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 supervisor contract missing"
grep -q '^first_stage_stop=disabled$' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 diagnostic image still carries first-stage stop policy"
grep -q '^selinux_policy=diagnostic-permissive$' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 diagnostic image is not explicitly permissive"
grep -q '^android_rc_bypasses=none$' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 diagnostic unexpectedly includes Android rc bypasses"
grep -q 'androidboot.selinux=permissive' <<<"$BUILD_OUTPUT" || \
    fail "Phase6 diagnostic cmdline is missing androidboot.selinux=permissive"

{
    echo "DISKLESS_V2_ANDROID_FULL_BOOT_PERMISSIVE_IMAGE_BUILT=1"
    echo "android_boot=$ANDROID_BOOT"
    echo "android_boot_sha256=$(sha256sum "$ANDROID_BOOT" | awk '{print $1}')"
    echo "transport_boot=$TRANSPORT_BOOT"
    echo "transport_boot_sha256=$(sha256sum "$TRANSPORT_BOOT" | awk '{print $1}')"
    echo "generated_fstab=$GENERATED_FSTAB"
    echo "generated_fstab_sha256=$(sha256sum "$GENERATED_FSTAB" | awk '{print $1}')"
    echo "wrapper_sha256=$(sha256sum "$WRAPPER" | awk '{print $1}')"
    echo "full_boot=$OUTPUT"
    echo "full_boot_sha256=$(sha256sum "$OUTPUT" | awk '{print $1}')"
    echo "android_init=preserved"
    echo "first_stage_stop=disabled"
    echo "selinux_policy=diagnostic-permissive"
    echo "android_rc_bypasses=none"
    echo "phase6_scope=second-stage-diagnostic-only"
} > "$MANIFEST"

echo
echo "DISKLESS_V2_ANDROID_FULL_BOOT_PERMISSIVE_IMAGE_BUILT=1"
cat "$MANIFEST"
echo "manifest=$MANIFEST"
