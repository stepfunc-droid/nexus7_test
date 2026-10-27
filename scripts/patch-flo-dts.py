#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} <qcom-apq8064-asus-nexus7-flo.dts>")

p = Path(sys.argv[1])
text = p.read_text()

# The DTB is now passed as a separate Qualcomm QCDT entry by lk2nd, so no
# legacy qcom,msm-id property needs to be injected into the Linux DT itself.
# Keep the failing eMMC completely out of Linux. CONFIG_MMC=n in build.sh is
# the second layer of isolation.
emmc_marker = "/* nexus7_test: force eMMC controller off */"
if emmc_marker not in text:
    text += f'''\n\n{emmc_marker}\n&sdcc1 {{\n\tstatus = "disabled";\n}};\n'''

p.write_text(text)
print(f"patched {p}")
