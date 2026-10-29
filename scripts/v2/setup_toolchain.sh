#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/diskless-v2/toolchain.env"

TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$ROOT/.toolchains/arm-linux-androideabi-4.9}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || fail "git not found"

mkdir -p "$(dirname "$TOOLCHAIN_DIR")"

if [[ ! -d "$TOOLCHAIN_DIR/.git" ]]; then
    [[ ! -e "$TOOLCHAIN_DIR" ]] || fail "toolchain path exists but is not a git repository: $TOOLCHAIN_DIR"
    echo "==> Cloning pinned LineageOS ARM GCC 4.9 toolchain"
    git clone --no-checkout "$TOOLCHAIN_REPOSITORY" "$TOOLCHAIN_DIR"
fi

echo "==> Fetching pinned toolchain commit $TOOLCHAIN_COMMIT"
git -C "$TOOLCHAIN_DIR" fetch --depth 1 origin "$TOOLCHAIN_COMMIT"
git -C "$TOOLCHAIN_DIR" checkout --detach "$TOOLCHAIN_COMMIT"

ACTUAL_COMMIT="$(git -C "$TOOLCHAIN_DIR" rev-parse HEAD)"
[[ "$ACTUAL_COMMIT" == "$TOOLCHAIN_COMMIT" ]] || \
    fail "toolchain HEAD $ACTUAL_COMMIT does not match pinned commit $TOOLCHAIN_COMMIT"

CC="$TOOLCHAIN_DIR/bin/${TOOLCHAIN_PREFIX}gcc"
[[ -x "$CC" ]] || fail "pinned compiler not found: $CC"

VERSION="$($CC -dumpversion)"
case "$VERSION" in
    4.9|4.9.*) ;;
    *) fail "expected GCC 4.9, got $VERSION from $CC" ;;
esac

echo
echo "Diskless v2 toolchain ready:"
echo "  repository: $TOOLCHAIN_REPOSITORY"
echo "  commit:     $ACTUAL_COMMIT"
echo "  compiler:   $($CC --version | head -n 1)"
echo "  prefix:     $TOOLCHAIN_DIR/bin/$TOOLCHAIN_PREFIX"
