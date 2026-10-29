#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DISK="${DISK:-$HOME/nexus7-diskless-v2/diskless-v2.raw.img}"
BIND="${BIND:-0.0.0.0}"
PORT="${PORT:-10810}"

if [[ ! -f "$DISK" ]]; then
    echo "ERROR: disk image not found: $DISK" >&2
    echo "Build it first with scripts/v2/build_disk.sh" >&2
    exit 1
fi

echo "Diskless v2 single NBD export"
echo "  bind: $BIND:$PORT"
echo "  disk: $DISK"
echo "  mode: read-write (system/vendor are protected later by Android fstab RO policy)"
echo

exec python3 "$ROOT/scripts/nbd_test_server.py" \
    --name disk-v2 \
    --bind "$BIND" \
    --port "$PORT" \
    "$DISK"
