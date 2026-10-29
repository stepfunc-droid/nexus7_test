#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/diskless-v2/toolchain.env"

KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
SKIP_CONFIGURE="${SKIP_CONFIGURE:-0}"
TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$ROOT/.toolchains/arm-linux-androideabi-4.9}"
AUTO_SETUP_TOOLCHAIN="${AUTO_SETUP_TOOLCHAIN:-1}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

command -v make >/dev/null 2>&1 || fail "make not found"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum not found"
command -v git >/dev/null 2>&1 || fail "git not found"

CC_BIN="$TOOLCHAIN_DIR/bin/${TOOLCHAIN_PREFIX}gcc"
if [[ ! -x "$CC_BIN" ]]; then
    if [[ "$AUTO_SETUP_TOOLCHAIN" == "1" ]]; then
        echo "==> Pinned GCC 4.9 toolchain is missing; installing it first"
        TOOLCHAIN_DIR="$TOOLCHAIN_DIR" bash "$ROOT/scripts/v2/setup_toolchain.sh"
    else
        fail "pinned compiler not found: $CC_BIN (run scripts/v2/setup_toolchain.sh)"
    fi
fi

[[ -d "$TOOLCHAIN_DIR/.git" ]] || fail "toolchain is not the repository-managed checkout: $TOOLCHAIN_DIR"
ACTUAL_TOOLCHAIN_COMMIT="$(git -C "$TOOLCHAIN_DIR" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_TOOLCHAIN_COMMIT" == "$TOOLCHAIN_COMMIT" ]] || \
    fail "toolchain HEAD $ACTUAL_TOOLCHAIN_COMMIT does not match pinned commit $TOOLCHAIN_COMMIT"

GCC_VERSION="$($CC_BIN -dumpversion)"
case "$GCC_VERSION" in
    4.9|4.9.*) ;;
    *) fail "diskless-v2 requires pinned GCC 4.9; got GCC $GCC_VERSION from $CC_BIN" ;;
esac

CROSS_COMPILE="$TOOLCHAIN_DIR/bin/$TOOLCHAIN_PREFIX"

if [[ "$SKIP_CONFIGURE" != "1" ]]; then
    echo "==> Preparing deterministic diskless-v2 config"
    KERNEL_DIR="$KERNEL_DIR" KERNEL_OUT="$KERNEL_OUT" \
        bash "$ROOT/scripts/v2/configure_kernel.sh"
else
    echo "==> SKIP_CONFIGURE=1: using existing $KERNEL_OUT/.config"
fi

echo "==> Toolchain"
echo "repository: $TOOLCHAIN_REPOSITORY"
echo "commit:     $ACTUAL_TOOLCHAIN_COMMIT"
"$CC_BIN" --version | head -n 1

echo "==> Building flo zImage"
make -C "$KERNEL_DIR" O="$KERNEL_OUT" \
    ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" \
    -j"$JOBS" zImage

ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
[[ -s "$ZIMAGE" ]] || fail "kernel build did not produce $ZIMAGE"

MANIFEST="$ROOT/out/diskless-v2-kernel-manifest.txt"
mkdir -p "$ROOT/out"

KERNEL_DIR="$KERNEL_DIR" \
KERNEL_OUT="$KERNEL_OUT" \
MANIFEST="$MANIFEST" \
    bash "$ROOT/scripts/v2/verify_kernel.sh"

{
    echo "toolchain_repository=$TOOLCHAIN_REPOSITORY"
    echo "toolchain_ref=$TOOLCHAIN_REF"
    echo "toolchain_commit=$ACTUAL_TOOLCHAIN_COMMIT"
    echo "cross_compile=$CROSS_COMPILE"
    echo "compiler=$($CC_BIN --version | head -n 1)"
    echo "compiler_dumpversion=$GCC_VERSION"
    echo "build_jobs=$JOBS"
} >> "$MANIFEST"

echo
echo "Diskless v2 kernel build passed verification."
echo "zImage:   $ZIMAGE"
echo "manifest: $MANIFEST"
