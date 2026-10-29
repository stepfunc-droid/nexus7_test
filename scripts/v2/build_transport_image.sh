#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/out"
WORK="$ROOT/.work-v2-transport"
KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
INIT_SRC="$ROOT/initramfs/diskless-v2-transport-init"
LAYOUT_JSON="$ROOT/diskless-v2/layout.json"
INITRAMFS="$WORK/diskless-v2-transport.cpio.gz"
BOOTIMG="$OUT/diskless-v2-transport.img"
BOOT_MANIFEST="$OUT/diskless-v2-transport-manifest.txt"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

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

for tool in python3 cpio gzip sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required tool: $tool"
done

[[ -s "$ZIMAGE" ]] || fail "verified v2 zImage not found: $ZIMAGE"
[[ -f "$INIT_SRC" ]] || fail "missing init source: $INIT_SRC"
[[ -f "$LAYOUT_JSON" ]] || fail "missing layout contract: $LAYOUT_JSON"

# Re-run the Phase-1 verifier immediately before packaging. A transport image
# must never silently package a stale or non-v2 kernel.
echo "==> Re-verifying deterministic v2 kernel"
VERIFY_OUTPUT="$(KERNEL_DIR="$KERNEL_DIR" KERNEL_OUT="$KERNEL_OUT" bash "$ROOT/scripts/v2/verify_kernel.sh")"
printf '%s\n' "$VERIFY_OUTPUT"
grep -q '^DISKLESS_V2_KERNEL_VERIFIED=1$' <<<"$VERIFY_OUTPUT" || fail "kernel verifier did not pass"

BB="$(find_busybox || true)"
if [[ -z "$BB" ]]; then
    fail "static ARM BusyBox not found; set BUSYBOX=/absolute/path/to/static/arm/busybox"
fi

mkdir -p "$OUT"
rm -rf "$WORK"
mkdir -p "$WORK/root/bin" "$WORK/root/sbin" "$WORK/root/proc" \
         "$WORK/root/sys" "$WORK/root/dev/pts" "$WORK/root/tmp" \
         "$WORK/root/www" "$WORK/root/etc" "$WORK/root/mnt"

cp "$BB" "$WORK/root/bin/busybox"
chmod 755 "$WORK/root/bin/busybox"
ln -s busybox "$WORK/root/bin/sh"
cp "$INIT_SRC" "$WORK/root/init"
chmod 755 "$WORK/root/init"

# Generate the shell contract used by the initramfs directly from layout.json.
# Do not duplicate partition sizes in the shell script.
python3 - "$LAYOUT_JSON" "$WORK/root/etc/diskless-v2-layout" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
data = json.loads(src.read_text())
if data.get("partition_table") != "dos":
    raise SystemExit("layout must use DOS/MBR")
sector_size = int(data.get("sector_size", 0))
if sector_size != 512:
    raise SystemExit(f"expected 512-byte sectors, got {sector_size}")
if int(data.get("nbd_max_part", 0)) != 8:
    raise SystemExit("v2 transport contract currently requires nbd_max_part=8")

wanted = {1, 2, 3, 5, 6, 7}
parts = {int(p["number"]): p for p in data["partitions"] if int(p["number"]) in wanted}
if set(parts) != wanted:
    raise SystemExit(f"layout missing required partitions: {sorted(wanted - set(parts))}")

lines = ["NBD_MAX_PART=8"]
for n in sorted(parts):
    p = parts[n]
    size = int(p["size_bytes"])
    if size % sector_size:
        raise SystemExit(f"p{n} size is not sector aligned: {size}")
    lines.append(f"P{n}_NAME={p['name']}")
    lines.append(f"P{n}_SECTORS={size // sector_size}")
    lines.append(f"P{n}_FILESYSTEM={p.get('filesystem', 'raw')}")
dst.write_text("\n".join(lines) + "\n")
PY

echo "==> Transport layout contract"
cat "$WORK/root/etc/diskless-v2-layout"

echo "==> Building transport-only initramfs"
(
    cd "$WORK/root"
    find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$INITRAMFS"
)

CMDLINE="console=ttyHSL0,115200,n8 androidboot.hardware=flox androidboot.diskless=1 nbd.max_part=8 panic=5 user_debug=31 msm_rtb.filter=0x3F ehci-hcd.park=3 vmalloc=340M rdinit=/init loglevel=8 ignore_loglevel"

echo "==> Building transport-only Android boot image"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$ZIMAGE" \
  --ramdisk "$INITRAMFS" \
  --board flo-diskless-v2-transport \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset 0x02000000 \
  --second_offset 0x00f00000 \
  --tags_offset 0x00000100 \
  --pagesize 2048 \
  --cmdline "$CMDLINE" \
  --output "$BOOTIMG"

[[ -s "$BOOTIMG" ]] || fail "boot image was not produced: $BOOTIMG"

KERNEL_SHA="$(sha256sum "$ZIMAGE" | awk '{print $1}')"
INITRAMFS_SHA="$(sha256sum "$INITRAMFS" | awk '{print $1}')"
BOOT_SHA="$(sha256sum "$BOOTIMG" | awk '{print $1}')"
LAYOUT_SHA="$(sha256sum "$LAYOUT_JSON" | awk '{print $1}')"

cat > "$BOOT_MANIFEST" <<EOF
DISKLESS_V2_TRANSPORT_IMAGE_BUILT=1
kernel=$ZIMAGE
kernel_sha256=$KERNEL_SHA
initramfs_sha256=$INITRAMFS_SHA
layout_sha256=$LAYOUT_SHA
boot_image=$BOOTIMG
boot_sha256=$BOOT_SHA
cmdline=$CMDLINE
EOF

sha256sum "$BOOTIMG" > "$BOOTIMG.sha256"

echo
echo "DISKLESS_V2_TRANSPORT_IMAGE_BUILT=1"
echo "boot_image=$BOOTIMG"
echo "manifest=$BOOT_MANIFEST"
echo "sha256=$BOOT_SHA"
echo
echo "This image is transport-only. It does NOT start Android."
