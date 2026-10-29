# Diskless v2 implementation progress

This file records implementation state and issues encountered while executing `DISKLESS_V2_EXECUTION.md`.

## Phase 1 — deterministic diskless kernel

Status: **PASSED**.

Accepted invariants:

- kernel source pinned to LineageOS flo commit `0da5107137f93b8d8f697e949ab0784f5ace450c`;
- pristine `lineageos_flo_defconfig` loaded from the pinned commit;
- `ARCH=arm` explicit;
- `CONFIG_BLK_DEV_NBD=y`;
- `CONFIG_USB_ETH=y`;
- `CONFIG_USB_G_ANDROID=n`;
- persistent RAM / Android ram console enabled;
- SDCC1/eMMC registration disabled and verified;
- LineageOS ARM GCC 4.9 pinned at `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`;
- kernel/config/toolchain/zImage identities recorded in a manifest;
- unknown tracked kernel source modifications fail closed.

Acceptance evidence:

```text
DISKLESS_V2_KERNEL_VERIFIED=1
Diskless v2 kernel build passed verification.
zImage: /home/debian/diskless_test/android_kernel_google_msm/out/arch/arm/boot/zImage
manifest: /home/debian/nexus7_test/out/diskless-v2-kernel-manifest.txt
```

Resolved issues:

- **P1-001:** historical working-tree `lineageos_flo_defconfig` modification. v2 ignores that copy and reads the pristine defconfig from the pinned commit.
- **P1-002:** Linux 3.4 has no `olddefconfig`. v2 uses `oldnoconfig` and verifies all required symbols afterwards.
- **P1-003:** Debian GCC 12 cannot compile this legacy tree. v2 uses only the pinned LineageOS GCC 4.9 toolchain.

---

## Phase 2 — single partitioned NBD disk

Status: **PASSED**.

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

Host-side acceptance on macOS:

```text
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
Diskless v2 host disk passed validation.
```

The combined image is sparse. Accepted build: about 5.8 GiB logical size and about 1.2 GiB allocated host storage.

Implemented:

- `diskless-v2/layout.json` as the single partition-layout source of truth;
- deterministic MBR + extended/EBR assembly;
- host-side independent MBR/EBR validation;
- system/vendor copied into RO-policy partitions;
- Linux-3.4-compatible ext4 cache/userdata/persist;
- raw reserved metadata partition;
- exactly one NBD export on port `10810`.

---

## Phase 3 — v2 initramfs transport supervisor

Status: **PASSED**.

Implemented:

- transport-only initramfs independent of Android init ordering;
- `usb0` configured as `172.16.42.1/24`;
- exactly one NBD session attached to `/dev/nbd0`;
- `nbd.max_part=8` boot policy;
- manual `/dev/nbd0p*` nodes because flo has no devtmpfs;
- partition sizes validated against `layout.json`;
- p1/p2 mounted `ro,noload`;
- p3/p5/p6 mounted RW;
- p7 validated but intentionally left raw/unmounted;
- userdata random write -> sync -> checksum -> unmount -> remount -> checksum integrity test;
- `/proc/last_kmsg` preserved for diagnostics;
- HTTP status/diagnostics on port `2325` and raw shell on `2324`;
- kernel panic timeout set to 5 seconds for diagnostic boots;
- NBD attach retry while macOS recreates/configures USB Ethernet;
- NBD liveness checked from kernel `/sys/block/nbd0/pid` plus non-zero device capacity.

Transport boot-image build acceptance:

```text
DISKLESS_V2_TRANSPORT_IMAGE_BUILT=1
boot_image=/home/debian/nexus7_test/out/diskless-v2-transport.img
sha256=f3da57d698fdf62e1579cccfb54459abe38e31bbb44e38e78c4a5cf4c8718f13
board=flo-v2-xport
```

Real-device transport acceptance on Nexus 7:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
uptime=617.14 1581.34
```

This closes the raw transport gate: one USB Ethernet link, one NBD TCP session, DOS/EBR partition discovery, RO system/vendor reads, RW userdata traffic, remount checksum validation, and more than 10 minutes of sustained block I/O all completed without transport loss.

Resolved issues:

- **P2-001:** Android boot header v0 board label exceeded 16 bytes. Fixed with deterministic short label `flo-v2-xport` and an explicit preflight length check.
- **P2-002:** false FAIL caused by BusyBox `nbd-client` daemonization. `$!` tracked the short-lived launcher PID, not the active NBD session. The verifier now uses `/sys/block/nbd0/pid`, which the Linux 3.4 NBD driver creates for the lifetime of `NBD_DO_IT`.
- Diagnostic raw shell commands must invoke BusyBox applets explicitly unless symlinks are present; this did not affect transport correctness but was identified during live inspection.

---

## Next phase — Phase 4: protect USB root transport

Status: **NEXT**.

Do not start Android integration yet. The standalone transport is stable, but normal Lineage boot enables additional USB/OTG and power-management behavior that was implicated in v1 late-boot stalls.

Next tasks from `DISKLESS_V2_EXECUTION.md`:

1. audit flo `msm_otg` and CI13xxx suspend/resume, charger detection, PHY low-power and runtime-PM paths used by this kernel;
2. make `androidboot.diskless=1` an explicit kernel policy input rather than only a cmdline marker;
3. in diskless mode, prevent USB controller/PHY transitions that can sever the active root-storage transport;
4. verify charger/power-source detection cannot reconfigure the USB data path;
5. confirm `CONFIG_USB_G_ANDROID=n` prevents Android USB userspace from rebinding/reconfiguring the UDC;
6. only after this protection gate passes, generate the deterministic `/dev/nbd0pN` Android fstab and begin stock-as-possible Lineage integration.

Phase 4 gate: transport remains alive through CPU idle / low-power enable, screen-state changes and normal Lineage `boot` actions.
