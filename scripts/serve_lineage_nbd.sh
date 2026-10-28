#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEM_IMG="${SYSTEM_IMG:-$HOME/system.raw.img}"
VENDOR_IMG="${VENDOR_IMG:-$HOME/vendor.raw.img}"
RW_DIR="${RW_DIR:-$HOME/nexus7-diskless}"
BIND="${BIND:-0.0.0.0}"

CACHE_IMG="$RW_DIR/cache.raw.img"
USERDATA_IMG="$RW_DIR/userdata.raw.img"
PERSIST_IMG="$RW_DIR/persist.raw.img"
VENDOR_DISKLESS_IMG="${VENDOR_DISKLESS_IMG:-$RW_DIR/vendor.diskless.raw.img}"

for f in "$SYSTEM_IMG" "$VENDOR_IMG" "$CACHE_IMG" "$USERDATA_IMG" "$PERSIST_IMG"; do
    [[ -f "$f" ]] || { echo "ERROR: missing image: $f" >&2; exit 1; }
done

mkdir -p "$RW_DIR"

echo "==> Preparing disposable diskless vendor image"
python3 "$ROOT/scripts/patch_lineage_vendor_devwait.py" \
    "$VENDOR_IMG" "$VENDOR_DISKLESS_IMG"

pids=()
cleanup() {
    local p
    for p in "${pids[@]:-}"; do
        kill "$p" 2>/dev/null || true
    done
}
trap cleanup EXIT INT TERM

start() {
    local port="$1" mode="$2" image="$3" name="$4"
    echo "==> $name: $BIND:$port -> $image ($mode)"
    if [[ "$mode" == "ro" ]]; then
        python3 "$ROOT/scripts/nbd_test_server.py" --bind "$BIND" --port "$port" --readonly "$image" &
    else
        python3 "$ROOT/scripts/nbd_test_server.py" --bind "$BIND" --port "$port" "$image" &
    fi
    pids+=("$!")
}

start 10810 ro "$SYSTEM_IMG" system
start 10811 ro "$VENDOR_DISKLESS_IMG" vendor
start 10812 rw "$CACHE_IMG" cache
start 10813 rw "$USERDATA_IMG" userdata
start 10814 rw "$PERSIST_IMG" persist

echo
echo "All Lineage NBD exports are running. Ctrl-C stops all servers."
echo "Vendor source remains untouched: $VENDOR_IMG"
echo "Diskless vendor copy:          $VENDOR_DISKLESS_IMG"
wait
