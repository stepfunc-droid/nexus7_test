#!/usr/bin/env bash
set -euo pipefail

DIR="${1:-$HOME/nexus7-diskless}"
DATA_SIZE="${DATA_SIZE:-4294967296}"   # 4 GiB logical sparse file by default
# flox BoardConfig advertises 76581888 bytes, but the Linux 3.4 NBD client
# exposes oldstyle exports in 4 KiB-aligned capacity. 76581888 is 3072 bytes
# past a 4 KiB boundary, so use the largest aligned size below it.
CACHE_SIZE=76578816
PERSIST_SIZE=15360000                    # flox BoardConfig: 14.6 MiB
PARTITIONS="${PARTITIONS:-cache userdata persist}"

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

# Probe which modern ext4 features this mke2fs understands, and only request
# disabling those. Older Homebrew e2fsprogs versions reject unknown feature
# names even when prefixed with '^'.
CANDIDATE_DISABLE=(64bit metadata_csum metadata_csum_seed orphan_file encrypt casefold verity)
DISABLE=()
TMP_PROBE="$(mktemp -t nexus7-mke2fs-probe.XXXXXX)"
cleanup_probe() { rm -f "$TMP_PROBE"; }
trap cleanup_probe EXIT
truncate -s 16M "$TMP_PROBE"
for feature in "${CANDIDATE_DISABLE[@]}"; do
    if "$MKE2FS" -q -F -t ext4 -O "^$feature" "$TMP_PROBE" >/dev/null 2>&1; then
        DISABLE+=("^$feature")
    fi
    truncate -s 16M "$TMP_PROBE"
done
rm -f "$TMP_PROBE"
trap - EXIT

FEATURE_ARGS=()
if (( ${#DISABLE[@]} )); then
    joined="$(IFS=,; echo "${DISABLE[*]}")"
    FEATURE_ARGS=(-O "$joined")
    echo "mke2fs: $MKE2FS"
    echo "Disabling ext4 features for Linux 3.4: $joined"
else
    echo "mke2fs: $MKE2FS"
    echo "No candidate modern ext4 features need explicit disabling."
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
        "${FEATURE_ARGS[@]}" \
        -E lazy_itable_init=0,lazy_journal_init=0 \
        "$path"
}

want_partition() {
    local needle="$1" p
    for p in $PARTITIONS; do
        [[ "$p" == "$needle" ]] && return 0
    done
    return 1
}

want_partition cache && format_ext4 "$DIR/cache.raw.img" "$CACHE_SIZE" cache
want_partition userdata && format_ext4 "$DIR/userdata.raw.img" "$DATA_SIZE" data
want_partition persist && format_ext4 "$DIR/persist.raw.img" "$PERSIST_SIZE" persist

echo
echo "Created requested diskless images in: $DIR"
for p in cache userdata persist; do
    [[ -f "$DIR/$p.raw.img" ]] && ls -lh "$DIR/$p.raw.img"
done
