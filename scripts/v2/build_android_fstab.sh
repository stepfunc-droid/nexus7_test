#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT/out/diskless-v2-android}"
FSTAB="$OUT_DIR/fstab.flox"
MANIFEST="$OUT_DIR/fstab-manifest.txt"
LAYOUT="$ROOT/diskless-v2/layout.json"
STOCK="$ROOT/diskless-v2/fstab.flox.stock"
ENV_FILE="$ROOT/diskless-v2/android.env"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 not found"
[[ -f "$LAYOUT" ]] || fail "layout not found: $LAYOUT"
[[ -f "$STOCK" ]] || fail "stock fstab snapshot not found: $STOCK"
[[ -f "$ENV_FILE" ]] || fail "android.env not found: $ENV_FILE"

# shellcheck disable=SC1090
source "$ENV_FILE"

mkdir -p "$OUT_DIR"

echo "==> Generating deterministic diskless Android fstab"
python3 "$ROOT/scripts/v2/generate_android_fstab.py" \
    --layout "$LAYOUT" \
    --stock "$STOCK" \
    --env "$ENV_FILE" \
    --output "$FSTAB"

echo
echo "==> Independently validating generated fstab"
VERIFY_OUTPUT="$(python3 "$ROOT/scripts/v2/validate_android_fstab.py" --layout "$LAYOUT" --fstab "$FSTAB")"
printf '%s\n' "$VERIFY_OUTPUT"
grep -q '^DISKLESS_V2_ANDROID_FSTAB_VERIFIED=1$' <<<"$VERIFY_OUTPUT" || \
    fail "generated fstab did not pass validation"

read -r FSTAB_SHA LAYOUT_SHA STOCK_SHA <<EOF
$(python3 - "$FSTAB" "$LAYOUT" "$STOCK" <<'PY'
import hashlib
import sys
from pathlib import Path
print(*(hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sys.argv[1:]))
PY
)
EOF

cat > "$MANIFEST" <<EOF
DISKLESS_V2_ANDROID_FSTAB_BUILT=1
android_device_repository=$ANDROID_DEVICE_REPOSITORY
android_device_ref=$ANDROID_DEVICE_REF
android_device_commit=$ANDROID_DEVICE_BASE_COMMIT
stock_fstab_path=$ANDROID_FSTAB_PATH
stock_fstab_sha256=$STOCK_SHA
layout_sha256=$LAYOUT_SHA
fstab=$FSTAB
fstab_sha256=$FSTAB_SHA
system=/dev/nbd0p1
vendor=/dev/nbd0p2
cache=/dev/nbd0p3
userdata=/dev/nbd0p5
persist=/dev/nbd0p6
metadata=/dev/nbd0p7
vendor_policy=ro-no-check-no-format
userdata_metadata_policy=encryptable-/dev/nbd0p7
emmc_references=absent
f2fs_fallbacks=absent
EOF

echo
echo "==> Generated fstab"
cat "$FSTAB"
echo
echo "DISKLESS_V2_ANDROID_FSTAB_BUILT=1"
echo "fstab=$FSTAB"
echo "manifest=$MANIFEST"
echo "fstab_sha256=$FSTAB_SHA"
