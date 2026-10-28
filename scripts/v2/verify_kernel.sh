#!/usr/bin/env bash
set -euo pipefail

KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
CONFIG="$KERNEL_OUT/.config"
ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
STORAGE_SRC="$KERNEL_DIR/arch/arm/mach-msm/asustek/flo/board-flo-storage.c"
MANIFEST="${MANIFEST:-}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

require_file() {
    [[ -f "$1" ]] || fail "required file not found: $1"
}

require_nonempty() {
    [[ -s "$1" ]] || fail "required file missing or empty: $1"
}

require_yes() {
    local key="$1"
    grep -qx "${key}=y" "$CONFIG" || fail "kernel config must contain ${key}=y"
}

require_not_set() {
    local key="$1"
    if grep -qx "${key}=y" "$CONFIG" || grep -qx "${key}=m" "$CONFIG"; then
        fail "kernel config must not enable $key"
    fi
    grep -qx "# ${key} is not set" "$CONFIG" || \
        fail "kernel config must explicitly contain '# ${key} is not set'"
}

for tool in git grep sha256sum awk sed; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

require_file "$CONFIG"
require_nonempty "$ZIMAGE"
require_file "$STORAGE_SRC"

# Machine / storage transport invariants.
require_yes CONFIG_MACH_APQ8064_FLO
require_yes CONFIG_BLK_DEV_NBD
require_yes CONFIG_INET
require_yes CONFIG_EXT4_FS
require_yes CONFIG_MSDOS_PARTITION

# Diskless USB has exactly one gadget owner: g_ether on the flo CI13xxx UDC.
require_yes CONFIG_USB_GADGET
require_yes CONFIG_USB_CI13XXX_MSM
require_yes CONFIG_USB_ETH
require_not_set CONFIG_USB_G_ANDROID

# Crash evidence must survive a panic/reboot independently of USB networking.
require_yes CONFIG_ANDROID_RAM_CONSOLE
require_yes CONFIG_ANDROID_PERSISTENT_RAM

# SDCC1/eMMC must be deliberately removed by the diskless source patch.
if grep -Eq '^[[:space:]]*apq8064_add_sdcc\(1,[[:space:]]*apq8064_sdc1_pdata\);[[:space:]]*$' "$STORAGE_SRC"; then
    fail "SDCC1/eMMC registration is still active in board-flo-storage.c"
fi

grep -Fq 'nexus7_test diskless: keep SDCC1/eMMC unregistered' "$STORAGE_SRC" || \
    fail "expected diskless SDCC1 disable marker not found in board-flo-storage.c"

# Machine ID is a useful guard against accidentally packing the wrong APQ8064 build.
if [[ -f "$KERNEL_OUT/include/generated/mach-types.h" ]]; then
    grep -Eq '#define[[:space:]]+MACH_TYPE_APQ8064_FLO[[:space:]]+7801$' \
        "$KERNEL_OUT/include/generated/mach-types.h" || \
        fail "generated mach-types.h does not define flo machine ID 7801"
fi

KERNEL_COMMIT="$(git -C "$KERNEL_DIR" rev-parse HEAD 2>/dev/null || true)"
[[ -n "$KERNEL_COMMIT" ]] || fail "cannot determine kernel git commit"

if [[ -n "$(git -C "$KERNEL_DIR" status --porcelain --untracked-files=no 2>/dev/null || true)" ]]; then
    KERNEL_DIRTY=yes
else
    KERNEL_DIRTY=no
fi

CONFIG_SHA256="$(sha256sum "$CONFIG" | awk '{print $1}')"
ZIMAGE_SHA256="$(sha256sum "$ZIMAGE" | awk '{print $1}')"
PANIC_TIMEOUT="$(sed -n 's/^CONFIG_PANIC_TIMEOUT=//p' "$CONFIG" | head -n1)"
[[ -n "$PANIC_TIMEOUT" ]] || PANIC_TIMEOUT=unknown

OUTPUT=$(cat <<EOF
DISKLESS_V2_KERNEL_VERIFIED=1
kernel_dir=$KERNEL_DIR
kernel_out=$KERNEL_OUT
kernel_commit=$KERNEL_COMMIT
kernel_dirty=$KERNEL_DIRTY
config_sha256=$CONFIG_SHA256
zimage_sha256=$ZIMAGE_SHA256
config_panic_timeout=$PANIC_TIMEOUT
machine=flo
machine_id=7801
nbd=builtin
usb_gadget=g_ether
usb_android_gadget=disabled
persistent_ram_console=enabled
sdcc1_emmc=disabled
EOF
)

printf '%s\n' "$OUTPUT"

if [[ -n "$MANIFEST" ]]; then
    mkdir -p "$(dirname "$MANIFEST")"
    printf '%s\n' "$OUTPUT" > "$MANIFEST"
    echo "manifest=$MANIFEST"
fi
