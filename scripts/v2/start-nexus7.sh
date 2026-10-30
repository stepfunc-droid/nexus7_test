#!/bin/sh
# Verify and RAM-boot lk2nd followed by this release's system boot image.
set -eu
NEXUS7_RELEASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec python3 "$NEXUS7_RELEASE_DIR/nexus7.py" boot
