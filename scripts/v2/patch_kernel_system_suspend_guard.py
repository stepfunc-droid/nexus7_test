#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_kernel_system_suspend_guard.py /path/to/msm_otg.c")

path = Path(sys.argv[1])
text = path.read_text()
marker = "nexus7_test diskless: block system suspend before device PM"

if marker in text:
    print("Already patched: diskless system-suspend guard")
    raise SystemExit(0)

usb_marker = "nexus7_test diskless: protect active USB root transport"
if usb_marker not in text:
    raise SystemExit("ERROR: base diskless USB guard must be applied first")

old_include = "#include <linux/pm_runtime.h>\n#include <linux/of.h>\n"
new_include = "#include <linux/pm_runtime.h>\n#include <linux/suspend.h>\n#include <linux/of.h>\n"
if text.count(old_include) != 1:
    raise SystemExit("ERROR: unexpected msm_otg include anchor count")
text = text.replace(old_include, new_include, 1)

old_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n"""
new_setup = """__setup(\"androidboot.diskless=\", msm_otg_diskless_setup);\n\n/* nexus7_test diskless: block system suspend before device PM */\nstatic int msm_otg_diskless_pm_notifier(struct notifier_block *nb,\n\t\tunsigned long event, void *unused)\n{\n\tif (!diskless_mode || event != PM_SUSPEND_PREPARE)\n\t\treturn NOTIFY_DONE;\n\n\t/*\n\t * Root storage is carried over USB Ethernet/NBD. Suspend-to-RAM cannot\n\t * preserve that transport without an explicit reconnect/resume protocol,\n\t * so reject system suspend before process freezing or device PM starts.\n\t */\n\tpr_warn(\"diskless: blocking system suspend before device PM\\n\");\n\treturn NOTIFY_BAD;\n}\n\nstatic struct notifier_block msm_otg_diskless_pm_nb = {\n\t.notifier_call = msm_otg_diskless_pm_notifier,\n};\n"""
if text.count(old_setup) != 1:
    raise SystemExit("ERROR: unexpected diskless setup anchor count")
text = text.replace(old_setup, new_setup, 1)

old_init = """static int __init msm_otg_init(void)\n{\n\treturn platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
new_init = """static int __init msm_otg_init(void)\n{\n\tint ret;\n\n\tret = register_pm_notifier(&msm_otg_diskless_pm_nb);\n\tif (ret)\n\t\treturn ret;\n\n\tret = platform_driver_probe(&msm_otg_driver, msm_otg_probe);\n\tif (ret)\n\t\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\n\treturn ret;\n}\n\nstatic void __exit msm_otg_exit(void)\n{\n\tunregister_pm_notifier(&msm_otg_diskless_pm_nb);\n\tplatform_driver_unregister(&msm_otg_driver);\n}\n"""
if text.count(old_init) != 1:
    raise SystemExit("ERROR: unexpected msm_otg module init/exit anchor count")
text = text.replace(old_init, new_init, 1)

path.write_text(text)
print("Patched msm_otg.c with early diskless system-suspend guard")
