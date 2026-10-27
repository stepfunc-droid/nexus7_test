#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
WORK="$ROOT/.work-pmos-runtime"
OUT="$ROOT/out"
DOWNLOAD_PROXY="${DOWNLOAD_PROXY:-http://192.168.1.116:7890}"
PMOS_MIRROR="${PMOS_MIRROR:-https://mirror.nju.edu.cn/postmarketos/main/postmarketos/armv7}"
PMOS_VERSION="${PMOS_VERSION:-}"

BASE_INITRD="$OUT/initramfs.cpio.gz"
RUNTIME_INITRD="$WORK/initramfs-runtime.cpio.gz"
EXTRACT="$WORK/pkg"
INITROOT="$WORK/initramfs-root"
DTB="$WORK/flo-no-emmc.dtb"
QCDT="$WORK/flo.dt.img"
IMAGE="$OUT/pmos-runtime.img"

proxy_wget() {
  http_proxy="$DOWNLOAD_PROXY" \
  https_proxy="$DOWNLOAD_PROXY" \
  HTTP_PROXY="$DOWNLOAD_PROXY" \
  HTTPS_PROXY="$DOWNLOAD_PROXY" \
  wget "$@"
}

for tool in wget bsdtar fdtput fdtget python3 stat file grep sort basename cpio gzip xz depmod find; do
  command -v "$tool" >/dev/null || {
    echo "missing tool: $tool" >&2
    echo "Install: sudo apt-get install -y libarchive-tools device-tree-compiler file cpio gzip xz-utils kmod" >&2
    exit 1
  }
done

[[ -s "$BASE_INITRD" ]] || {
  echo "missing $BASE_INITRD" >&2
  echo "Run the normal builder once so the static BusyBox initramfs exists." >&2
  exit 1
}
[[ -s "$ROOT/initramfs/init" ]] || { echo "missing initramfs/init" >&2; exit 1; }

mkdir -p "$CACHE" "$OUT"
rm -rf "$WORK"
mkdir -p "$EXTRACT" "$INITROOT"

# postmarketOS mirrors are rolling. Discover the currently available APQ8064
# kernel package unless the caller pins PMOS_VERSION or APK_URL.
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

printf '\nNexus 7 flo postmarketOS RAM-only runtime builder\n'
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

KERNEL="$(find "$EXTRACT/boot" -maxdepth 1 -type f -name 'vmlinuz*' | head -n1 || true)"
DTB_SRC="$EXTRACT/boot/dtbs/qcom-apq8064-asus-nexus7-flo.dtb"
[[ -n "$KERNEL" && -s "$KERNEL" ]] || { echo "postmarketOS vmlinuz not found" >&2; exit 1; }
[[ -s "$DTB_SRC" ]] || { echo "flo DTB not found in package" >&2; exit 1; }
[[ -d "$EXTRACT/lib/modules" ]] || { echo "kernel module tree not found in package" >&2; exit 1; }

CONFIG_FILE="$(find "$EXTRACT/boot" -maxdepth 1 -type f -name 'config*' | head -n1 || true)"
if [[ -n "$CONFIG_FILE" ]]; then
  echo "==> Packaged USB gadget config"
  grep -E '^(CONFIG_USB_(GADGET|LIBCOMPOSITE|U_ETHER|F_(ECM|NCM|RNDIS)|CONFIGFS|CONFIGFS_(ECM|NCM|RNDIS)|ETH|ETH_RNDIS|CHIPIDEA|CHIPIDEA_UDC|CHIPIDEA_MSM|ROLE_SWITCH))=' "$CONFIG_FILE" || true
fi

# Reuse the already-built static BusyBox initramfs, replace /init, and add the
# exact module tree that belongs to the packaged kernel. The APQ8064 package has
# the UDC built in, but libcomposite/configfs and Ethernet gadget functions are
# modules, so a module-less initramfs can never create ECM/NCM/RNDIS.
echo "==> Refreshing initramfs and bundling matching kernel modules"
(
  cd "$INITROOT"
  gzip -dc "$BASE_INITRD" | cpio -idmu --quiet
)
cp "$ROOT/initramfs/init" "$INITROOT/init"
chmod 0755 "$INITROOT/init"
mkdir -p "$INITROOT/lib"
cp -a "$EXTRACT/lib/modules" "$INITROOT/lib/"

# Make runtime module loading independent of BusyBox support for compressed .ko
# files, then regenerate modules.dep for the initramfs root.
if find "$INITROOT/lib/modules" -type f -name '*.ko.gz' -print -quit | grep -q .; then
  find "$INITROOT/lib/modules" -type f -name '*.ko.gz' -exec gzip -d {} +
fi
if find "$INITROOT/lib/modules" -type f -name '*.ko.xz' -print -quit | grep -q .; then
  find "$INITROOT/lib/modules" -type f -name '*.ko.xz' -exec xz -d {} +
fi
if find "$INITROOT/lib/modules" -type f -name '*.ko.zst' -print -quit | grep -q .; then
  command -v zstd >/dev/null || {
    echo "kernel modules are zstd-compressed; install zstd: sudo apt-get install -y zstd" >&2
    exit 1
  }
  find "$INITROOT/lib/modules" -type f -name '*.ko.zst' -exec zstd -q -d --rm {} +
fi

MODULE_DIR="$(find "$INITROOT/lib/modules" -mindepth 1 -maxdepth 1 -type d | head -n1 || true)"
[[ -n "$MODULE_DIR" ]] || { echo "no kernel release directory under lib/modules" >&2; exit 1; }
KREL="$(basename "$MODULE_DIR")"
depmod -b "$INITROOT" "$KREL"
printf '    module release: %s\n' "$KREL"
printf '    gadget modules:\n'
find "$MODULE_DIR" -type f \( -name 'libcomposite.ko' -o -name 'usb_f_ecm.ko' -o -name 'usb_f_ncm.ko' -o -name 'usb_f_rndis.ko' -o -name 'u_ether.ko' \) -printf '      %P\n' | sort || true

(
  cd "$INITROOT"
  find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -9 > "$RUNTIME_INITRD"
)
printf '    runtime initramfs: %s bytes\n' "$(stat -c %s "$RUNTIME_INITRD")"

cp "$DTB_SRC" "$DTB"

echo "==> Disabling onboard eMMC in packaged flo DTB"
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
printf '    kernel:   %s\n' "$(file -b "$KERNEL")"
printf '    kernel:   %s bytes\n' "$(stat -c %s "$KERNEL")"
printf '    DTB:      %s bytes\n' "$(stat -c %s "$DTB")"

echo "==> Building exact-match QCDT for this flo"
python3 "$ROOT/scripts/mkqcdt.py" \
  --dtb "$DTB" \
  --platform-id 172 \
  --variant-id 8 \
  --soc-rev 0x00020000 \
  --pagesize 2048 \
  --output "$QCDT"

# Keep the exact memory policy already proven by pmos-probe.img.
RAMDISK_SIZE=$(stat -c %s "$RUNTIME_INITRD")
BOOT_MEM=$((128 * 1024 * 1024))
RAMDISK_OFFSET=$(((BOOT_MEM - RAMDISK_SIZE) & ~4095))
TAGS_OFFSET=$((RAMDISK_OFFSET - 2 * 1024 * 1024))
RAMDISK_OFFSET_HEX=$(printf '0x%x' "$RAMDISK_OFFSET")
TAGS_OFFSET_HEX=$(printf '0x%x' "$TAGS_OFFSET")

CMDLINE='fw_devlink=permissive earlycon console=ttyMSM0,115200n8 rdinit=/init loglevel=8 ignore_loglevel panic=0'

echo "==> Packing RAM-only runtime image"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$KERNEL" \
  --ramdisk "$RUNTIME_INITRD" \
  --dt "$QCDT" \
  --board flo-pmos-runtime \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset "$RAMDISK_OFFSET_HEX" \
  --second_offset 0x00f00000 \
  --tags_offset "$TAGS_OFFSET_HEX" \
  --pagesize 2048 \
  --cmdline "$CMDLINE" \
  --output "$IMAGE"

cp "$RUNTIME_INITRD" "$OUT/pmos-runtime-initramfs.cpio.gz"
cp "$DTB" "$OUT/pmos-runtime-flo-no-emmc.dtb"

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

printf '\nRuntime image ready: %s\n' "$IMAGE"
printf 'Boot only with lk2nd + fastboot boot. DO NOT FLASH.\n'
printf 'Expected host side: a new USB network interface; Nexus address is 172.16.42.1, telnet port 2323.\n'
