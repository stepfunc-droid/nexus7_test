#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SYSTEM_IMG="${1:-$HOME/system.raw.img}"
PATCHED_VENDOR="${2:-$ROOT/out/diskless-v2-android/vendor-fstab.raw.img}"
WORK_DIR="${WORK_DIR:-$HOME/nexus7-diskless-v2}"
OUTPUT="${OUTPUT:-$WORK_DIR/diskless-v2-android.raw.img}"
MANIFEST="${MANIFEST:-$OUTPUT.manifest.json}"
COMPONENT_DIR="${COMPONENT_DIR:-$WORK_DIR/components}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ -f "$SYSTEM_IMG" ]] || fail "clean system raw image not found: $SYSTEM_IMG"
[[ -f "$PATCHED_VENDOR" ]] || fail "Phase 5B patched vendor image not found: $PATCHED_VENDOR"

for tool in python3; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

echo "==> Auditing clean system source; v1 rc bypasses must be absent"
python3 "$ROOT/scripts/v2/audit_android_system_source.py" --image "$SYSTEM_IMG"

echo
echo "==> Reassembling separate Android-test single-NBD disk"
SYSTEM_IMG="$SYSTEM_IMG" \
VENDOR_IMG="$PATCHED_VENDOR" \
WORK_DIR="$WORK_DIR" \
COMPONENT_DIR="$COMPONENT_DIR" \
OUTPUT="$OUTPUT" \
MANIFEST="$MANIFEST" \
FORCE=1 \
    bash "$ROOT/scripts/v2/build_disk.sh"

echo
echo "==> Verifying exact system/vendor source bytes inside assembled disk"
python3 "$ROOT/scripts/v2/validate_android_disk_sources.py" \
    --disk "$OUTPUT" \
    --manifest "$MANIFEST" \
    --system "$SYSTEM_IMG" \
    --vendor "$PATCHED_VENDOR"

echo
echo "DISKLESS_V2_ANDROID_DISK_PREPARED=1"
echo "disk=$OUTPUT"
echo "manifest=$MANIFEST"
echo "system_source=$SYSTEM_IMG"
echo "vendor_source=$PATCHED_VENDOR"
echo "transport_baseline_disk=preserved-separately"
