# Diskless v2 implementation progress

This file records implementation state and issues encountered while executing `DISKLESS_V2_EXECUTION.md`.

## Phase 1 — deterministic diskless kernel

Status: **PASSED**.

Acceptance evidence from the Debian build host:

```text
DISKLESS_V2_KERNEL_VERIFIED=1
Diskless v2 kernel build passed verification.
zImage: /home/debian/diskless_test/android_kernel_google_msm/out/arch/arm/boot/zImage
manifest: /home/debian/nexus7_test/out/diskless-v2-kernel-manifest.txt
```

Implemented invariants:

- kernel source baseline pinned to LineageOS flo commit `0da5107137f93b8d8f697e949ab0784f5ace450c`;
- pristine `lineageos_flo_defconfig` read directly from the pinned commit;
- explicit `ARCH=arm`;
- `CONFIG_BLK_DEV_NBD=y`;
- `CONFIG_USB_ETH=y`;
- `CONFIG_USB_G_ANDROID=n`;
- persistent Android RAM console support enabled;
- SDCC1/eMMC registration disabled and source transformation verified;
- LineageOS ARM GCC 4.9 pinned at `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`;
- build manifest records kernel/toolchain/config/zImage identity;
- unknown tracked kernel source changes fail closed.

Resolved Phase 1 issues:

- **P1-001:** historical working-tree `lineageos_flo_defconfig` modification. v2 now reads the pristine defconfig from the pinned commit.
- **P1-002:** Linux 3.4 has no `olddefconfig`. v2 uses `oldnoconfig` and verifies invariants afterwards.
- **P1-003:** Debian GCC 12 cannot compile this legacy tree. v2 uses only the pinned LineageOS GCC 4.9 toolchain.

---

## Phase 2 — one partitioned NBD disk + transport acceptance

Status: **host disk PASSED; real-device transport gate pending**.

### Host disk acceptance — PASSED

Observed on macOS:

```text
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
Diskless v2 host disk passed validation.
```

Accepted layout:

```text
/dev/nbd0
  p1 system    primary   ext4 RO   3072000 sectors
  p2 vendor    primary   ext4 RO    512000 sectors
  p3 cache     primary   ext4 RW    151552 sectors
  p4 extended                    8462336 sectors
  p5 userdata  logical   ext4 RW   8388608 sectors
  p6 persist   logical   ext4 RW     32768 sectors
  p7 metadata  logical   raw          32768 sectors
```

The combined image is sparse. In the accepted build its logical size was about 5.8 GiB while allocated host storage was about 1.2 GiB.

### Transport-only implementation

Implemented:

- `initramfs/diskless-v2-transport-init`;
- `scripts/v2/build_transport_image.sh`;
- `scripts/v2/serve_disk.sh` for exactly one NBD export on port `10810`;
- boot contract: `androidboot.diskless=1 nbd.max_part=8 panic=5`;
- manual `/dev/nbd0` and `/dev/nbd0p1..p15` creation because flo has no devtmpfs;
- partition expectations generated from `diskless-v2/layout.json` and embedded into the initramfs;
- p1/p2 mounted `ro,noload`;
- p3/p5/p6 mounted read-write;
- p7 is intentionally raw/reserved and is validated but not mounted;
- userdata random write -> sync -> checksum -> unmount -> remount -> checksum integrity test;
- 10-minute acceptance loop repeatedly reads system/vendor and writes/reads userdata;
- status and diagnostics exposed through BusyBox HTTP on port 2325 when available;
- `/proc/last_kmsg` copied into HTTP diagnostics when present;
- kernel oops promoted to panic and panic timeout set to 5 seconds;
- initial NBD attach retries if the macOS USB Ethernet side is not configured yet, so host interface timing is not mistaken for a transport failure.

Relevant transport implementation commits:

```text
8a9b1f4aa9bc0d2423b0ce4c1f37964c35b24754  initial transport initramfs
98347b939818a9cfc1c22fd6fcff06f1bb033489  deterministic transport boot-image builder
a5f54523376184a63a00f7b2d16555e4d2209aa0  keep raw metadata unmounted
6ce2c62bb1ce6353bf09c01dcbfe77854beb69ac  retry initial NBD attach until host is ready
```

### Real-device Phase 2 gate

Do **not** start Android yet.

Pass requires:

1. exactly one NBD client/export;
2. p1/p2/p3/p5/p6/p7 visible with expected capacities;
3. system/vendor/cache/userdata/persist mounts succeed;
4. userdata checksum survives unmount/remount;
5. the 10-minute stress loop reaches `DISKLESS_V2_TRANSPORT_STATUS=PASS`;
6. Mac-side NBD server reports no disconnect/transport exception;
7. USB packet processing remains alive through the entire test.

Only after this gate passes may Android integration begin.
