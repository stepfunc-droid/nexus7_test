#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} <qcom-apq8064-asus-nexus7-flo.dts>")

p = Path(sys.argv[1])
text = p.read_text()

# lk2nd's Android fastboot boot path scans appended DTBs using the legacy
# Qualcomm qcom,msm-id property. Modern upstream flo DT uses only compatible
# strings, so lk2nd cannot select it and reports no matching SoC DTB. APQ8064
# is Qualcomm SoC ID 109. A soc_rev of 0 is the generic/default revision and
# is sufficient for lk2nd's SOC_MATCH selection.
msm_id_marker = "/* nexus7_test: lk2nd legacy SoC match */"
if msm_id_marker not in text:
    needle = '/ {\n\tmodel = "Asus Nexus7(flo)";'
    replacement = (
        '/ {\n'
        '\t' + msm_id_marker + '\n'
        '\tqcom,msm-id = <109 0>;\n'
        '\tmodel = "Asus Nexus7(flo)";'
    )
    if needle not in text:
        raise SystemExit("ERROR: flo root node layout changed; cannot insert qcom,msm-id safely")
    text = text.replace(needle, replacement, 1)

# Keep the failing eMMC completely out of Linux even if userspace probes for
# storage later. CONFIG_MMC=n in build.sh is the second layer of isolation.
emmc_marker = "/* nexus7_test: force eMMC controller off */"
if emmc_marker not in text:
    text += f'''\n\n{emmc_marker}\n&sdcc1 {{\n\tstatus = "disabled";\n}};\n'''

p.write_text(text)
print(f"patched {p}")
