#!/bin/sh
# Start this release's normal writable disk; no arguments required.
set -eu
NEXUS7_RELEASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec python3 "$NEXUS7_RELEASE_DIR/nexus7.py" serve "$NEXUS7_RELEASE_DIR/disks/daily.raw.img"
