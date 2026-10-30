#!/bin/sh
# Stop recognized NBD storage only after verifying Nexus fastboot state.
set -eu
NEXUS7_RELEASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec python3 "$NEXUS7_RELEASE_DIR/nexus7.py" stop-nbd
