#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: Phase6 full-boot builder is paused pending the 6R0/6R1 architecture reset." >&2
echo "The previous wrapper renamed /init and carried diagnostic processes across the SELinux boundary." >&2
echo "Do not build or boot that architecture. See diskless-v2/PHASE6_AUDIT.md." >&2
exit 2
