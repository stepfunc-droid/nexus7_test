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

KERNEL_COMMIT="$(git -C "$KERNEL_DIR" rev-parse HEAD 2>/dev/null || true)"
[[ -n "$KERNEL_COMMIT" ]] || fail "cannot determine kernel git commit"
[[ "$KERNEL_COMMIT" == "$KERNEL_BASE_COMMIT" ]] || \
    fail "kernel HEAD $KERNEL_COMMIT does not match pinned v2 baseline $KERNEL_BASE_COMMIT"

# The working-tree defconfig is intentionally not trusted or consumed by v2.
# It may contain old experiment edits. All other tracked changes are rejected
# except the exact source transformations independently validated below.
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

# Verify board-flo-storage.c is byte-for-byte equal to the pinned upstream file
# with exactly one deterministic SDCC1 registration replacement.
python3 - "$BASE_STORAGE" "$STORAGE_SRC" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text()
actual = Path(sys.argv[2]).read_text()
old = "\t\tapq8064_add_sdcc(1, apq8064_sdc1_pdata);"
new = (
    "\t\t/* nexus7_test diskless: keep SDCC1/eMMC unregistered */\n"
    "\t\t/* apq8064_add_sdcc(1, apq8064_sdc1_pdata); */"
)
count = base.count(old)
if count != 1:
    raise SystemExit(f"ERROR: pinned storage source has unexpected SDCC1 registration count: {count}")
expected = base.replace(old, new, 1)
if actual != expected:
    raise SystemExit(
        "ERROR: board-flo-storage.c differs from the single allowed v2 SDCC1 patch"
    )
PY

# Independently reconstruct the exact allowed msm_otg.c transformations from
# the pinned upstream file. Do not trust either patcher merely because the
# pathname is allow-listed.
python3 - "$BASE_USB" "$USB_OTG_SRC" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text()
actual = Path(sys.argv[2]).read_text()

# Layer 1: keep the active B-peripheral root transport out of OTG/PHY LPM.
old_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n"""
new_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n\n/* nexus7_test diskless: protect active USB root transport */\nstatic bool diskless_mode;\nmodule_param_named(diskless_mode, diskless_mode, bool, 0444);\nMODULE_PARM_DESC(diskless_mode,\n\t\t\"keep active USB peripheral root transport out of OTG low power\");\n\nstatic int __init msm_otg_diskless_setup(char *str)\n{\n\tif (str && str[0] == '1')\n\t\tdiskless_mode = true;\n\n\treturn 1;\n}\n__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""
if base.count(old_globals) != 1:
    raise SystemExit("ERROR: pinned msm_otg globals anchor changed")
expected = base.replace(old_globals, new_globals, 1)

start = expected.find("static int msm_otg_set_suspend(struct usb_phy *phy, int suspend)")
end = expected.find("\n}\n", start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: pinned msm_otg_set_suspend layout changed")
fn = expected[start:end]
old = """\tif (aca_enabled())\n\t\treturn 0;\n\n"""
new = """\tif (aca_enabled())\n\t\treturn 0;\n\n\t/*\n\t * Diskless mode uses this peripheral link as the live root-storage\n\t * transport. Never let a peripheral bus-suspend notification turn\n\t * into an OTG/PHY low-power transition while that policy is active.\n\t */\n\tif (diskless_mode && suspend &&\n\t    phy->state == OTG_STATE_B_PERIPHERAL) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: keeping peripheral PHY active on bus suspend\\n\");\n\t\treturn 0;\n\t}\n\n"""
if fn.count(old) != 1:
    raise SystemExit("ERROR: pinned msm_otg_set_suspend anchor changed")
fn = fn.replace(old, new, 1)
expected = expected[:start] + fn + expected[end:]

start = expected.find("static int msm_otg_suspend(struct msm_otg *motg)")
end = expected.find("\n}\n", start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: pinned msm_otg_suspend layout changed")
fn = expected[start:end]
old = """\tu32 portsc;\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
new = """\tu32 portsc;\n\n\t/*\n\t * In diskless mode an active B-peripheral session carries the root\n\t * filesystem. Refuse runtime/system OTG LPM even if charger state or\n\t * future platform-data changes would otherwise permit it.\n\t */\n\tif (diskless_mode && phy->state == OTG_STATE_B_PERIPHERAL &&\n\t    test_bit(B_SESS_VLD, &motg->inputs)) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: refusing OTG LPM while root transport is active\\n\");\n\t\treturn -EBUSY;\n\t}\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
if fn.count(old) != 1:
    raise SystemExit("ERROR: pinned msm_otg_suspend anchor changed")
fn = fn.replace(old, new, 1)
expected = expected[:start] + fn + expected[end:]

# Layer 2: reject system suspend at PM_SUSPEND_PREPARE, before freeze/device PM.
old_include = "#include <linux/pm_runtime.h>\n#include <linux/of.h>\n"
new_include = "#include <linux/pm_runtime.h>\n#include <linux/suspend.h>\n#include <linux/of.h>\n"
if expected.count(old_include) != 1:
    raise SystemExit("ERROR: pinned msm_otg include anchor changed")
expected = expected.replace(old_include, new_include, 1)

old_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""
new_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n\n/* nexus7_test diskless: block system suspend before device PM */\nstatic int msm_otg_diskless_pm_notifier(struct notifier_block *nb,\n\t\tunsigned long event, void *unused)\n{\n\tstruct msm_otg *motg = the_msm_otg;\n\n\tif (!diskless_mode || event != PM_SUSPEND_PREPARE)\n\t\treturn NOTIFY_DONE;\n\n\tif (!motg || motg->phy.state != OTG_STATE_B_PERIPHERAL ||\n\t    !test_bit(B_SESS_VLD, &motg->inputs))\n\t\treturn NOTIFY_DONE;\n\n\tdev_warn(motg->phy.dev,\n\t\t\"diskless: blocking system suspend while USB root transport is active\\n\");\n\treturn NOTIFY_BAD;\n}\n\nstatic struct notifier_block msm_otg_diskless_pm_nb = {\n\t.notifier_call = msm_otg_diskless_pm_notifier,\n};\n"""
if expected.count(old_setup) != 1:
    raise SystemExit("ERROR: pinned diskless setup anchor changed")
expected = expected.replace(old_setup, new_setup, 1)

old_init = """static int __init msm_otg_init(void)\n{\n\treturn platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
new_init = """static int __init msm_otg_init(void)\n{\n\tint ret;\n\n\tret = register_pm_notifier(&msm_otg_diskless_pm_nb);\n\tif (ret)\n\t\treturn ret;\n\n\tret = platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n\tif (ret)\n\t\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\n\treturn ret;\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
if expected.count(old_init) != 1:
    raise SystemExit("ERROR: pinned msm_otg module init/exit anchor changed")
expected = expected.replace(old_init, new_init, 1)

if actual != expected:
    raise SystemExit(
        "ERROR: msm_otg.c differs from the exact v2 diskless USB/suspend guards"
    )
PY

KERNEL_SOURCE_STATE=baseline-plus-exact-sdcc1-usb-and-system-suspend-guards

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

# Machine ID is a useful guard against accidentally packing the wrong APQ8064 build.
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
