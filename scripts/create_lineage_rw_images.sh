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

# Different e2fsprogs releases recognize different ext4 feature names.
# Probe each feature independently with mke2fs -n, then disable only the
# features understood by the installed version.  This keeps the resulting
# filesystem compatible with the flo 3.4 kernel without making the script
# depend on one particular Homebrew e2fsprogs release.
probe_disable_features() {
    local probe="$DIR/.mke2fs-feature-probe.$$"
    local feature
    local -a supported=()
    make_sparse "$probe" 16777216

    for feature in 64bit metadata_csum metadata_csum_seed orphan_file encrypt casefold verity; do
        if "$MKE2FS" -n -q -F -t ext4 -O "^$feature" "$probe" >/dev/null 2>&1; then
            supported+=("^$feature")
        fi
    done
    rm -f "$probe"

    local joined=""
    if ((${#supported[@]})); then
        local IFS=,
        joined="${supported[*]}"
    fi
    printf '%s\n' "$joined"
}

DISABLE_FEATURES="$(probe_disable_features)"
echo "mke2fs: $MKE2FS"
if [[ -n "$DISABLE_FEATURES" ]]; then
    echo "Disabling ext4 features for Linux 3.4: $DISABLE_FEATURES"
else
    echo "No incompatible optional ext4 features recognized by this mke2fs"
fi

format_ext4() {
    local path="$1" size="$2" label="$3"
    local tmp="${path}.tmp.$$"

    if [[ -e "$path" ]]; then
        echo "ERROR: refusing to overwrite existing image: $path" >&2
        echo "Remove it explicitly if it is from a failed previous run." >&2
        exit 1
    fi

    rm -f "$tmp"
    trap 'rm -f "$tmp"' RETURN

    echo "==> $label: $path ($size bytes logical)"
    make_sparse "$tmp" "$size"

    local -a cmd=("$MKE2FS" -q -F -t ext4 -L "$label")
    if [[ -n "$DISABLE_FEATURES" ]]; then
        cmd+=( -O "$DISABLE_FEATURES" )
    fi
    cmd+=( -E lazy_itable_init=0,lazy_journal_init=0 "$tmp" )
    "${cmd[@]}"

    # Verify the ext superblock magic before publishing the image.
    python3 - "$tmp" <<'PY'
import sys
p = sys.argv[1]
with open(p, 'rb') as f:
    f.seek(1080)
    magic = f.read(2)
if magic != b'\x53\xef':
    raise SystemExit(f'bad ext filesystem magic: {magic.hex()}')
PY

    mv "$tmp" "$path"
    trap - RETURN
}

format_ext4 "$DIR/cache.raw.img" "$CACHE_SIZE" cache
format_ext4 "$DIR/userdata.raw.img" "$DATA_SIZE" data
format_ext4 "$DIR/persist.raw.img" "$PERSIST_SIZE" persist

echo
echo "Created diskless writable images in: $DIR"
ls -lh "$DIR"/*.raw.img
