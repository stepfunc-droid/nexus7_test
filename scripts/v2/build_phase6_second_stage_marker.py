#!/usr/bin/env python3
raise SystemExit(
    "ERROR: build_phase6_second_stage_marker.py is retired.\n"
    "Reason: Phase6 boot ramdisk contains no Android rc files; flo second-stage rc files live in the system-root filesystem after SwitchRoot('/system').\n"
    "Do not patch Android rc files for the Phase6 reset. See diskless-v2/PHASE6_AUDIT.md (6R0-6R3)."
)
