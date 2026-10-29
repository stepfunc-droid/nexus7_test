# Diskless v2 implementation progress

This file records implementation state and issues encountered while executing `DISKLESS_V2_EXECUTION.md`.

## Phase 1 — deterministic diskless kernel

Status: **PASSED**.

Acceptance evidence from the Debian build host:

```text
manifest=/home/debian/nexus7_test/out/diskless-v2-kernel-manifest.txt

Diskless v2 kernel build passed verification.
zImage:   /home/debian/diskless_test/android_kernel_google_msm/out/arch/arm/boot/zImage
manifest: /home/debian/nexus7_test/out/diskless-v2-kernel-manifest.txt
```

The Phase 1 gate therefore completed with `DISKLESS_V2_KERNEL_VERIFIED=1`.

Implemented invariants:

- kernel source baseline pinned to LineageOS flo commit `0da5107137f93b8d8f697e949ab0784f5ace450c`;
- pristine `lineageos_flo_defconfig` is read directly from that pinned commit;
- `ARCH=arm` is explicit for Kconfig and build operations;
- `CONFIG_BLK_DEV_NBD=y`;
- `CONFIG_USB_ETH=y`;
- `CONFIG_USB_G_ANDROID=n`;
- persistent Android RAM console support enabled;
- SDCC1/eMMC registration disabled and source transformation verified;
- LineageOS ARM GCC 4.9 toolchain pinned to commit `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`;
- build manifest records kernel/toolchain/config/zImage identity;
- unknown tracked kernel source changes fail closed.

### P1-001 — historical defconfig modification

The existing kernel tree had a tracked experimental change in `arch/arm/configs/lineageos_flo_defconfig`. v2 no longer trusts the working-tree copy; it loads the pristine defconfig directly from the pinned commit. The old modification is explicitly ignored and cannot affect the build.

### P1-002 — Linux 3.4 has no `olddefconfig`

This tree provides `oldconfig`, `silentoldconfig`, and `oldnoconfig`, but not modern `olddefconfig`. v2 now uses non-interactive `oldnoconfig`, followed by explicit invariant verification.

### P1-003 — host GCC 12 cannot build Linux 3.4

The original wrapper accidentally selected Debian GCC 12, producing:

```text
fatal error: linux/compiler-gcc12.h: No such file or directory
```

v2 now uses only the pinned LineageOS GCC 4.9 checkout and rejects incompatible compiler versions.

---

## Phase 2 — one partitioned NBD disk

Status: **in progress; host-side disk build/validation gate pending**.

Design correction made before implementation:

A DOS/MBR disk cannot contain six primary partitions. The single NBD disk therefore uses three primary partitions, one extended partition, and three logical partitions:

```text
/dev/nbd0
  p1  system      primary   ext4  RO policy
  p2  vendor      primary   ext4  RO policy
  p3  cache       primary   ext4  RW
  p4  extended    container
  p5  userdata    logical   ext4  RW
  p6  persist     logical   ext4  RW
  p7  metadata    logical   raw/reserved
```

The built-in Linux 3.4 NBD driver defaults to `max_part=0`, so the later v2 boot contract must include:

```text
nbd.max_part=8
```

Without that parameter the kernel allocates no partition minors for `/dev/nbd0`.

Implemented so far:

- `diskless-v2/layout.json` is the single source of truth for partition sizes/order;
- `scripts/v2/assemble_disk.py` creates a sparse DOS disk with deterministic MBR/EBR metadata and embeds the component filesystem images;
- all data partitions are aligned to 1 MiB boundaries;
- system/vendor source images are never modified in place;
- existing Linux-3.4-compatible ext4 creation is reused for cache/userdata/persist;
- `scripts/v2/validate_disk.py` independently parses the final MBR and EBR chain and verifies actual LBA/size/type values and ext4 superblock magic;
- `scripts/v2/build_disk.sh` performs component creation, assembly, and independent validation as one host-side gate;
- `scripts/v2/serve_disk.sh` exports exactly one read-write NBD disk on port `10810` using the existing instrumented oldstyle server.

Current Phase 2 gate:

1. Build the combined disk on the Mac where the extracted system/vendor images already exist.
2. Require `DISKLESS_V2_DISK_ASSEMBLED=1`.
3. Require `DISKLESS_V2_DISK_VERIFIED=1`.
4. Do not boot the Nexus yet.

After the host-side gate passes, Phase 2 continues with the transport-only boot: attach only `/dev/nbd0`, verify `/dev/nbd0p1`, `p2`, `p3`, `p5`, `p6`, `p7`, and run the standalone read/write stress test before Android is allowed to start.
