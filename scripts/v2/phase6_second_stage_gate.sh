#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: phase6_second_stage_gate.sh is retired." >&2
echo "Reason: both /proc/kmsg and /dev/kmsg based Phase6 progress gates were invalid on the enforcing Linux 3.4 flo path." >&2
echo "Do not use the abandoned rc-marker experiment either." >&2
echo "Phase6 is paused for architecture reset; see diskless-v2/PHASE6_AUDIT.md." >&2
exit 2
