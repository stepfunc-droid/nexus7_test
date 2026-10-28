#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/out"
WORK="$ROOT/.work-lineage-probe"
KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
INIT_SRC="$ROOT/initramfs/lineage-init"
INITRAMFS="$WORK/lineage-usb-initramfs.cpio.gz"
BOOTIMG="$OUT/lineage-usb-probe-mach7801.img"

find_busybox() {
    if [[ -n "${BUSYBOX:-}" && -x "$BUSYBOX" ]]; then
        printf '%s\n' "$BUSYBOX"
        return 0
    fi

    local candidate
    for candidate in \
        "$ROOT/.work-pmos-runtime/initramfs-root/bin/busybox" \
        "$ROOT/.work-pmos-probe/initramfs-root/bin/busybox" \
        "$ROOT/.work-pmos-runtime/root/bin/busybox"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

for tool in python3 cpio gzip grep; do
    command -v "$tool" >/dev/null || {
        echo "ERROR: missing required tool: $tool" >&2
        exit 1
    }
done

[[ -s "$ZIMAGE" ]] || {
    echo "ERROR: Lineage zImage not found: $ZIMAGE" >&2
    echo "Set KERNEL_DIR=/path/to/android_kernel_google_msm if needed." >&2
    exit 1
}

[[ -f "$KERNEL_OUT/.config" ]] || {
    echo "ERROR: kernel config not found: $KERNEL_OUT/.config" >&2
    exit 1
}

if ! grep -q '^CONFIG_BLK_DEV_NBD=y$' "$KERNEL_OUT/.config"; then
    echo "ERROR: CONFIG_BLK_DEV_NBD=y is required" >&2
    exit 1
fi

if ! grep -q '^CONFIG_USB_ETH=y$' "$KERNEL_OUT/.config"; then
    echo "ERROR: CONFIG_USB_ETH=y is required" >&2
    exit 1
fi

if [[ -f "$KERNEL_OUT/include/generated/mach-types.h" ]]; then
    if ! grep -Eq '#define[[:space:]]+MACH_TYPE_APQ8064_FLO[[:space:]]+7801$' \
        "$KERNEL_OUT/include/generated/mach-types.h"; then
        echo "ERROR: kernel is not built for flo machine ID 7801" >&2
        grep 'MACH_TYPE_APQ8064_FLO' "$KERNEL_OUT/include/generated/mach-types.h" || true
        exit 1
    fi
fi

BB="$(find_busybox || true)"
if [[ -z "$BB" ]]; then
    echo "ERROR: static ARM BusyBox not found." >&2
    echo "Set BUSYBOX=/absolute/path/to/static/arm/busybox" >&2
    exit 1
fi

[[ -f "$INIT_SRC" ]] || {
    echo "ERROR: missing init source: $INIT_SRC" >&2
    exit 1
}

mkdir -p "$OUT"
rm -rf "$WORK"
mkdir -p "$WORK/root/bin" "$WORK/root/sbin" "$WORK/root/proc" \
         "$WORK/root/sys" "$WORK/root/dev/pts" "$WORK/root/tmp" "$WORK/root/www"

cp "$BB" "$WORK/root/bin/busybox"
chmod 755 "$WORK/root/bin/busybox"
ln -s busybox "$WORK/root/bin/sh"
cp "$INIT_SRC" "$WORK/root/init"
chmod 755 "$WORK/root/init"

echo "==> Building Lineage probe initramfs"
(
    cd "$WORK/root"
    find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$INITRAMFS"
)

echo "==> Building Android boot image"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$ZIMAGE" \
  --ramdisk "$INITRAMFS" \
  --board flo-lineage-usb \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset 0x02000000 \
  --second_offset 0x00f00000 \
  --tags_offset 0x00000100 \
  --pagesize 2048 \
  --cmdline "console=ttyHSL0,115200,n8 androidboot.hardware=flox user_debug=31 msm_rtb.filter=0x3F ehci-hcd.park=3 vmalloc=340M rdinit=/init loglevel=8 ignore_loglevel panic=0" \
  --output "$BOOTIMG"

[[ -s "$BOOTIMG" ]] || {
    echo "ERROR: boot image was not produced" >&2
    exit 1
}

sha256sum "$BOOTIMG" > "$BOOTIMG.sha256"

echo
echo "Build complete:"
echo "  $BOOTIMG"
echo
echo "RAM-ONLY boot chain (DO NOT FLASH):"
echo "  1) stock fastboot: fastboot boot out/lk2nd-flo-fastboot.img"
echo "  2) patched lk2nd: fastboot boot out/lineage-usb-probe-mach7801.img"
echo "  3) Mac: sudo ifconfig en6 172.16.42.2 netmask 255.255.255.0 up"
echo "  4) Mac: curl http://172.16.42.1:2325/diag.txt"
