#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
WRAPPER="$ROOT/initramfs/diskless-v2-android-first-stage-init"
PHASE4_ENV="$ROOT/diskless-v2/phase4-accepted.env"
OUTPUT="${OUTPUT:-$OUT/android-first-stage-probe.img}"
MANIFEST="${MANIFEST:-$OUT/android-first-stage-probe-manifest.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

[[ -f "$ANDROID_BOOT" ]] || fail "Phase 5B boot-fstab-only artifact not found: $ANDROID_BOOT"
[[ -f "$TRANSPORT_BOOT" ]] || fail "accepted Phase 4 transport boot not found: $TRANSPORT_BOOT"
[[ -f "$GENERATED_FSTAB" ]] || fail "generated Phase 5 fstab not found: $GENERATED_FSTAB"
[[ -f "$WRAPPER" ]] || fail "first-stage supervisor missing: $WRAPPER"
[[ -f "$PHASE4_ENV" ]] || fail "accepted Phase 4 identity missing: $PHASE4_ENV"

mkdir -p "$OUT"
rm -f "$OUTPUT" "$MANIFEST"

echo "==> Building Android first-stage mount probe from accepted artifacts"
BUILD_OUTPUT="$(python3 "$ROOT/scripts/v2/build_android_first_stage_probe.py" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$WRAPPER" \
    --phase4-env "$PHASE4_ENV" \
    --output "$OUTPUT")"
printf '%s\n' "$BUILD_OUTPUT"

grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1$' <<<"$BUILD_OUTPUT" || \
    fail "first-stage probe builder did not emit success marker"
grep -q '^android_init=preserved-as-/init.android$' <<<"$BUILD_OUTPUT" || \
    fail "original Android init preservation was not verified"
grep -q '^probe_init=single-nbd-supervisor$' <<<"$BUILD_OUTPUT" || \
    fail "probe wrapper contract missing"
grep -q '^late_android_boot=intentionally-stopped-after-first-stage-mounts$' <<<"$BUILD_OUTPUT" || \
    fail "probe does not enforce first-stage-only scope"

{
    echo "DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_IMAGE_BUILT=1"
    echo "android_boot=$ANDROID_BOOT"
    echo "android_boot_sha256=$(sha256sum "$ANDROID_BOOT" | awk '{print $1}')"
    echo "transport_boot=$TRANSPORT_BOOT"
    echo "transport_boot_sha256=$(sha256sum "$TRANSPORT_BOOT" | awk '{print $1}')"
    echo "generated_fstab=$GENERATED_FSTAB"
    echo "generated_fstab_sha256=$(sha256sum "$GENERATED_FSTAB" | awk '{print $1}')"
    echo "wrapper_sha256=$(sha256sum "$WRAPPER" | awk '{print $1}')"
    echo "probe_boot=$OUTPUT"
    echo "probe_boot_sha256=$(sha256sum "$OUTPUT" | awk '{print $1}')"
    echo "android_init=preserved"
    echo "android_rc_bypasses=none"
    echo "probe_scope=first-stage-system-vendor-mounts-only"
} > "$MANIFEST"

echo
echo "DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_IMAGE_BUILT=1"
cat "$MANIFEST"
echo "manifest=$MANIFEST"
