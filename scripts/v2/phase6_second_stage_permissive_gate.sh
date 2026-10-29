#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: phase6_second_stage_permissive_gate.sh is retired." >&2
echo "Reason: it depends on the invalid Linux 3.4 /dev/kmsg reader contract." >&2
echo "The earlier permissive run remains diagnostic evidence only; it is not an accepted Phase6 gate." >&2
echo "See diskless-v2/PHASE6_AUDIT.md." >&2
exit 2
