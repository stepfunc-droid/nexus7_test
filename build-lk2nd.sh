#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$ROOT/.work-lk2nd"
OUT="$ROOT/out"
LK2ND_VERSION="${LK2ND_VERSION:-23.1}"
JOBS="${JOBS:-$(nproc)}"

echo "==> Checking lk2nd build tools"
for tool in git make arm-none-eabi-gcc dtc python3; do
  command -v "$tool" >/dev/null || {
    echo "missing required tool: $tool" >&2
    echo "Debian packages: gcc-arm-none-eabi device-tree-compiler libfdt-dev git make python3" >&2
    exit 1
  }
done

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"

echo "==> Cloning lk2nd ${LK2ND_VERSION}"
git clone --depth 1 --branch "$LK2ND_VERSION" \
  https://github.com/msm8916-mainline/lk2nd.git "$WORK/lk2nd"

pushd "$WORK/lk2nd" >/dev/null

echo "==> Patching downstream ATAGS machine-id handoff for flo"
python3 - <<'PY'
from pathlib import Path

p = Path("app/aboot/aboot.c")
s = p.read_text()

old = """void boot_linux(void *kernel, unsigned *tags,
		const char *cmdline, unsigned machtype,
		void *ramdisk, unsigned ramdisk_size,
		enum boot_type boot_type)
{
	unsigned char *final_cmdline;
"""

new = """void boot_linux(void *kernel, unsigned *tags,
		const char *cmdline, unsigned machtype,
		void *ramdisk, unsigned ramdisk_size,
		enum boot_type boot_type)
{
	unsigned char *final_cmdline;

#if WITH_LK2ND_DEVICE_2ND
	/*
	 * Preserve the Linux machine type supplied by the stock bootloader
	 * when lk2nd is handing off to a downstream ATAGS kernel.
	 *
	 * Nexus 7 flo stock bootloader passes r1 = 0x1e79 (7801), while
	 * msm8960 board_machtype() returns board_target_id() instead.
	 */
	if (boot_type & BOOT_ATAGS_COPY) {
		extern uintptr_t lk_boot_args[3];

		dprintf(INFO, "Using stock bootloader machtype: %#lx\\n",
			lk_boot_args[1]);
		machtype = (unsigned)lk_boot_args[1];
	}
#endif
"""

if old not in s:
    raise SystemExit("ERROR: expected lk2nd 23.1 boot_linux() block not found")

p.write_text(s.replace(old, new, 1))
PY

echo "==> Building lk2nd-msm8960 for Nexus 7 flo"
echo "    LK2ND_FORCE_FASTBOOT=1: do not continue into normal storage boot flow"
echo "    DEBUG_FBCON=1: show lk2nd debug output on the tablet display"
make -j"$JOBS" \
  TOOLCHAIN_PREFIX=arm-none-eabi- \
  LK2ND_FORCE_FASTBOOT=1 \
  DEBUG_FBCON=1 \
  lk2nd-msm8960

IMG="build-lk2nd-msm8960/lk2nd.img"
[[ -s "$IMG" ]] || { echo "ERROR: lk2nd image not produced" >&2; exit 1; }
cp "$IMG" "$OUT/lk2nd-flo-fastboot.img"
popd >/dev/null

sha256sum "$OUT/lk2nd-flo-fastboot.img" > "$OUT/lk2nd-flo-fastboot.img.sha256"

echo
echo "Build complete:"
echo "  $OUT/lk2nd-flo-fastboot.img"
echo
echo "RAM-ONLY TEST CHAIN (DO NOT FLASH):"
echo "  1) stock bootloader: fastboot boot lk2nd-flo-fastboot.img"
echo "  2) wait for lk2nd fastboot to enumerate"
echo "  3) lk2nd fastboot:  fastboot boot lineage-usb-probe-mach7801.img"
