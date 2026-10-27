#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
WORK="$ROOT/.work-pmos-probe"
OUT="$ROOT/out"
DOWNLOAD_PROXY="${DOWNLOAD_PROXY:-http://192.168.1.116:7890}"
PMOS_MIRROR="${PMOS_MIRROR:-https://mirror.nju.edu.cn/postmarketos/main/postmarketos/armv7}"
PMOS_VERSION="${PMOS_VERSION:-}"

EXTRACT="$WORK/pkg"
INITRD="$OUT/initramfs.cpio.gz"
DTB="$WORK/flo-no-emmc.dtb"
QCDT="$WORK/flo.dt.img"
IMAGE="$OUT/pmos-probe.img"

proxy_wget() {
  http_proxy="$DOWNLOAD_PROXY" \
  https_proxy="$DOWNLOAD_PROXY" \
  HTTP_PROXY="$DOWNLOAD_PROXY" \
  HTTPS_PROXY="$DOWNLOAD_PROXY" \
  wget "$@"
}

for tool in wget bsdtar fdtput fdtget python3 stat file grep sort basename; do
  command -v "$tool" >/dev/null || {
    echo "missing tool: $tool" >&2
    echo "Install: sudo apt-get install -y libarchive-tools device-tree-compiler file" >&2
    exit 1
  }
done

[[ -s "$INITRD" ]] || {
  echo "missing $INITRD" >&2
  echo "Run the normal builder once so the static BusyBox initramfs exists." >&2
  exit 1
}

mkdir -p "$CACHE" "$OUT"
rm -rf "$WORK"
mkdir -p "$EXTRACT"

# postmarketOS mirrors are rolling: old package revisions disappear.  Do not
# hard-code a revision unless PMOS_VERSION or APK_URL is explicitly supplied.
if [[ -n "${APK_URL:-}" ]]; then
  APK_NAME="$(basename "$APK_URL")"
elif [[ -n "$PMOS_VERSION" ]]; then
  APK_NAME="linux-postmarketos-qcom-apq8064-${PMOS_VERSION}.apk"
  APK_URL="$PMOS_MIRROR/$APK_NAME"
else
  echo "==> Discovering current APQ8064 kernel package"
  INDEX_HTML="$WORK/index.html"
  proxy_wget -q "$PMOS_MIRROR/" -O "$INDEX_HTML"
  APK_NAME="$(grep -oE 'linux-postmarketos-qcom-apq8064-[^"<>[:space:]]+\.apk' "$INDEX_HTML" | sort -Vu | tail -n1 || true)"
  [[ -n "$APK_NAME" ]] || {
    echo "could not discover linux-postmarketos-qcom-apq8064 package at $PMOS_MIRROR" >&2
    exit 1
  }
  APK_URL="$PMOS_MIRROR/$APK_NAME"
fi

APK="$CACHE/$APK_NAME"
KERNEL="$EXTRACT/boot/vmlinuz"
DTB_SRC="$EXTRACT/boot/dtbs/qcom-apq8064-asus-nexus7-flo.dtb"

printf '\nNexus 7 flo postmarketOS APQ8064 probe builder\n'
printf '  package: %s\n' "$APK_NAME"
printf '  proxy:   %s\n' "$DOWNLOAD_PROXY"
printf '  output:  %s\n\n' "$IMAGE"

if [[ ! -s "$APK" ]]; then
  echo "==> Downloading $APK_NAME"
  proxy_wget -c --progress=bar:force:noscroll "$APK_URL" -O "$APK"
else
  echo "==> Using cached $APK"
fi

echo "==> Extracting postmarketOS kernel package"
bsdtar -xf "$APK" -C "$EXTRACT"

if [[ ! -s "$KERNEL" ]]; then
  KERNEL="$(find "$EXTRACT/boot" -maxdepth 1 -type f -name 'vmlinuz*' | head -n1 || true)"
fi
[[ -n "$KERNEL" && -s "$KERNEL" ]] || { echo "postmarketOS vmlinuz not found" >&2; exit 1; }
[[ -s "$DTB_SRC" ]] || { echo "flo DTB not found in package" >&2; exit 1; }

cp "$DTB_SRC" "$DTB"

echo "==> Disabling onboard eMMC in the packaged flo DTB"
MMC_NODE=""
for node in /soc/mmc@12400000 /amba/mmc@12400000 /soc/sdcc@12400000 /amba/sdcc@12400000; do
  if fdtget "$DTB" "$node" status >/dev/null 2>&1; then
    MMC_NODE="$node"
    break
  fi
done
[[ -n "$MMC_NODE" ]] || { echo "could not locate sdcc1/eMMC DT node" >&2; exit 1; }
fdtput -t s "$DTB" "$MMC_NODE" status disabled
[[ "$(fdtget "$DTB" "$MMC_NODE" status)" == "disabled" ]] || {
  echo "failed to disable eMMC DT node" >&2
  exit 1
}
printf '    eMMC node: %s -> disabled\n' "$MMC_NODE"

printf '    kernel: %s\n' "$(file -b "$KERNEL")"
printf '    kernel size: %s bytes\n' "$(stat -c %s "$KERNEL")"
printf '    DTB size:    %s bytes\n' "$(stat -c %s "$DTB")"

echo "==> Building exact-match QCDT for this flo"
python3 "$ROOT/scripts/mkqcdt.py" \
  --dtb "$DTB" \
  --platform-id 172 \
  --variant-id 8 \
  --soc-rev 0x00020000 \
  --pagesize 2048 \
  --output "$QCDT"

# Match lk2nd's extlinux memory policy on msm8960: 128 MiB boot window,
# ramdisk at the top, DTB 2 MiB below it, kernel at BASE + 0x8000.
RAMDISK_SIZE=$(stat -c %s "$INITRD")
BOOT_MEM=$((128 * 1024 * 1024))
RAMDISK_OFFSET=$(((BOOT_MEM - RAMDISK_SIZE) & ~4095))
TAGS_OFFSET=$((RAMDISK_OFFSET - 2 * 1024 * 1024))
RAMDISK_OFFSET_HEX=$(printf '0x%x' "$RAMDISK_OFFSET")
TAGS_OFFSET_HEX=$(printf '0x%x' "$TAGS_OFFSET")

CMDLINE='fw_devlink=permissive earlycon console=ttyMSM0,115200n8 rdinit=/bin/busybox loglevel=8 ignore_loglevel panic=5'

echo "==> Packing RAM-only probe image"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$KERNEL" \
  --ramdisk "$INITRD" \
  --dt "$QCDT" \
  --board flo-pmos-probe \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset "$RAMDISK_OFFSET_HEX" \
  --second_offset 0x00f00000 \
  --tags_offset "$TAGS_OFFSET_HEX" \
  --pagesize 2048 \
  --cmdline "$CMDLINE" \
  --output "$IMAGE"

python3 - "$IMAGE" <<'PY'
import struct, sys
p = sys.argv[1]
with open(p, 'rb') as f:
    h = f.read(48)
assert h[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, ps, dt_size, unused = struct.unpack('<10I', h[8:48])
print(f'    kernel_addr = 0x{ka:08x}')
print(f'    ramdisk_addr= 0x{ra:08x}')
print(f'    tags_addr   = 0x{ta:08x}')
print(f'    dt_size     = {dt_size}')
assert ka == 0x80208000
assert dt_size > 0
PY

printf '\nProbe ready: %s\n' "$IMAGE"
printf 'Expected result if kernel reaches initramfs: BusyBox exits as PID 1, kernel panics, then reboots after panic=5.\n'
printf 'Do NOT flash it; use fastboot boot only.\n'
