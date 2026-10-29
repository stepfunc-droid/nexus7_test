#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_kernel_usb_guard.py /path/to/msm_otg.c")

path = Path(sys.argv[1])
text = path.read_text()
marker = "nexus7_test diskless: protect active USB root transport"

if marker in text:
    print("Already patched: diskless USB root-transport guard")
    raise SystemExit(0)

old_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n"""
new_globals = """static bool debug_aca_enabled;\nstatic bool debug_bus_voting_enabled;\nstatic bool mhl_det_in_progress;\n\n/* nexus7_test diskless: protect active USB root transport */\nstatic bool diskless_mode;\nmodule_param_named(diskless_mode, diskless_mode, bool, 0444);\nMODULE_PARM_DESC(diskless_mode,\n\t\t\"keep active USB peripheral root transport out of OTG low power\");\n\nstatic int __init msm_otg_diskless_setup(char *str)\n{\n\tif (str && str[0] == '1')\n\t\tdiskless_mode = true;\n\n\treturn 1;\n}\n__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""

if text.count(old_globals) != 1:
    raise SystemExit("ERROR: unexpected msm_otg globals anchor count")
text = text.replace(old_globals, new_globals, 1)

set_suspend_start = text.find("static int msm_otg_set_suspend(struct usb_phy *phy, int suspend)")
if set_suspend_start < 0:
    raise SystemExit("ERROR: msm_otg_set_suspend not found")
set_suspend_end = text.find("\n}\n", set_suspend_start)
if set_suspend_end < 0:
    raise SystemExit("ERROR: msm_otg_set_suspend end not found")
set_suspend = text[set_suspend_start:set_suspend_end]
old_set_suspend = """\tif (aca_enabled())\n\t\treturn 0;\n\n"""
new_set_suspend = """\tif (aca_enabled())\n\t\treturn 0;\n\n\t/*\n\t * Diskless mode uses this peripheral link as the live root-storage\n\t * transport. Never let a peripheral bus-suspend notification turn\n\t * into an OTG/PHY low-power transition while that policy is active.\n\t */\n\tif (diskless_mode && suspend &&\n\t    phy->state == OTG_STATE_B_PERIPHERAL) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: keeping peripheral PHY active on bus suspend\\n\");\n\t\treturn 0;\n\t}\n\n"""
if set_suspend.count(old_set_suspend) != 1:
    raise SystemExit("ERROR: unexpected msm_otg_set_suspend anchor count")
set_suspend = set_suspend.replace(old_set_suspend, new_set_suspend, 1)
text = text[:set_suspend_start] + set_suspend + text[set_suspend_end:]

suspend_start = text.find("static int msm_otg_suspend(struct msm_otg *motg)")
if suspend_start < 0:
    raise SystemExit("ERROR: msm_otg_suspend not found")
suspend_end = text.find("\n}\n", suspend_start)
if suspend_end < 0:
    raise SystemExit("ERROR: msm_otg_suspend end not found")
suspend_fn = text[suspend_start:suspend_end]
old_suspend = """\tu32 portsc;\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
new_suspend = """\tu32 portsc;\n\n\t/*\n\t * In diskless mode an active B-peripheral session carries the root\n\t * filesystem. Refuse runtime/system OTG LPM even if charger state or\n\t * future platform-data changes would otherwise permit it.\n\t */\n\tif (diskless_mode && phy->state == OTG_STATE_B_PERIPHERAL &&\n\t    test_bit(B_SESS_VLD, &motg->inputs)) {\n\t\tdev_dbg(phy->dev,\n\t\t\t\"diskless: refusing OTG LPM while root transport is active\\n\");\n\t\treturn -EBUSY;\n\t}\n\n\tif (atomic_read(&motg->in_lpm))\n\t\treturn 0;\n"""
if suspend_fn.count(old_suspend) != 1:
    raise SystemExit("ERROR: unexpected msm_otg_suspend anchor count")
suspend_fn = suspend_fn.replace(old_suspend, new_suspend, 1)
text = text[:suspend_start] + suspend_fn + text[suspend_end:]

path.write_text(text)
print("Patched msm_otg.c with explicit diskless USB root-transport guard")
