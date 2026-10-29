#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAYOUT="${LAYOUT:-$ROOT/diskless-v2/layout.json}"
SYSTEM_IMG="${SYSTEM_IMG:-$HOME/system.nbd.raw.img}"
VENDOR_IMG="${VENDOR_IMG:-$HOME/vendor.nbd.raw.img}"
WORK_DIR="${WORK_DIR:-$HOME/nexus7-diskless-v2}"
COMPONENT_DIR="${COMPONENT_DIR:-$WORK_DIR/components}"
OUTPUT="${OUTPUT:-$WORK_DIR/diskless-v2.raw.img}"
MANIFEST="${MANIFEST:-$OUTPUT.manifest.json}"
FORCE="${FORCE:-0}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

[[ -f "$LAYOUT" ]] || fail "layout not found: $LAYOUT"
[[ -f "$SYSTEM_IMG" ]] || fail "system image not found: $SYSTEM_IMG"
[[ -f "$VENDOR_IMG" ]] || fail "vendor image not found: $VENDOR_IMG"

mkdir -p "$COMPONENT_DIR" "$WORK_DIR"

missing=()
[[ -f "$COMPONENT_DIR/cache.raw.img" ]] || missing+=(cache)
[[ -f "$COMPONENT_DIR/userdata.raw.img" ]] || missing+=(userdata)
[[ -f "$COMPONENT_DIR/persist.raw.img" ]] || missing+=(persist)

if (( ${#missing[@]} )); then
    echo "==> Creating missing Linux-3.4-compatible RW ext4 component images"
    PARTITIONS="${missing[*]}" \
        bash "$ROOT/scripts/create_lineage_rw_images.sh" "$COMPONENT_DIR"
else
    echo "==> Reusing existing RW component images in $COMPONENT_DIR"
fi

args=(
    --layout "$LAYOUT"
    --output "$OUTPUT"
    --manifest "$MANIFEST"
    --source "system_image=$SYSTEM_IMG"
    --source "vendor_image=$VENDOR_IMG"
    --source "cache_image=$COMPONENT_DIR/cache.raw.img"
    --source "userdata_image=$COMPONENT_DIR/userdata.raw.img"
    --source "persist_image=$COMPONENT_DIR/persist.raw.img"
)

if [[ "$FORCE" == "1" ]]; then
    args+=(--force)
fi

echo "==> Assembling one partitioned NBD disk"
python3 "$ROOT/scripts/v2/assemble_disk.py" "${args[@]}"

echo
echo "==> Independently validating final MBR/EBR disk"
python3 "$ROOT/scripts/v2/validate_disk.py" \
    --disk "$OUTPUT" \
    --manifest "$MANIFEST"

echo
echo "Diskless v2 host disk passed validation."
ls -lh "$OUTPUT" "$MANIFEST"
if command -v du >/dev/null 2>&1; then
    echo "allocated host storage: $(du -h "$OUTPUT" | awk '{print $1}')"
fi

echo
echo "Next gate is transport-only: export this single disk and attach it as /dev/nbd0 with nbd.max_part=8."
