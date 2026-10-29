#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/diskless-v2/kernel.env"

KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
CONFIG="$KERNEL_OUT/.config"
ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
DEFCONFIG_REL="arch/arm/configs/$KERNEL_DEFCONFIG"
STORAGE_REL="arch/arm/mach-msm/asustek/flo/board-flo-storage.c"
STORAGE_SRC="$KERNEL_DIR/$STORAGE_REL"
USB_OTG_REL="drivers/usb/otg/msm_otg.c"
USB_OTG_SRC="$KERNEL_DIR/$USB_OTG_REL"
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

for tool in git grep sha256sum awk sed sort python3 mktemp; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

require_file "$CONFIG"
require_nonempty "$ZIMAGE"
require_file "$STORAGE_SRC"
require_file "$USB_OTG_SRC"
require_file "$ROOT/scripts/v2/verify_kernel_sources.py"

KERNEL_COMMIT="$(git -C "$KERNEL_DIR" rev-parse HEAD 2>/dev/null || true)"
[[ -n "$KERNEL_COMMIT" ]] || fail "cannot determine kernel git commit"
[[ "$KERNEL_COMMIT" == "$KERNEL_BASE_COMMIT" ]] || \
    fail "kernel HEAD $KERNEL_COMMIT does not match pinned v2 baseline $KERNEL_BASE_COMMIT"

CHANGED_TRACKED="$({
    git -C "$KERNEL_DIR" diff --name-only
    git -C "$KERNEL_DIR" diff --cached --name-only
} | sort -u | sed '/^$/d')"

DEFCONFIG_DIRTY=no
if [[ -n "$CHANGED_TRACKED" ]]; then
    while IFS= read -r path; do
        case "$path" in
            "$STORAGE_REL"|"$USB_OTG_REL") ;;
            "$DEFCONFIG_REL") DEFCONFIG_DIRTY=yes ;;
            *) fail "unexpected tracked kernel source modification: $path" ;;
        esac
    done <<< "$CHANGED_TRACKED"
fi

BASE_STORAGE="$(mktemp)"
BASE_USB="$(mktemp)"
trap 'rm -f "$BASE_STORAGE" "$BASE_USB"' EXIT

git -C "$KERNEL_DIR" show "$KERNEL_BASE_COMMIT:$STORAGE_REL" > "$BASE_STORAGE" || \
    fail "cannot read pinned $STORAGE_REL"
git -C "$KERNEL_DIR" show "$KERNEL_BASE_COMMIT:$USB_OTG_REL" > "$BASE_USB" || \
    fail "cannot read pinned $USB_OTG_REL"

SOURCE_VERIFY_OUTPUT="$(python3 "$ROOT/scripts/v2/verify_kernel_sources.py" \
    "$BASE_STORAGE" "$STORAGE_SRC" "$BASE_USB" "$USB_OTG_SRC")"
printf '%s\n' "$SOURCE_VERIFY_OUTPUT"
grep -q '^DISKLESS_V2_KERNEL_SOURCE_TRANSFORMS_VERIFIED=1$' <<<"$SOURCE_VERIFY_OUTPUT" || \
    fail "kernel source transform verifier did not pass"

KERNEL_SOURCE_STATE=baseline-plus-exact-sdcc1-usb-and-system-suspend-guards

require_yes CONFIG_MACH_APQ8064_FLO
require_yes CONFIG_BLK_DEV_NBD
require_yes CONFIG_INET
require_yes CONFIG_EXT4_FS
require_yes CONFIG_MSDOS_PARTITION

require_yes CONFIG_USB_GADGET
require_yes CONFIG_USB_CI13XXX_MSM
require_yes CONFIG_USB_ETH
require_not_set CONFIG_USB_G_ANDROID

require_yes CONFIG_ANDROID_RAM_CONSOLE
require_yes CONFIG_ANDROID_PERSISTENT_RAM

if [[ -f "$KERNEL_OUT/include/generated/mach-types.h" ]]; then
    grep -Eq '#define[[:space:]]+MACH_TYPE_APQ8064_FLO[[:space:]]+7801$' \
        "$KERNEL_OUT/include/generated/mach-types.h" || \
        fail "generated mach-types.h does not define flo machine ID 7801"
fi

CONFIG_SHA256="$(sha256sum "$CONFIG" | awk '{print $1}')"
ZIMAGE_SHA256="$(sha256sum "$ZIMAGE" | awk '{print $1}')"
PANIC_TIMEOUT="$(sed -n 's/^CONFIG_PANIC_TIMEOUT=//p' "$CONFIG" | head -n1)"
[[ -n "$PANIC_TIMEOUT" ]] || PANIC_TIMEOUT=unknown

OUTPUT=$(cat <<EOF
DISKLESS_V2_KERNEL_VERIFIED=1
kernel_repository=$KERNEL_REPOSITORY
kernel_ref=$KERNEL_REF
kernel_dir=$KERNEL_DIR
kernel_out=$KERNEL_OUT
kernel_commit=$KERNEL_COMMIT
kernel_source_state=$KERNEL_SOURCE_STATE
working_tree_defconfig_dirty=$DEFCONFIG_DIRTY
config_source=pinned-git-object:$KERNEL_BASE_COMMIT:$DEFCONFIG_REL
config_sha256=$CONFIG_SHA256
zimage_sha256=$ZIMAGE_SHA256
config_panic_timeout=$PANIC_TIMEOUT
machine=flo
machine_id=7801
nbd=builtin
usb_gadget=g_ether
usb_android_gadget=disabled
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
usb_system_suspend_guard=pm_notifier
usb_system_suspend_stage=PM_SUSPEND_PREPARE
system_suspend_policy=blocked-in-diskless-mode
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
