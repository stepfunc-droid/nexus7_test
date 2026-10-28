#!/usr/bin/env bash
set -euo pipefail

KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
TARGET="$KERNEL_DIR/arch/arm/mach-msm/asustek/flo/board-flo-storage.c"

[[ -f "$TARGET" ]] || {
  echo "ERROR: flo storage board file not found: $TARGET" >&2
  exit 1
}

OLD='\t\tapq8064_add_sdcc(1, apq8064_sdc1_pdata);'
MARKER='\t\t/* nexus7_test diskless: keep SDCC1/eMMC unregistered */'

if grep -Fq 'nexus7_test diskless: keep SDCC1/eMMC unregistered' "$TARGET"; then
  echo "Already patched: SDCC1/eMMC registration is disabled"
  exit 0
fi

python3 - "$TARGET" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
old = "\t\tapq8064_add_sdcc(1, apq8064_sdc1_pdata);"
new = "\t\t/* nexus7_test diskless: keep SDCC1/eMMC unregistered */\n\t\t/* apq8064_add_sdcc(1, apq8064_sdc1_pdata); */"

count = s.count(old)
if count != 1:
    raise SystemExit(f"ERROR: expected exactly one SDCC1 registration, found {count}")

p.write_text(s.replace(old, new, 1))
PY

echo "Patched: $TARGET"
echo "SDCC1/eMMC will no longer be registered; apq8064_add_uio() and other SDCC controllers are unchanged."
echo
sed -n '/void __init apq8064_init_mmc/,/if (apq8064_sdc2_pdata)/p' "$TARGET" | head -n 12
