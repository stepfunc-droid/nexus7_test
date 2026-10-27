#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$ROOT/.work"
OUT="$ROOT/out"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
DOWNLOAD_PROXY="${DOWNLOAD_PROXY:-http://192.168.1.116:7890}"
KERNEL_VERSION="${KERNEL_VERSION:-7.2.13}"
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
CROSS_COMPILE="${CROSS_COMPILE:-arm-linux-gnueabihf-}"
JOBS="${JOBS:-$(nproc)}"
START_TIME=$(date +%s)
CURRENT_STEP="initialization"

step() {
  CURRENT_STEP="$1"
  printf '\n\033[1;36m==> %s\033[0m\n' "$CURRENT_STEP"
}

info() {
  printf '    %s\n' "$1"
}

on_error() {
  rc=$?
  printf '\n\033[1;31mERROR\033[0m while: %s (exit %d)\n' "$CURRENT_STEP" "$rc" >&2
  exit "$rc"
}
trap on_error ERR

proxy_wget() {
  http_proxy="$DOWNLOAD_PROXY" \
  https_proxy="$DOWNLOAD_PROXY" \
  HTTP_PROXY="$DOWNLOAD_PROXY" \
  HTTPS_PROXY="$DOWNLOAD_PROXY" \
  wget "$@"
}

valid_bz2() {
  [[ -s "$1" ]] && bzip2 -t "$1" >/dev/null 2>&1
}

valid_xz() {
  [[ -s "$1" ]] && xz -t "$1" >/dev/null 2>&1
}

printf '\nNexus 7 flo RAM-only image builder (lk2nd handoff)\n'
printf '  Kernel:    Linux %s\n' "$KERNEL_VERSION"
printf '  BusyBox:   %s\n' "$BUSYBOX_VERSION"
printf '  Jobs:      %s\n' "$JOBS"
printf '  Toolchain: %s\n' "$CROSS_COMPILE"
printf '  Output:    %s\n' "$OUT"
printf '  Cache:     %s\n' "$CACHE"
printf '  Proxy:     %s\n' "$DOWNLOAD_PROXY"

step "Checking build tools"
for tool in make "${CROSS_COMPILE}gcc" cpio gzip python3 wget tar sed sha256sum bzip2 xz; do
  if command -v "$tool" >/dev/null; then
    printf '    [ok] %s\n' "$tool"
  else
    printf '    [missing] %s\n' "$tool" >&2
    exit 1
  fi
done

step "Preserving source downloads and preparing clean work directories"
mkdir -p "$CACHE"
# Migrate tarballs from older builds before .work is cleaned. Integrity is
# checked later; incomplete files are moved to .part and resumed instead of
# being blindly trusted as valid cache entries.
for old_tar in "$WORK"/linux-*.tar.xz "$WORK"/busybox-*.tar.bz2; do
  if [[ -s "$old_tar" ]]; then
    base="$(basename "$old_tar")"
    if [[ ! -e "$CACHE/$base" && ! -e "$CACHE/$base.part" ]]; then
      cp "$old_tar" "$CACHE/$base"
      info "cached existing download: $base"
    fi
  fi
done
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT" "$CACHE"
info "work:  $WORK"
info "out:   $OUT"
info "cache: $CACHE (not deleted between builds)"

# -----------------------------------------------------------------------------
# 1) Tiny static ARM initramfs
# -----------------------------------------------------------------------------
INITROOT="$WORK/initramfs"
mkdir -p "$INITROOT"/{bin,sbin,etc,proc,sys,dev,tmp,run,root,usr/bin,usr/sbin}

if [[ -n "${BUSYBOX_ARM:-}" ]]; then
  step "Using supplied static ARM BusyBox"
  BUSYBOX_SRC="$BUSYBOX_ARM"
  info "$BUSYBOX_SRC"
else
  BB_TAR="$CACHE/busybox-${BUSYBOX_VERSION}.tar.bz2"
  BB_PART="$BB_TAR.part"
  BB_SRC="$WORK/busybox-${BUSYBOX_VERSION}"
  BB_URL="https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2"

  if [[ -s "$BB_TAR" ]] && ! valid_bz2 "$BB_TAR"; then
    step "Cached BusyBox archive is incomplete/corrupt; resuming it"
    rm -f "$BB_PART"
    mv "$BB_TAR" "$BB_PART"
  fi

  if valid_bz2 "$BB_TAR"; then
    step "Using validated cached BusyBox ${BUSYBOX_VERSION} tarball"
    info "$BB_TAR"
  else
    step "Downloading/resuming BusyBox ${BUSYBOX_VERSION} through proxy"
    info "proxy: $DOWNLOAD_PROXY"
    proxy_wget -c --progress=bar:force:noscroll "$BB_URL" -O "$BB_PART"
    if ! valid_bz2 "$BB_PART"; then
      echo "ERROR: downloaded BusyBox archive still fails bzip2 integrity check" >&2
      exit 1
    fi
    mv "$BB_PART" "$BB_TAR"
    info "validated and cached: $BB_TAR"
  fi

  step "Extracting BusyBox"
  tar -xjf "$BB_TAR" -C "$WORK"

  step "Configuring BusyBox for static ARM build"
  pushd "$BB_SRC" >/dev/null
  make distclean >/dev/null 2>&1 || true
  make defconfig
  sed -i 's/^# CONFIG_STATIC is not set$/CONFIG_STATIC=y/' .config
  # BusyBox 1.36 tc does not build against newer Linux UAPI headers; not needed.
  sed -i 's/^CONFIG_TC=y$/# CONFIG_TC is not set/' .config

  step "Building BusyBox (${JOBS} jobs)"
  make -j"$JOBS" CROSS_COMPILE="$CROSS_COMPILE"
  BUSYBOX_SRC="$BB_SRC/busybox"
  popd >/dev/null
fi

[[ -x "$BUSYBOX_SRC" ]] || { echo "static ARM BusyBox was not produced" >&2; exit 1; }

step "Assembling initramfs"
cp "$BUSYBOX_SRC" "$INITROOT/bin/busybox"
chmod 0755 "$INITROOT/bin/busybox"
cp "$ROOT/initramfs/init" "$INITROOT/init"
chmod 0755 "$INITROOT/init"

for applet in sh mount mkdir cat echo sleep ls head ifconfig telnetd grep uname ln dmesg; do
  ln -s busybox "$INITROOT/bin/$applet"
done

(
  cd "$INITROOT"
  find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -9 > "$WORK/initramfs.cpio.gz"
)
info "initramfs: $(du -h "$WORK/initramfs.cpio.gz" | awk '{print $1}')"

# -----------------------------------------------------------------------------
# 2) Linux for flo
# -----------------------------------------------------------------------------
KERNEL_TAR="$CACHE/linux-${KERNEL_VERSION}.tar.xz"
KERNEL_PART="$KERNEL_TAR.part"
KERNEL="$WORK/linux-${KERNEL_VERSION}"
KERNEL_MAJOR="${KERNEL_VERSION%%.*}"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR}.x/linux-${KERNEL_VERSION}.tar.xz"

if [[ -s "$KERNEL_TAR" ]] && ! valid_xz "$KERNEL_TAR"; then
  step "Cached Linux archive is incomplete/corrupt; resuming it"
  rm -f "$KERNEL_PART"
  mv "$KERNEL_TAR" "$KERNEL_PART"
fi

if valid_xz "$KERNEL_TAR"; then
  step "Using validated cached Linux ${KERNEL_VERSION} tarball"
  info "$KERNEL_TAR"
else
  step "Downloading/resuming Linux ${KERNEL_VERSION} through proxy"
  info "$KERNEL_URL"
  info "proxy: $DOWNLOAD_PROXY"
  proxy_wget -c --progress=bar:force:noscroll "$KERNEL_URL" -O "$KERNEL_PART"
  if ! valid_xz "$KERNEL_PART"; then
    echo "ERROR: downloaded Linux archive still fails xz integrity check" >&2
    exit 1
  fi
  mv "$KERNEL_PART" "$KERNEL_TAR"
  info "validated and cached: $KERNEL_TAR"
fi

step "Extracting Linux ${KERNEL_VERSION}"
tar -xJf "$KERNEL_TAR" -C "$WORK"

step "Patching flo device tree to disable eMMC"
python3 "$ROOT/scripts/patch-flo-dts.py" \
  "$KERNEL/arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts"

pushd "$KERNEL" >/dev/null

step "Configuring Linux kernel"
make ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" multi_v7_defconfig

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

scripts/config --enable PSTORE
scripts/config --enable PSTORE_RAM
scripts/config --enable PSTORE_CONSOLE

# Absolutely no Linux-side eMMC access in this experiment.
scripts/config --disable MMC

# USB gadget Ethernet for the first userspace proof-of-life.
scripts/config --enable USB_GADGET
scripts/config --enable USB_CONFIGFS
scripts/config --enable USB_CONFIGFS_ECM
scripts/config --enable USB_CHIPIDEA
scripts/config --enable USB_CHIPIDEA_UDC
scripts/config --enable USB_CHIPIDEA_MSM
scripts/config --enable PHY_QCOM_USB_HS

make ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" olddefconfig

step "Verifying critical kernel options"
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
printf '    [ok] CONFIG_MMC=n\n'
printf '    [ok] CONFIG_ARM_APPENDED_DTB=y\n'
printf '    [ok] CONFIG_USB_CONFIGFS_ECM=y\n'

step "Building Linux zImage + DTBs (${JOBS} jobs)"
make -j"$JOBS" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" zImage dtbs

ZIMAGE="arch/arm/boot/zImage"
DTB="arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dtb"
[[ -s "$ZIMAGE" ]] || { echo "missing zImage" >&2; exit 1; }
[[ -s "$DTB" ]] || { echo "missing flo DTB" >&2; exit 1; }

step "Appending flo DTB for lk2nd to extract and pass in r2"
cat "$ZIMAGE" "$DTB" > "$WORK/zImage-dtb"
cp .config "$OUT/kernel.config"
cp "$DTB" "$OUT/flo-no-emmc.dtb"
info "zImage: $(du -h "$ZIMAGE" | awk '{print $1}')"
info "DTB:    $(du -h "$DTB" | awk '{print $1}')"

popd >/dev/null

# -----------------------------------------------------------------------------
# 3) Legacy Android boot image for *lk2nd* fastboot
# -----------------------------------------------------------------------------
CMDLINE='console=ttyMSM0,115200n8 rdinit=/init loglevel=8 ignore_loglevel user_debug=31 msm_rtb.filter=0x3F panic=5'

step "Packing legacy Android boot image for lk2nd"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$WORK/zImage-dtb" \
  --ramdisk "$WORK/initramfs.cpio.gz" \
  --board flo-diskless \
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

step "Sanity-checking boot.img"
python3 - "$OUT/diskless-test.img" <<'PY'
import struct, sys
p = sys.argv[1]
with open(p, 'rb') as f:
    h = f.read(48)
if h[:8] != b'ANDROID!':
    raise SystemExit('ERROR: invalid Android boot image magic')
vals = struct.unpack('<10I', h[8:48])
ks, ka, rs, ra, ss, sa, ta, ps, dt_size, unused = vals
assert ka == 0x80208000, hex(ka)
assert ra == 0x82200000, hex(ra)
assert ta == 0x80200100, hex(ta)
assert ps == 2048, ps
assert dt_size == 0, dt_size
print(f'    kernel={ks} bytes')
print(f'    ramdisk={rs} bytes')
print(f'    kernel_addr=0x{ka:08x}')
print(f'    ramdisk_addr=0x{ra:08x}')
print(f'    tags_addr=0x{ta:08x}')
print(f'    page_size={ps}')
PY

ELAPSED=$(( $(date +%s) - START_TIME ))
MIN=$(( ELAPSED / 60 ))
SEC=$(( ELAPSED % 60 ))

printf '\n\033[1;32mBuild complete\033[0m in %dm %02ds\n' "$MIN" "$SEC"
printf '  image: %s\n' "$OUT/diskless-test.img"
printf '  size:  %s\n' "$(du -h "$OUT/diskless-test.img" | awk '{print $1}')"
printf '\nRAM-ONLY TEST CHAIN (DO NOT FLASH):\n'
printf '  1) stock: fastboot boot lk2nd-flo-fastboot.img\n'
printf '  2) lk2nd: fastboot boot diskless-test.img\n'
printf '\nDO NOT use fastboot flash.\n'
