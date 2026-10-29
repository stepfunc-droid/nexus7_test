#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
REPO_STOCK_FSTAB="$ROOT/diskless-v2/fstab.flox.stock"
GENERATED_FSTAB="$OUT/fstab.flox"
ARTIFACT_STOCK_FSTAB="$OUT/fstab.artifact.stock"

STOCK_BOOT="${1:-}"
STOCK_VENDOR="${2:-}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ -z "$STOCK_BOOT" || -z "$STOCK_VENDOR" ]]; then
    echo "usage: $0 /path/to/official-lineage-boot.img /path/to/vendor.raw.img" >&2
    exit 2
fi

for tool in python3 sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

[[ -f "$STOCK_BOOT" ]] || fail "stock boot image not found: $STOCK_BOOT"
[[ -f "$STOCK_VENDOR" ]] || fail "stock vendor raw image not found: $STOCK_VENDOR"
[[ -f "$REPO_STOCK_FSTAB" ]] || fail "repository stock fstab snapshot missing: $REPO_STOCK_FSTAB"

mkdir -p "$OUT"

echo "==> Auditing actual ROM boot/vendor fstab sources"
python3 "$ROOT/scripts/v2/audit_android_fstab_sources.py" \
    --boot "$STOCK_BOOT" \
    --vendor "$STOCK_VENDOR" \
    --out-dir "$OUT" \
    --repo-stock "$REPO_STOCK_FSTAB"
[[ -f "$ARTIFACT_STOCK_FSTAB" ]] || fail "verified artifact fstab baseline missing: $ARTIFACT_STOCK_FSTAB"
ARTIFACT_STOCK_SHA="$(sha256sum "$ARTIFACT_STOCK_FSTAB" | awk '{print $1}')"

echo
echo "==> Generating diskless fstab from verified actual-ROM baseline"
python3 "$ROOT/scripts/v2/generate_android_fstab.py" \
    --stock "$ARTIFACT_STOCK_FSTAB" \
    --expected-stock-sha256 "$ARTIFACT_STOCK_SHA" \
    --stock-label "actual-ROM boot/vendor artifact baseline" \
    --output "$GENERATED_FSTAB"

echo
echo "==> Independently validating generated fstab"
python3 "$ROOT/scripts/v2/validate_android_fstab.py" \
    --fstab "$GENERATED_FSTAB"

PATCHED_BOOT="$OUT/boot-fstab-only.img"
PATCHED_VENDOR="$OUT/vendor-fstab.raw.img"
MANIFEST="$OUT/fstab-artifacts-manifest.txt"

rm -f "$PATCHED_BOOT" "$PATCHED_VENDOR" "$MANIFEST"

echo
echo "==> Replacing only /fstab.flox in stock boot ramdisk"
python3 "$ROOT/scripts/v2/patch_boot_fstab.py" \
    --input "$STOCK_BOOT" \
    --stock-fstab "$ARTIFACT_STOCK_FSTAB" \
    --fstab "$GENERATED_FSTAB" \
    --output "$PATCHED_BOOT"

echo
echo "==> Replacing only /etc/fstab.flox file data in vendor raw image copy"
python3 "$ROOT/scripts/v2/patch_vendor_fstab.py" \
    --input "$STOCK_VENDOR" \
    --stock-fstab "$ARTIFACT_STOCK_FSTAB" \
    --fstab "$GENERATED_FSTAB" \
    --output "$PATCHED_VENDOR"

echo
echo "==> Independently validating Phase 5B artifacts"
python3 "$ROOT/scripts/v2/validate_android_fstab_artifacts.py" \
    --stock-boot "$STOCK_BOOT" \
    --patched-boot "$PATCHED_BOOT" \
    --stock-vendor "$STOCK_VENDOR" \
    --patched-vendor "$PATCHED_VENDOR" \
    --stock-fstab "$ARTIFACT_STOCK_FSTAB" \
    --generated-fstab "$GENERATED_FSTAB"

{
    echo "DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_BUILT=1"
    echo "stock_boot=$STOCK_BOOT"
    echo "stock_boot_sha256=$(sha256sum "$STOCK_BOOT" | awk '{print $1}')"
    echo "stock_vendor=$STOCK_VENDOR"
    echo "stock_vendor_sha256=$(sha256sum "$STOCK_VENDOR" | awk '{print $1}')"
    echo "artifact_stock_fstab=$ARTIFACT_STOCK_FSTAB"
    echo "artifact_stock_fstab_sha256=$ARTIFACT_STOCK_SHA"
    echo "generated_fstab=$GENERATED_FSTAB"
    echo "generated_fstab_sha256=$(sha256sum "$GENERATED_FSTAB" | awk '{print $1}')"
    echo "patched_boot=$PATCHED_BOOT"
    echo "patched_boot_sha256=$(sha256sum "$PATCHED_BOOT" | awk '{print $1}')"
    echo "patched_vendor=$PATCHED_VENDOR"
    echo "patched_vendor_sha256=$(sha256sum "$PATCHED_VENDOR" | awk '{print $1}')"
    echo "boot_policy=fstab-only"
    echo "vendor_policy=fstab-only"
    echo "android_init=unchanged"
    echo "v1_rc_bypasses=not-applied"
} > "$MANIFEST"

echo
echo "DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_BUILT=1"
cat "$MANIFEST"
echo "manifest=$MANIFEST"
