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

## Phase 4 — protect USB root transport

Status: **kernel gate PASSED; real-device power gate pending**.

Audit document:

```text
diskless-v2/PHASE4_USB_AUDIT.md
```

### Audit findings

1. flo uses `USB_OTG`, `OTG_PMIC_CONTROL`, and the SNPS 28 nm integrated PHY.
2. flo's `msm_otg_pdata` does **not** enable `enable_lpm_on_dev_suspend`, so stock flo does not set `ALLOW_LPM_ON_DEV_SUSPEND`.
3. CI13xxx gadget suspend does not itself power down the PHY/controller; it ultimately delegates through `usb_phy_set_suspend()` to `msm_otg`.
4. Stock `msm_otg_suspend()` already rejects many active B-session suspend attempts with `-EBUSY`, which is consistent with the stable Phase 3 transport result.
5. This implicit behavior is not strong enough as the root-storage contract: it depends on platform-data, charger classification and future code remaining unchanged.
6. `CONFIG_USB_G_ANDROID=n` remains a separate hard invariant, so Android's normal composite gadget cannot bind and replace g_ether.

### Implemented explicit diskless policy

Added `scripts/v2/patch_kernel_usb_guard.py`, applied by `configure_kernel.sh` and independently reconstructed by `verify_kernel.sh`.

The exact allowed `msm_otg.c` transformation:

- parses `androidboot.diskless=1`;
- exposes read-only `/sys/module/msm_otg/parameters/diskless_mode`;
- refuses a B-peripheral bus-suspend LPM transition in diskless mode;
- returns `-EBUSY` from OTG runtime/system suspend before PHY retention, clock shutdown or regulator power-collapse logic can run while `OTG_STATE_B_PERIPHERAL + B_SESS_VLD` is the active diskless root transport.

The patch deliberately does **not** disable charger detection, global CPU/RPM low power, host mode, idle-state PM or non-diskless OTG behavior.

Kernel verification now reports:

```text
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
```

and `build_transport_image.sh` refuses to package a kernel without that verified guard.

### Phase 4 deterministic kernel gate — PASSED

Observed on the Debian build host:

```text
DISKLESS_V2_KERNEL_VERIFIED=1
kernel_source_state=baseline-plus-exact-sdcc1-and-usb-diskless-patches
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=d56a4a5864acf5c18e5f11446b0e760af28a02d9d66c01ee83718b59a4f399aa
config_panic_timeout=5
usb_gadget=g_ether
usb_android_gadget=disabled
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
persistent_ram_console=enabled
sdcc1_emmc=disabled
```

This closes the Phase 4 build/reproducibility sub-gate. The remaining Phase 4 requirement is the real-device power/USB test below.

### Phase 4 real-device gate

Added:

```text
scripts/v2/phase4_power_test.sh
```

It runs while the existing ten-minute NBD stress loop is active and:

1. requires the live kernel `diskless_mode` parameter to be active;
2. records the kernel NBD session PID;
3. reproduces flo Lineage's stock `enable-low-power` RPM/CPU retention/power-collapse sysfs writes;
4. blanks/unblanks fb0 when supported;
5. puts the actual `msm_otg` platform device under runtime-PM `auto` policy;
6. performs a controlled system-suspend request when supported;
7. requires the same NBD session afterwards;
8. performs immediate system-partition read and userdata write/readback I/O;
9. waits for the original ten-minute transport stress gate to PASS;
10. requires exactly one Mac-side NBD connection and no server/transport exception.

Formal success marker:

```text
DISKLESS_V2_PHASE4_VERIFIED=1
```

Do not begin Phase 5 Android fstab/image work until this marker is observed on the real device.
