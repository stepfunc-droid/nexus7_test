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
REPORT="${REPORT:-$OUT/phase6-v2-frozen-facts.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in \
    "$STOCK_BOOT" "$ANDROID_BOOT" "$STOCK_VENDOR" "$PATCHED_VENDOR" \
    "$STOCK_FSTAB" "$GENERATED_FSTAB" "$SYSTEM_IMG" "$TRANSPORT_BOOT" \
    "$ANDROID_DISK" "$DISK_MANIFEST" "$LAYOUT" "$PHASE4_ENV"; do
    [[ -f "$f" ]] || fail "required frozen-fact input not found: $f"
done

mkdir -p "$OUT"
TMP="$(mktemp "${TMPDIR:-/tmp}/phase6-v2-facts.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

{
    python3 "$ROOT/scripts/v2/validate_android_fstab_artifacts.py" \
        --stock-boot "$STOCK_BOOT" \
        --patched-boot "$ANDROID_BOOT" \
        --stock-vendor "$STOCK_VENDOR" \
        --patched-vendor "$PATCHED_VENDOR" \
        --stock-fstab "$STOCK_FSTAB" \
        --generated-fstab "$GENERATED_FSTAB"

    python3 "$ROOT/scripts/v2/audit_android_system_source.py" \
        --image "$SYSTEM_IMG"

    python3 "$ROOT/scripts/v2/validate_disk.py" \
        --disk "$ANDROID_DISK" \
        --manifest "$DISK_MANIFEST"

    python3 "$ROOT/scripts/v2/validate_android_disk_sources.py" \
        --disk "$ANDROID_DISK" \
        --manifest "$DISK_MANIFEST" \
        --system "$SYSTEM_IMG" \
        --vendor "$PATCHED_VENDOR"

    # audit_phase6_r0.py contains valid artifact identity checks plus historical
    # informational design printouts.  Capture it here, but accept only its
    # artifact marker; Audit V2 does not inherit its old handoff design text.
    python3 "$ROOT/scripts/v2/audit_phase6_r0.py" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --layout "$LAYOUT" \
        --phase4-env "$PHASE4_ENV" \
        --system "$SYSTEM_IMG"
} > "$TMP"

grep -q '^DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_VERIFIED=1$' "$TMP" || \
    fail "Phase5 fstab artifact fact marker missing"
grep -q '^DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1$' "$TMP" || \
    fail "clean system fact marker missing"
grep -q '^DISKLESS_V2_DISK_VERIFIED=1$' "$TMP" || \
    fail "disk structural fact marker missing"
grep -q '^DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1$' "$TMP" || \
    fail "disk source-byte fact marker missing"
grep -q '^DISKLESS_V2_PHASE6_R0_ARTIFACT_AUDIT=PASS$' "$TMP" || \
    fail "artifact identity fact marker missing"

# Extract only factual identity lines; do not propagate old R0 design targets.
{
    echo "DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS"
    grep -E '^(android_boot_sha256|transport_boot_sha256|kernel_sha256|android_init_path|android_init_sha256|generated_fstab_sha256|system_sha256|busybox_sha256|busybox_source|boot_ramdisk_android_rc_entries)=' "$TMP" || true
    echo "vendor_fstab_sha256=$(sha256sum "$PATCHED_VENDOR" | awk '{print $1}')"
    echo "disk_manifest_sha256=$(sha256sum "$DISK_MANIFEST" | awk '{print $1}')"
    echo "phase1_5_acceptance_boundary=2e5a6ba791816bcf746ae53817122f9fb916b2f8"
    echo "runtime_design_claims=none"
    echo "real_device_boot=not-performed"
} > "$REPORT"

cat "$REPORT"
echo "report=$REPORT"
