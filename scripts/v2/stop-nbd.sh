#!/bin/sh
# Stop the local NBD service independently of Nexus device state.
set -eu
NEXUS7_RELEASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec python3 "$NEXUS7_RELEASE_DIR/nexus7.py" stop-nbd
