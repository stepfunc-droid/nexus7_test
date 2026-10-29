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
- unknown tracked kernel source modifications fail closed.

Resolved issues:

- **P1-001:** historical working-tree defconfig contamination.
- **P1-002:** Linux 3.4 lacks `olddefconfig`; v2 uses `oldnoconfig` plus invariant checks.
- **P1-003:** Debian GCC 12 is incompatible with this tree; v2 pins LineageOS ARM GCC 4.9.

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

Host acceptance:

```text
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
```

One sparse raw disk is exported through exactly one NBD TCP session on port `10810`.

---

## Phase 3 — v2 initramfs transport supervisor

Status: **PASSED**.

Implemented and accepted:

- transport-only initramfs independent of Android init ordering;
- `usb0=172.16.42.1/24`;
- exactly one NBD session on `/dev/nbd0`;
- DOS/EBR partition discovery and exact size validation;
- p1/p2 RO, p3/p5/p6 RW, p7 raw/unmounted;
- userdata write/sync/checksum/unmount/remount/checksum test;
- persistent `/proc/last_kmsg` capture;
- HTTP diagnostics on 2325 and raw shell on 2324;
- NBD liveness from kernel `/sys/block/nbd0/pid`.

Accepted real-device result:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
```

Resolved issues:

- **P2-001:** Android boot header v0 board name exceeded 16 bytes.
- **P2-002:** BusyBox `nbd-client` daemonization caused a false FAIL; kernel NBD pid is authoritative.

---

## Phase 4 — protect USB root transport

Status: **PASSED**.

Accepted kernel identity:

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
usb_gadget=g_ether
usb_android_gadget=disabled
usb_diskless_guard=enabled
usb_system_suspend_guard=pm_notifier
system_suspend_policy=blocked-in-diskless-mode
persistent_ram_console=enabled
sdcc1_emmc=disabled
```

Final real-device gate:

```text
DISKLESS_V2_PHASE4_SUSPEND=PASS
nbd_pid_before=276
nbd_pid_after=276

DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=171 checksum=0e9fbf0a07142896c8cf8d3e3bded48c

DISKLESS_V2_PHASE4_VERIFIED=1
isolation_gate=PASS
system_suspend_guard=PASS
transport_stress=PASS
single_nbd_connection=PASS
usb_root_transport=protected
```

Resolved issues:

- **P4-001:** combined test changed the NBD session during forced system suspend.
- **P4-002:** normal runtime low-power, framebuffer and OTG runtime-PM actions were isolated and proven safe.
- Layer 2 blocks system suspend at `PM_SUSPEND_PREPARE` in diskless mode.

---

## Phase 5 — deterministic Android fstab/image

Status: **PASSED**.

### Phase 5A — deterministic fstab generation — PASSED

Pinned device-tree baseline:

```text
LineageOS/android_device_asus_flox
commit=936d74531565ca36e663e71dbcd43212fa93071b
stock_fstab_sha256=ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
```

**P5-001:** the initial `/dev/nbd0pN` mapping was rejected after auditing LineageOS 18.1 first-stage `/dev` recreation. Android block uevents create `/dev/block/<basename>`, so the accepted mapping is:

```text
system=/dev/block/nbd0p1
vendor=/dev/block/nbd0p2
cache=/dev/block/nbd0p3
userdata=/dev/block/nbd0p5
persist=/dev/block/nbd0p6
metadata=/dev/block/nbd0p7
```

Accepted corrected generated fstab:

```text
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
emmc_references=absent
f2fs_fallbacks=absent
vendor_formattable=disabled
usb_vold=preserved
zram=preserved
```

### Phase 5B — exact boot/vendor fstab replacement — PASSED

Accepted properties:

- stock Lineage boot `/init` preserved byte-for-byte;
- only `/fstab.flox` replaced in the boot ramdisk;
- only `/etc/fstab.flox` replaced in the vendor image;
- no v1 devwait, USB, installd, SELinux or panic-policy patch imported;
- corrected Android `/dev/block/nbd0pN` fstab packaged into both required artifacts.

### Phase 5C — Android-test disk assembly — PASSED

Accepted markers:

```text
DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_PREPARED=1
```

Android-test disk:

```text
~/nexus7-diskless-v2/diskless-v2-android.raw.img
```

It uses exact clean system p1 and the exact fstab-only vendor p2. The accepted Phase 3/4 transport disk remains separate.

### Phase 5D — original Lineage first-stage mount gate — PASSED

The probe uses the accepted Phase 4 kernel:

```text
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
android_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
android_rc_bypasses=none
```

Resolved probe-only issues:

- **P5D-001:** probe-owned `/dev/pts` caused Lineage `SwitchRoot()` to fatal after `/system` mounted. Fix: remove probe devpts before handoff.
- **P5D-002:** later normal boots can overwrite persistent `last_kmsg`. Fix: stream current `/proc/kmsg` live to Mac port `11000`.
- **P5D-003:** an open `/sys/block/nbd0/pid` fd caused normal `umount /sys` to fail before handoff. Fix: lazy-detach probe sysfs while retaining the pinned descriptor; remove the FIFO false-positive live-kmsg connection path.

Final accepted real-device result:

```text
DISKLESS_V2_LIVE_KMSG_STREAM=1 nbd_pid=258
DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS nbd_pid_before=258 nbd_pid_after=258 system_source=/dev/block/nbd0p1 vendor_source=/dev/block/nbd0p2 pid1_action=SIGSTOP-after-first-stage-mounts

DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1
system_mount=/dev/block/nbd0p1
vendor_mount=/dev/block/nbd0p2
nbd_session=unchanged:258
android_init=original-Lineage-first-stage
pid1=SIGSTOP-at-first-stage-gate
single_nbd_connection=PASS
android_late_boot=not-tested
```

This proves on real hardware that the original Lineage first-stage init can use the single NBD disk, recreate the correct `/dev/block/nbd0pN` namespace, mount `/system` from p1 and `/vendor` from p2, and preserve the same live NBD kernel session across handoff without v1 Android rc bypasses.

**Phase 5 is closed.**

---

## Phase 6 — full Android integration

Status: **NOT STARTED**.

Scope:

- remove the intentional first-stage `SIGSTOP` boundary;
- retain the accepted Phase 4 kernel, one-NBD transport and Phase 5 fstab/image unchanged;
- let original Lineage continue into SELinux setup and second-stage init;
- classify the first new failure before changing Android behavior;
- do not reintroduce broad v1 USB/devwait/ADSP/installd bypasses;
- keep live kmsg evidence on the Mac so reboot cannot erase the decisive log.
