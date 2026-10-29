#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: phase6_second_stage_gate.sh is retired." >&2
echo "Reason: flo's Linux 3.4 /dev/kmsg is not a readable per-reader kernel-log interface." >&2
echo "Use the enforcing second-stage early-init marker diagnostic instead:" >&2
echo "  python3 scripts/v2/build_phase6_second_stage_marker.py --input out/diskless-v2-android/android-full-boot.img --output out/diskless-v2-android/android-full-boot-second-stage-marker.img" >&2
echo "  nc -lk 11001 | tee ~/phase6-second-stage-marker.txt" >&2
echo "  python3 scripts/v2/phase6_second_stage_marker_gate.py" >&2
exit 2
