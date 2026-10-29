#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"

STOCK_BOOT="${STOCK_BOOT:-$ROOT/lineage-flox-boot.img}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
STOCK_VENDOR="${STOCK_VENDOR:-$HOME/vendor.raw.img}"
PATCHED_VENDOR="${PATCHED_VENDOR:-$OUT/vendor-fstab.raw.img}"
STOCK_FSTAB="${STOCK_FSTAB:-$ROOT/diskless-v2/fstab.flox.stock}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
SYSTEM_IMG="${SYSTEM_IMG:-$HOME/system.raw.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
ANDROID_DISK="${ANDROID_DISK:-$HOME/nexus7-diskless-v2/diskless-v2-android.raw.img}"
DISK_MANIFEST="${DISK_MANIFEST:-$ANDROID_DISK.manifest.json}"
LAYOUT="${LAYOUT:-$ROOT/diskless-v2/layout.json}"
PHASE4_ENV="${PHASE4_ENV:-$ROOT/diskless-v2/phase4-accepted.env}"
REPORT="${REPORT:-$OUT/phase6-r0-host-audit.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 sha256sum grep tee; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in \
    "$STOCK_BOOT" "$ANDROID_BOOT" "$STOCK_VENDOR" "$PATCHED_VENDOR" \
    "$STOCK_FSTAB" "$GENERATED_FSTAB" "$SYSTEM_IMG" "$TRANSPORT_BOOT" \
    "$ANDROID_DISK" "$DISK_MANIFEST" "$LAYOUT" "$PHASE4_ENV"; do
    [[ -f "$f" ]] || fail "required Phase6 R0 input not found: $f"
done

mkdir -p "$OUT"
TMP="$(mktemp "${TMPDIR:-/tmp}/phase6-r0.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

{
    echo "==> Phase6 R0: revalidate Phase5 fstab-only artifacts"
    python3 "$ROOT/scripts/v2/validate_android_fstab_artifacts.py" \
        --stock-boot "$STOCK_BOOT" \
        --patched-boot "$ANDROID_BOOT" \
        --stock-vendor "$STOCK_VENDOR" \
        --patched-vendor "$PATCHED_VENDOR" \
        --stock-fstab "$STOCK_FSTAB" \
        --generated-fstab "$GENERATED_FSTAB"

    echo
    echo "==> Phase6 R0: re-audit clean system source"
    python3 "$ROOT/scripts/v2/audit_android_system_source.py" \
        --image "$SYSTEM_IMG"

    echo
    echo "==> Phase6 R0: revalidate Android-test disk structure"
    python3 "$ROOT/scripts/v2/validate_disk.py" \
        --disk "$ANDROID_DISK" \
        --manifest "$DISK_MANIFEST"

    echo
    echo "==> Phase6 R0: prove exact system/vendor source bytes remain in p1/p2"
    python3 "$ROOT/scripts/v2/validate_android_disk_sources.py" \
        --disk "$ANDROID_DISK" \
        --manifest "$DISK_MANIFEST" \
        --system "$SYSTEM_IMG" \
        --vendor "$PATCHED_VENDOR"

    echo
    echo "==> Phase6 R0: audit accepted boot/transport payload identities"
    python3 "$ROOT/scripts/v2/audit_phase6_r0.py" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --layout "$LAYOUT" \
        --phase4-env "$PHASE4_ENV" \
        --system "$SYSTEM_IMG"
} | tee "$TMP"

grep -q '^DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_VERIFIED=1$' "$TMP" || \
    fail "Phase5B artifact revalidation marker missing"
grep -q '^DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1$' "$TMP" || \
    fail "clean system source marker missing"
grep -q '^DISKLESS_V2_DISK_VERIFIED=1$' "$TMP" || \
    fail "Android-test disk structural marker missing"
grep -q '^DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1$' "$TMP" || \
    fail "Android-test disk source marker missing"
grep -q '^DISKLESS_V2_PHASE6_R0_ARTIFACT_AUDIT=PASS$' "$TMP" || \
    fail "Phase6 R0 artifact audit marker missing"

{
    cat "$TMP"
    echo
    echo "DISKLESS_V2_PHASE6_R0_HOST_AUDIT=PASS"
    echo "vendor_fstab_sha256=$(sha256sum "$PATCHED_VENDOR" | awk '{print $1}')"
    echo "disk_manifest_sha256=$(sha256sum "$DISK_MANIFEST" | awk '{print $1}')"
    echo "handoff_process_contract=pid1-diskless-init-plus-one-nbd-handler-only"
    echo "diagnostic_children_at_handoff=0"
    echo "android_init_target=/init-unchanged"
    echo "rdinit_target=/diskless-init"
    echo "nbd_selinux_socket_question=resolved-by-pinned-kernel-source"
    echo "real_device_boot=not-performed"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_R0_HOST_AUDIT=PASS"
echo "report=$REPORT"
echo "vendor_fstab_sha256=$(sha256sum "$PATCHED_VENDOR" | awk '{print $1}')"
echo "No Nexus boot was performed. Phase6 hardware remains paused until 6R1 host audit passes."
