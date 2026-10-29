#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 5:
    raise SystemExit(
        "usage: verify_kernel_sources.py BASE_STORAGE ACTUAL_STORAGE BASE_USB ACTUAL_USB"
    )

base_storage = Path(sys.argv[1]).read_text()
actual_storage = Path(sys.argv[2]).read_text()
base_usb = Path(sys.argv[3]).read_text()
actual_usb = Path(sys.argv[4]).read_text()

# SDCC1/eMMC: exactly one deterministic source transformation.
old = "\t\tapq8064_add_sdcc(1, apq8064_sdc1_pdata);"
new = (
    "\t\t/* nexus7_test diskless: keep SDCC1/eMMC unregistered */\n"
    "\t\t/* apq8064_add_sdcc(1, apq8064_sdc1_pdata); */"
)
if base_storage.count(old) != 1:
    raise SystemExit(
        f"ERROR: pinned storage source has unexpected SDCC1 registration count: {base_storage.count(old)}"
    )
expected_storage = base_storage.replace(old, new, 1)
if actual_storage != expected_storage:
    raise SystemExit(
        "ERROR: board-flo-storage.c differs from the single allowed v2 SDCC1 patch"
    )

# msm_otg.c layer 1: explicit USB root-transport low-power guard.
old_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n"""
new_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n\n/* nexus7_test diskless: protect active USB root transport */\nstatic bool diskless_mode;\nmodule_param_named(diskless_mode, diskless_mode, bool, 0444);\nMODULE_PARM_DESC(diskless_mode,\n\t\t\"keep active USB peripheral root transport out of OTG low power\");\n\nstatic int __init msm_otg_diskless_setup(char *str)\n{\n\tif (str && str[0] == '1')\n\t\tdiskless_mode = true;\n\n\treturn 1;\n}\n__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""
if base_usb.count(old_globals) != 1:
    raise SystemExit("ERROR: pinned msm_otg globals anchor changed")
expected_usb = base_usb.replace(old_globals, new_globals, 1)

start = expected_usb.find("static int msm_otg_set_suspend(struct usb_phy *phy, int suspend)")
end = expected_usb.find("\n}\n", start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: pinned msm_otg_set_suspend layout changed")
fn = expected_usb[start:end]
old = """\tif (aca_enabled())\n\t\treturn 0;\n\n"""
new = """\tif (aca_enabled())\n\t\treturn 0;\n\n\t/*\n\t * Diskless mode uses this peripheral link as the live root-storage\n\t * transport. Never let a peripheral bus-suspend notification turn\n\t * into an OTG/PHY low-power transition while that policy is active.\n\t */\n\tif (diskless_mode && suspend &&\n\t    phy->state == OTG_STATE_B_PERIPHERAL) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: keeping peripheral PHY active on bus suspend\\n\");\n\t\treturn 0;\n\t}\n\n"""
if fn.count(old) != 1:
    raise SystemExit("ERROR: pinned msm_otg_set_suspend anchor changed")
fn = fn.replace(old, new, 1)
expected_usb = expected_usb[:start] + fn + expected_usb[end:]

start = expected_usb.find("static int msm_otg_suspend(struct msm_otg *motg)")
end = expected_usb.find("\n}\n", start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: pinned msm_otg_suspend layout changed")
fn = expected_usb[start:end]
old = """\tu32 portsc;\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
new = """\tu32 portsc;\n\n\t/*\n\t * In diskless mode an active B-peripheral session carries the root\n\t * filesystem. Refuse runtime/system OTG LPM even if charger state or\n\t * future platform-data changes would otherwise permit it.\n\t */\n\tif (diskless_mode && phy->state == OTG_STATE_B_PERIPHERAL &&\n\t    test_bit(B_SESS_VLD, &motg->inputs)) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: refusing OTG LPM while root transport is active\\n\");\n\t\treturn -EBUSY;\n\t}\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
if fn.count(old) != 1:
    raise SystemExit("ERROR: pinned msm_otg_suspend anchor changed")
fn = fn.replace(old, new, 1)
expected_usb = expected_usb[:start] + fn + expected_usb[end:]

# msm_otg.c layer 2: reject all system suspend at PM_SUSPEND_PREPARE when
# androidboot.diskless=1, before process freezing or any device PM callbacks.
old_include = "#include <linux/pm_runtime.h>\n#include <linux/of.h>\n"
new_include = "#include <linux/pm_runtime.h>\n#include <linux/suspend.h>\n#include <linux/of.h>\n"
if expected_usb.count(old_include) != 1:
    raise SystemExit("ERROR: pinned msm_otg include anchor changed")
expected_usb = expected_usb.replace(old_include, new_include, 1)

old_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""
new_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n\n/* nexus7_test diskless: block system suspend before device PM */\nstatic int msm_otg_diskless_pm_notifier(struct notifier_block *nb,\n\t\tunsigned long event, void *unused)\n{\n\tif (!diskless_mode || event != PM_SUSPEND_PREPARE)\n\t\treturn NOTIFY_DONE;\n\n\t/*\n\t * Root storage is carried over USB Ethernet/NBD. Suspend-to-RAM cannot\n\t * preserve that transport without an explicit reconnect/resume protocol,\n\t * so reject system suspend before process freezing or device PM starts.\n\t */\n\tpr_warn(\"diskless: blocking system suspend before device PM\\n\");\n\treturn NOTIFY_BAD;\n}\n\nstatic struct notifier_block msm_otg_diskless_pm_nb = {\n\t.notifier_call = msm_otg_diskless_pm_notifier,\n};\n"""
if expected_usb.count(old_setup) != 1:
    raise SystemExit("ERROR: pinned diskless setup anchor changed")
expected_usb = expected_usb.replace(old_setup, new_setup, 1)

old_init = """static int __init msm_otg_init(void)\n{\n\treturn platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
new_init = """static int __init msm_otg_init(void)\n{\n\tint ret;\n\n\tret = register_pm_notifier(&msm_otg_diskless_pm_nb);\n\tif (ret)\n\t\treturn ret;\n\n\tret = platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n\tif (ret)\n\t\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\n\treturn ret;\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
if expected_usb.count(old_init) != 1:
    raise SystemExit("ERROR: pinned msm_otg module init/exit anchor changed")
expected_usb = expected_usb.replace(old_init, new_init, 1)

if actual_usb != expected_usb:
    raise SystemExit(
        "ERROR: msm_otg.c differs from the exact v2 diskless USB/system-suspend guards"
    )

print("DISKLESS_V2_KERNEL_SOURCE_TRANSFORMS_VERIFIED=1")
