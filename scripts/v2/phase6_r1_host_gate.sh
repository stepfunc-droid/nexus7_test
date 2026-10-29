#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: revoked Phase6 R1 host gate." >&2
echo "The old gate passed an image that failed on real hardware before NBD attach." >&2
echo "Do not boot phase6-r1-full-boot.img." >&2
echo "See diskless-v2/PHASE6_AUDIT_V2.md and diskless-v2/PHASE6_FAILURE_LOG.md." >&2
exit 1
