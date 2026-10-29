#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/diskless-v2/kernel.env"

KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
DEFCONFIG="${DEFCONFIG:-$KERNEL_DEFCONFIG}"
DEFCONFIG_REL="arch/arm/configs/$DEFCONFIG"
STORAGE_REL="arch/arm/mach-msm/asustek/flo/board-flo-storage.c"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ -d "$KERNEL_DIR" ]] || fail "kernel tree not found: $KERNEL_DIR"

for tool in git make python3 grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

ACTUAL_COMMIT="$(git -C "$KERNEL_DIR" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_COMMIT" == "$KERNEL_BASE_COMMIT" ]] || \
    fail "kernel HEAD $ACTUAL_COMMIT does not match pinned v2 baseline $KERNEL_BASE_COMMIT"

# v2 does not trust the working-tree defconfig. Historical experiments may have
# modified it, so the build always reads the pristine defconfig directly from
# the pinned commit. The only tracked source file allowed to differ and affect
# the build is board-flo-storage.c, and verify_kernel.sh later checks that its
# contents equal exactly the repository-managed SDCC1 patch.
check_tracked_changes() {
    local path
    {
        git -C "$KERNEL_DIR" diff --name-only
        git -C "$KERNEL_DIR" diff --cached --name-only
    } | sort -u | while IFS= read -r path; do
        [[ -z "$path" ]] && continue
        case "$path" in
            "$STORAGE_REL") ;;
            "$DEFCONFIG_REL")
                echo "NOTE: ignoring historical working-tree defconfig modification: $path" >&2
                ;;
            *) fail "unexpected tracked kernel source modification: $path" ;;
        esac
    done
}
check_tracked_changes

mkdir -p "$KERNEL_OUT"
CONFIG="$KERNEL_OUT/.config"

echo "==> Kernel baseline verified: $KERNEL_BASE_COMMIT"
echo "==> Loading pristine $DEFCONFIG_REL from pinned commit"
git -C "$KERNEL_DIR" show "$KERNEL_BASE_COMMIT:$DEFCONFIG_REL" > "$CONFIG" || \
    fail "cannot read pinned defconfig $DEFCONFIG_REL from $KERNEL_BASE_COMMIT"

# Change only the symbols that define the diskless architecture. Everything
# else comes from the pinned Lineage flo defconfig snapshot.
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
check_tracked_changes

# This Lineage 3.4 tree predates the newer olddefconfig target. Its Kconfig
# makefile provides oldnoconfig, which is non-interactive and preserves the
# supplied .config while assigning n to any symbols not represented there.
# The checks below then fail closed if Kconfig changes a required v2 invariant.
echo "==> Running ARM oldnoconfig (legacy 3.4 Kconfig)"
make -C "$KERNEL_DIR" O="$KERNEL_OUT" ARCH=arm oldnoconfig

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
echo "  kernel:    $KERNEL_DIR"
echo "  commit:    $ACTUAL_COMMIT"
echo "  output:    $KERNEL_OUT"
echo "  config:    $CONFIG"
echo "  defconfig: $DEFCONFIG_REL @ $KERNEL_BASE_COMMIT (working-tree copy ignored)"
echo "  resolver:  oldnoconfig (legacy 3.4, non-interactive)"
echo
echo "Next: build the kernel, then run scripts/v2/verify_kernel.sh"
