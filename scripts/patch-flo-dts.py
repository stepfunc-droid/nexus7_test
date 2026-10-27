#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} <qcom-apq8064-asus-nexus7-flo.dts>")

p = Path(sys.argv[1])
text = p.read_text()
marker = "/* nexus7_test: force eMMC controller off */"

if marker not in text:
    text += f'''\n\n{marker}\n&sdcc1 {{\n\tstatus = "disabled";\n}};\n'''
    p.write_text(text)

print(f"patched {p}")
