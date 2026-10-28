#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
DEFCONFIG="${DEFCONFIG:-lineageos_flo_defconfig}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ -d "$KERNEL_DIR" ]] || fail "kernel tree not found: $KERNEL_DIR"
[[ -f "$KERNEL_DIR/arch/arm/configs/$DEFCONFIG" ]] || \
    fail "defconfig not found: $KERNEL_DIR/arch/arm/configs/$DEFCONFIG"

command -v make >/dev/null 2>&1 || fail "make not found"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"

mkdir -p "$KERNEL_OUT"

echo "==> Resetting kernel config from $DEFCONFIG"
make -C "$KERNEL_DIR" O="$KERNEL_OUT" "$DEFCONFIG"

CONFIG="$KERNEL_OUT/.config"
[[ -f "$CONFIG" ]] || fail "kernel did not produce $CONFIG"

# Change only the symbols that define the diskless architecture. Everything
# else continues to come from the Lineage flo defconfig and olddefconfig.
python3 - "$CONFIG" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text()

wanted = {
    "CONFIG_BLK_DEV_NBD": "y",
    "CONFIG_USB_GADGET": "y",
    "CONFIG_USB_CI13XXX_MSM": "y",
    "CONFIG_USB_ETH": "y",
    "CONFIG_USB_G_ANDROID": "n",
    "CONFIG_ANDROID_RAM_CONSOLE": "y",
    "CONFIG_MSDOS_PARTITION": "y",
    "CONFIG_INET": "y",
    "CONFIG_EXT4_FS": "y",
}

lines = text.splitlines()
index = {}
for i, line in enumerate(lines):
    m = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=", line)
    if m:
        index[m.group(1)] = i
        continue
    m = re.match(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$", line)
    if m:
        index[m.group(1)] = i

for key, value in wanted.items():
    replacement = f"{key}=y" if value == "y" else f"# {key} is not set"
    if key in index:
        lines[index[key]] = replacement
    else:
        index[key] = len(lines)
        lines.append(replacement)

path.write_text("\n".join(lines) + "\n")
PY

# The eMMC removal is a source-level invariant, not a config option.
echo "==> Disabling flo SDCC1/eMMC registration"
KERNEL_DIR="$KERNEL_DIR" bash "$ROOT/patch-lineage-disable-emmc.sh"

# Resolve dependencies after our explicit symbol choices.
echo "==> Running olddefconfig"
make -C "$KERNEL_DIR" O="$KERNEL_OUT" olddefconfig

# Fail early if Kconfig silently changed any architectural invariant.
check_yes() {
    grep -qx "$1=y" "$CONFIG" || fail "Kconfig did not preserve $1=y"
}
check_no() {
    grep -qx "# $1 is not set" "$CONFIG" || fail "Kconfig did not preserve $1=n"
}

check_yes CONFIG_MACH_APQ8064_FLO
check_yes CONFIG_BLK_DEV_NBD
check_yes CONFIG_USB_GADGET
check_yes CONFIG_USB_CI13XXX_MSM
check_yes CONFIG_USB_ETH
check_no  CONFIG_USB_G_ANDROID
check_yes CONFIG_ANDROID_RAM_CONSOLE
check_yes CONFIG_ANDROID_PERSISTENT_RAM
check_yes CONFIG_MSDOS_PARTITION
check_yes CONFIG_INET
check_yes CONFIG_EXT4_FS

echo
echo "Diskless v2 kernel configuration prepared:"
echo "  kernel:   $KERNEL_DIR"
echo "  output:   $KERNEL_OUT"
echo "  config:   $CONFIG"
echo "  defconfig:$DEFCONFIG"
echo
echo "Next: build the kernel, then run scripts/v2/verify_kernel.sh"
