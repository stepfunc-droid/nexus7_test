#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$ROOT/.work"
OUT="$ROOT/out"
KERNEL_VERSION="${KERNEL_VERSION:-6.6}"
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
CROSS_COMPILE="${CROSS_COMPILE:-arm-linux-gnueabihf-}"
JOBS="${JOBS:-$(nproc)}"

rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT"

for tool in make "${CROSS_COMPILE}gcc" cpio gzip python3 wget tar; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done

# -----------------------------
# 1) Build a tiny ARM initramfs
# -----------------------------
INITROOT="$WORK/initramfs"
mkdir -p "$INITROOT"/{bin,sbin,etc,proc,sys,dev,tmp,run,root,usr/bin,usr/sbin}

if [[ -n "${BUSYBOX_ARM:-}" ]]; then
  BUSYBOX_SRC="$BUSYBOX_ARM"
else
  BB_TAR="$WORK/busybox-${BUSYBOX_VERSION}.tar.bz2"
  BB_SRC="$WORK/busybox-${BUSYBOX_VERSION}"
  wget -q "https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2" -O "$BB_TAR"
  tar -xjf "$BB_TAR" -C "$WORK"

  pushd "$BB_SRC" >/dev/null
  make distclean >/dev/null 2>&1 || true
  make defconfig >/dev/null
  sed -i 's/^# CONFIG_STATIC is not set$/CONFIG_STATIC=y/' .config
  # BusyBox 1.36's tc applet no longer builds against modern Linux UAPI
  # headers (CBQ was removed). We do not need tc in the rescue initramfs.
  sed -i 's/^CONFIG_TC=y$/# CONFIG_TC is not set/' .config
  make -j"$JOBS" CROSS_COMPILE="$CROSS_COMPILE" >/dev/null
  BUSYBOX_SRC="$BB_SRC/busybox"
  popd >/dev/null
fi

[[ -x "$BUSYBOX_SRC" ]] || { echo "static ARM BusyBox was not produced" >&2; exit 1; }
cp "$BUSYBOX_SRC" "$INITROOT/bin/busybox"
chmod 0755 "$INITROOT/bin/busybox"
cp "$ROOT/initramfs/init" "$INITROOT/init"
chmod 0755 "$INITROOT/init"

# Only create applet links we actually use. The ARM binary cannot be executed on
# the x86 build host to ask BusyBox for its applet list.
for applet in sh mount mkdir cat echo sleep ls head ifconfig telnetd grep uname ln; do
  ln -s busybox "$INITROOT/bin/$applet"
done

(
  cd "$INITROOT"
  find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -9 > "$WORK/initramfs.cpio.gz"
)

# -----------------------------
# 2) Build Linux for flo
# -----------------------------
KERNEL_TAR="$WORK/linux-${KERNEL_VERSION}.tar.xz"
KERNEL="$WORK/linux-${KERNEL_VERSION}"
wget -q "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz" -O "$KERNEL_TAR"
tar -xJf "$KERNEL_TAR" -C "$WORK"

python3 "$ROOT/scripts/patch-flo-dts.py" \
  "$KERNEL/arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts"

pushd "$KERNEL" >/dev/null

make ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" multi_v7_defconfig

# Direct stock-bootloader handoff with an appended DTB.
scripts/config --enable ARM_APPENDED_DTB
scripts/config --enable ARM_ATAG_DTB_COMPAT
scripts/config --enable BLK_DEV_INITRD
scripts/config --enable DEVTMPFS
scripts/config --enable DEVTMPFS_MOUNT
scripts/config --enable TMPFS
scripts/config --enable PROC_FS
scripts/config --enable SYSFS
scripts/config --enable CONFIGFS_FS
scripts/config --enable INET

# Belt-and-suspenders eMMC isolation: even if a DT mistake slips through,
# there is no MMC subsystem in this test kernel.
scripts/config --disable MMC

# USB gadget Ethernet so the host can reach a shell after fastboot hands the
# cable over from the bootloader to Linux.
scripts/config --enable USB_GADGET
scripts/config --enable USB_CONFIGFS
scripts/config --enable USB_CONFIGFS_ECM
scripts/config --enable USB_CHIPIDEA
scripts/config --enable USB_CHIPIDEA_UDC
scripts/config --enable USB_CHIPIDEA_MSM
scripts/config --enable PHY_QCOM_USB_HS

make ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" olddefconfig

# Fail loudly if the properties that matter most were lost to dependency
# resolution.
grep -q '^# CONFIG_MMC is not set$' .config || {
  echo "ERROR: CONFIG_MMC was not disabled" >&2
  exit 1
}
grep -q '^CONFIG_ARM_APPENDED_DTB=y$' .config || {
  echo "ERROR: CONFIG_ARM_APPENDED_DTB is not enabled" >&2
  exit 1
}
grep -q '^CONFIG_USB_CONFIGFS_ECM=y$' .config || {
  echo "ERROR: USB ECM gadget support did not resolve to built-in" >&2
  grep -E 'USB_(GADGET|CONFIGFS|CONFIGFS_ECM|CHIPIDEA)' .config || true
  exit 1
}

make -j"$JOBS" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" zImage dtbs

ZIMAGE="arch/arm/boot/zImage"
DTB="arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dtb"
[[ -s "$ZIMAGE" ]] || { echo "missing zImage" >&2; exit 1; }
[[ -s "$DTB" ]] || { echo "missing flo DTB" >&2; exit 1; }

cat "$ZIMAGE" "$DTB" > "$WORK/zImage-dtb"
cp .config "$OUT/kernel.config"
cp "$DTB" "$OUT/flo-no-emmc.dtb"

popd >/dev/null

# -----------------------------
# 3) Legacy Android boot image, loaded only with `fastboot boot`
# -----------------------------
# Flo's stock bootloader historically eats the first 26 cmdline characters
# when handing off a mainline kernel, hence the padding.
CMDLINE='xxxxxxxxxxxxxxxxxxxxxxxxxxconsole=ttyMSM0,115200,n8 rdinit=/init loglevel=8 ignore_loglevel user_debug=31 msm_rtb.filter=0x3F ehci-hcd.park=3'

python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$WORK/zImage-dtb" \
  --ramdisk "$WORK/initramfs.cpio.gz" \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset 0x02000000 \
  --second_offset 0x00f00000 \
  --tags_offset 0x00000100 \
  --pagesize 2048 \
  --cmdline "$CMDLINE" \
  --output "$OUT/diskless-test.img"

cp "$WORK/initramfs.cpio.gz" "$OUT/initramfs.cpio.gz"
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"

# Sanity-check the legacy Android magic before presenting the image.
python3 - "$OUT/diskless-test.img" <<'PY'
import struct, sys
p = sys.argv[1]
with open(p, 'rb') as f:
    h = f.read(48)
if h[:8] != b'ANDROID!':
    raise SystemExit('ERROR: invalid Android boot image magic')
vals = struct.unpack('<10I', h[8:48])
ks, ka, rs, ra, ss, sa, ta, ps, hv, osv = vals
assert ka == 0x80208000, hex(ka)
assert ra == 0x82200000, hex(ra)
assert ta == 0x80200100, hex(ta)
assert ps == 2048, ps
assert hv == 0, hv
print(f'boot.img sanity: kernel={ks} ramdisk={rs} kernel_addr=0x{ka:08x} ramdisk_addr=0x{ra:08x}')
PY

cat <<EOF

Build complete:
  $OUT/diskless-test.img

TEST WITH:
  fastboot boot $OUT/diskless-test.img

DO NOT use 'fastboot flash'.
EOF
