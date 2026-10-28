#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
SKIP_CONFIGURE="${SKIP_CONFIGURE:-0}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ -z "${CROSS_COMPILE:-}" ]]; then
    if command -v arm-linux-gnueabihf-gcc >/dev/null 2>&1; then
        CROSS_COMPILE=arm-linux-gnueabihf-
    else
        fail "CROSS_COMPILE is not set and arm-linux-gnueabihf-gcc was not found"
    fi
fi

CC_BIN="${CROSS_COMPILE}gcc"
command -v "$CC_BIN" >/dev/null 2>&1 || fail "cross compiler not found: $CC_BIN"
command -v make >/dev/null 2>&1 || fail "make not found"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum not found"

if [[ "$SKIP_CONFIGURE" != "1" ]]; then
    echo "==> Preparing deterministic diskless-v2 config"
    KERNEL_DIR="$KERNEL_DIR" KERNEL_OUT="$KERNEL_OUT" \
        bash "$ROOT/scripts/v2/configure_kernel.sh"
else
    echo "==> SKIP_CONFIGURE=1: using existing $KERNEL_OUT/.config"
fi

echo "==> Toolchain"
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
    echo "cross_compile=$CROSS_COMPILE"
    echo "compiler=$($CC_BIN --version | head -n 1)"
    echo "build_jobs=$JOBS"
} >> "$MANIFEST"

echo
echo "Diskless v2 kernel build passed verification."
echo "zImage:   $ZIMAGE"
echo "manifest: $MANIFEST"
