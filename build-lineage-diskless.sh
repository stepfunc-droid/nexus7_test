#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/out"
WORK="$ROOT/.work-lineage-diskless"
KERNEL_DIR="${KERNEL_DIR:-/home/debian/diskless_test/android_kernel_google_msm}"
KERNEL_OUT="${KERNEL_OUT:-$KERNEL_DIR/out}"
ZIMAGE="$KERNEL_OUT/arch/arm/boot/zImage"
BOOTIMG="${1:-}"
OUTPUT="$OUT/lineage-diskless.img"

if [[ -z "$BOOTIMG" ]]; then
    echo "usage: $0 /path/to/official-lineage-boot.img" >&2
    exit 2
fi

BOOTIMG="$(realpath "$BOOTIMG")"
[[ -f "$BOOTIMG" ]] || { echo "ERROR: boot image not found: $BOOTIMG" >&2; exit 1; }
[[ -s "$ZIMAGE" ]] || { echo "ERROR: custom Lineage zImage not found: $ZIMAGE" >&2; exit 1; }

for tool in python3 cpio gzip xz realpath; do
    command -v "$tool" >/dev/null || { echo "ERROR: missing required tool: $tool" >&2; exit 1; }
done

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

BB="$(find_busybox || true)"
[[ -n "$BB" ]] || {
    echo "ERROR: static ARM BusyBox not found; set BUSYBOX=/path/to/busybox" >&2
    exit 1
}

rm -rf "$WORK"
mkdir -p "$WORK/unpacked" "$WORK/root" "$OUT"

python3 "$ROOT/scripts/unpack_bootimg_v0.py" "$BOOTIMG" "$WORK/unpacked"
RAMDISK="$WORK/unpacked/ramdisk"
[[ -f "$RAMDISK" ]] || { echo "ERROR: unpacked ramdisk missing" >&2; exit 1; }

echo "==> Unpacking official Lineage ramdisk"
magic="$(od -An -tx1 -N6 "$RAMDISK" | tr -d ' \n')"
case "$magic" in
    fd377a585a00*) xz -dc "$RAMDISK" > "$WORK/ramdisk.cpio" ;;
    1f8b*)         gzip -dc "$RAMDISK" > "$WORK/ramdisk.cpio" ;;
    *)             cp "$RAMDISK" "$WORK/ramdisk.cpio" ;;
esac
(
    cd "$WORK/root"
    cpio -idm --no-absolute-filenames < "$WORK/ramdisk.cpio" >/dev/null 2>&1
)

[[ -x "$WORK/root/init" ]] || { echo "ERROR: official /init missing from ramdisk" >&2; exit 1; }
[[ -f "$WORK/root/fstab.flox" ]] || { echo "ERROR: fstab.flox missing from ramdisk" >&2; exit 1; }
[[ -f "$WORK/root/init.flox.rc" ]] || { echo "ERROR: init.flox.rc missing from ramdisk" >&2; exit 1; }

mv "$WORK/root/init" "$WORK/root/init.android"
cp "$ROOT/initramfs/lineage-diskless-init" "$WORK/root/init"
chmod 0755 "$WORK/root/init" "$WORK/root/init.android"
mkdir -p "$WORK/root/bin"
cp "$BB" "$WORK/root/bin/busybox"
chmod 0755 "$WORK/root/bin/busybox"
ln -sf busybox "$WORK/root/bin/sh"

cat > "$WORK/root/fstab.flox" <<'EOF'
# Diskless flox fstab. NBD sockets are attached by /init before Android
# first-stage init starts. Android first-stage coldboot recreates them as
# /dev/block/nbdN after it mounts its own /dev tmpfs.
/dev/block/nbd0   /system   ext4   ro,barrier=1                                                          wait,first_stage_mount
/dev/block/nbd1   /vendor   ext4   ro,barrier=1                                                          wait,first_stage_mount
/dev/block/nbd2   /cache    ext4   noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic wait
/dev/block/nbd3   /data     ext4   noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic latemount,wait
/dev/block/nbd4   /persist  ext4   noatime,nosuid,nodev,barrier=1,data=ordered,nodelalloc                  wait
/devices/platform/msm_hsusb_host/usb* auto auto defaults voldmanaged=usb:auto
/dev/block/zram0  none      swap   defaults zramsize=1610612736,notrim
EOF

# Keep the RAM-only safety contract explicit: no old eMMC path may survive.
if grep -q 'msm_sdcc\.1' "$WORK/root/fstab.flox"; then
    echo "ERROR: eMMC path unexpectedly present in diskless fstab" >&2
    exit 1
fi

# flox's legacy Qualcomm bring-up synchronously waits for sys.qcom.devup=1 in
# early-boot. On the diskless kernel the ADSP boot path may never complete,
# which blocks Android init forever even though zygote/netd are already alive.
# During diskless bring-up, skip both the ADSP start and the synchronous wait.
# Do not fake sys.qcom.devup=1: consumers should not be told the DSP is ready.
echo "==> Patching flox Qualcomm ADSP wait for diskless boot"
python3 - "$WORK/root/init.flox.rc" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

replacements = [
    (
        "    start devstart_sh\n",
        "    # nexus7_test diskless: skip Qualcomm ADSP devstart during bring-up\n"
        "    # start devstart_sh\n",
    ),
    (
        "    exec - root root system -- /vendor/bin/init.qcom.devwait.sh\n",
        "    # nexus7_test diskless: do not block init waiting for sys.qcom.devup\n"
        "    # exec - root root system -- /vendor/bin/init.qcom.devwait.sh\n",
    ),
]

for old, new in replacements:
    count = s.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: expected exactly one init.flox.rc match for {old.strip()!r}, found {count}"
        )
    s = s.replace(old, new, 1)

p.write_text(s)
PY

grep -Fq 'nexus7_test diskless: skip Qualcomm ADSP devstart' "$WORK/root/init.flox.rc" || {
    echo "ERROR: devstart_sh bypass marker missing after patch" >&2
    exit 1
}
grep -Fq 'nexus7_test diskless: do not block init waiting for sys.qcom.devup' "$WORK/root/init.flox.rc" || {
    echo "ERROR: devwait bypass marker missing after patch" >&2
    exit 1
}

echo "==> Packing diskless ramdisk"
(
    cd "$WORK/root"
    find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$WORK/ramdisk.cpio.gz"
)

# Use the already-validated flo boot geometry. The legacy boot header board
# field is only 16 bytes, so keep this name short.
echo "==> Building diskless Lineage boot image"
python3 "$ROOT/scripts/mkbootimg_v0.py" \
  --kernel "$ZIMAGE" \
  --ramdisk "$WORK/ramdisk.cpio.gz" \
  --board flo-diskless \
  --base 0x80200000 \
  --kernel_offset 0x00008000 \
  --ramdisk_offset 0x02000000 \
  --second_offset 0x00f00000 \
  --tags_offset 0x00000100 \
  --pagesize 2048 \
  --cmdline "console=ttyHSL0,115200,n8 androidboot.hardware=flox androidboot.selinux=permissive panic=0 user_debug=31 msm_rtb.filter=0x3F ehci-hcd.park=3 vmalloc=340M rdinit=/init loglevel=7" \
  --output "$OUTPUT"

sha256sum "$OUTPUT" > "$OUTPUT.sha256"

echo
echo "Build complete: $OUTPUT"
echo "RAM ONLY. DO NOT FLASH."
echo "NBD ports expected on Mac 172.16.42.2:"
echo "  10810 system   -> nbd0 (RO)"
echo "  10811 vendor   -> nbd1 (RO)"
echo "  10812 cache    -> nbd2 (RW)"
echo "  10813 userdata -> nbd3 (RW)"
echo "  10814 persist  -> nbd4 (RW)"
