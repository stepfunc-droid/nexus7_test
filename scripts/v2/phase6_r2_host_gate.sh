#!/usr/bin/env bash
set -euo pipefail

echo "ERROR: old Phase6 R2 host gate is paused by Audit V2." >&2
echo "Its transport self-tests remain useful, but the old rc-extent stage semantics are revoked." >&2
echo "See diskless-v2/PHASE6_AUDIT_V2.md and diskless-v2/PHASE6_FAILURE_LOG.md." >&2
exit 1
