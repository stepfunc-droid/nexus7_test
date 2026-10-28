#!/usr/bin/env bash
set -euo pipefail

DIR="${1:-$HOME/nexus7-diskless}"
DATA_SIZE="${DATA_SIZE:-4294967296}"   # 4 GiB logical sparse file by default
CACHE_SIZE=76581888                      # flox BoardConfig: 73 MiB
PERSIST_SIZE=15360000                    # flox BoardConfig: 14.6 MiB

find_mke2fs() {
    local p
    for p in \
        "$(command -v mke2fs 2>/dev/null || true)" \
        /opt/homebrew/opt/e2fsprogs/sbin/mke2fs \
        /usr/local/opt/e2fsprogs/sbin/mke2fs; do
        if [[ -n "$p" && -x "$p" ]]; then
            printf '%s\n' "$p"
            return 0
        fi
    done
    return 1
}

MKE2FS="$(find_mke2fs || true)"
if [[ -z "$MKE2FS" ]]; then
    echo "ERROR: mke2fs not found." >&2
    echo "On macOS: brew install e2fsprogs" >&2
    exit 1
fi

mkdir -p "$DIR"

make_sparse() {
    local path="$1" size="$2"
    python3 - "$path" "$size" <<'PY'
import os, sys
path = os.path.expanduser(sys.argv[1])
size = int(sys.argv[2])
with open(path, 'wb') as f:
    f.truncate(size)
PY
}

format_ext4() {
    local path="$1" size="$2" label="$3"
    if [[ -e "$path" ]]; then
        echo "ERROR: refusing to overwrite existing image: $path" >&2
        exit 1
    fi
    echo "==> $label: $path ($size bytes logical)"
    make_sparse "$path" "$size"
    "$MKE2FS" -q -F -t ext4 -L "$label" \
        -O '^64bit,^metadata_csum,^metadata_csum_seed,^orphan_file,^encrypt,^casefold,^verity' \
        -E lazy_itable_init=0,lazy_journal_init=0 \
        "$path"
}

format_ext4 "$DIR/cache.raw.img" "$CACHE_SIZE" cache
format_ext4 "$DIR/userdata.raw.img" "$DATA_SIZE" data
format_ext4 "$DIR/persist.raw.img" "$PERSIST_SIZE" persist

echo
echo "Created diskless writable images in: $DIR"
ls -lh "$DIR"/*.raw.img
