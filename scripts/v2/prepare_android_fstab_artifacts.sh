#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
STOCK_FSTAB="$ROOT/diskless-v2/fstab.flox.stock"
GENERATED_FSTAB="$OUT/fstab.flox"

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
[[ -f "$STOCK_FSTAB" ]] || fail "pinned stock fstab missing: $STOCK_FSTAB"

mkdir -p "$OUT"

# Always regenerate and independently validate the source fstab first. The
# artifact step must never consume a hand-edited output from a previous run.
echo "==> Rebuilding deterministic Android fstab source"
bash "$ROOT/scripts/v2/build_android_fstab.sh"
[[ -f "$GENERATED_FSTAB" ]] || fail "generated fstab missing: $GENERATED_FSTAB"

PATCHED_BOOT="$OUT/boot-fstab-only.img"
PATCHED_VENDOR="$OUT/vendor-fstab.raw.img"
MANIFEST="$OUT/fstab-artifacts-manifest.txt"

rm -f "$PATCHED_BOOT" "$PATCHED_VENDOR" "$MANIFEST"

echo
echo "==> Replacing only /fstab.flox in stock boot ramdisk"
python3 "$ROOT/scripts/v2/patch_boot_fstab.py" \
    --input "$STOCK_BOOT" \
    --fstab "$GENERATED_FSTAB" \
    --output "$PATCHED_BOOT"

echo
echo "==> Replacing only /etc/fstab.flox file data in vendor raw image copy"
python3 "$ROOT/scripts/v2/patch_vendor_fstab.py" \
    --input "$STOCK_VENDOR" \
    --stock-fstab "$STOCK_FSTAB" \
    --fstab "$GENERATED_FSTAB" \
    --output "$PATCHED_VENDOR"

echo
echo "==> Independently validating Phase 5B artifacts"
python3 "$ROOT/scripts/v2/validate_android_fstab_artifacts.py" \
    --stock-boot "$STOCK_BOOT" \
    --patched-boot "$PATCHED_BOOT" \
    --stock-vendor "$STOCK_VENDOR" \
    --patched-vendor "$PATCHED_VENDOR" \
    --stock-fstab "$STOCK_FSTAB" \
    --generated-fstab "$GENERATED_FSTAB"

{
    echo "DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_BUILT=1"
    echo "stock_boot=$STOCK_BOOT"
    echo "stock_boot_sha256=$(sha256sum "$STOCK_BOOT" | awk '{print $1}')"
    echo "patched_boot=$PATCHED_BOOT"
    echo "patched_boot_sha256=$(sha256sum "$PATCHED_BOOT" | awk '{print $1}')"
    echo "stock_vendor=$STOCK_VENDOR"
    echo "stock_vendor_sha256=$(sha256sum "$STOCK_VENDOR" | awk '{print $1}')"
    echo "patched_vendor=$PATCHED_VENDOR"
    echo "patched_vendor_sha256=$(sha256sum "$PATCHED_VENDOR" | awk '{print $1}')"
    echo "generated_fstab=$GENERATED_FSTAB"
    echo "generated_fstab_sha256=$(sha256sum "$GENERATED_FSTAB" | awk '{print $1}')"
    echo "boot_policy=fstab-only"
    echo "vendor_policy=fstab-only"
    echo "android_init=unchanged"
    echo "v1_rc_bypasses=not-applied"
} > "$MANIFEST"

echo
echo "DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_BUILT=1"
cat "$MANIFEST"
echo "manifest=$MANIFEST"
