# Diskless v2 Phase 5D — Android first-stage mount probe

Status: **probe image build PASSED; real-device gate reached /system mount; probe-owned devpts handoff bug fixed; rerun pending**.

## Purpose

This gate answers one binary question only:

> Can the original LineageOS first-stage `/init` mount `/system` and `/vendor` from the single partitioned NBD disk using the deterministic Phase 5 fstab, without any eMMC lookup or v1 Android rc bypass?

It is deliberately **not** a full Android boot test.

## Accepted prerequisites

Phase 4 real-device USB/root-transport gate passed with:

```text
KERNEL_ZIMAGE_SHA256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
usb_diskless_guard=enabled
usb_system_suspend_guard=pm_notifier
DISKLESS_V2_PHASE4_VERIFIED=1
```

Phase 5B produced and independently verified fstab-only boot/vendor artifacts. After auditing LineageOS 18.1 first-stage device creation, the Android block namespace was corrected to:

```text
/system   /dev/block/nbd0p1
/vendor   /dev/block/nbd0p2
/cache    /dev/block/nbd0p3
/data     /dev/block/nbd0p5
/persist  /dev/block/nbd0p6
metadata  /dev/block/nbd0p7
```

The corrected generated fstab has:

```text
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
```

Phase 5C then rebuilt the separate Android-test disk and passed:

```text
DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_PREPARED=1
```

The disk is:

```text
~/nexus7-diskless-v2/diskless-v2-android.raw.img
```

using exact clean system p1 and exact fstab-only vendor p2. The previously accepted Phase 3/4 transport-only disk remains untouched.

## Probe image construction — PASSED

`scripts/v2/build_android_first_stage_probe.sh` consumes:

```text
out/diskless-v2-android/boot-fstab-only.img
out/diskless-v2-transport.img
out/diskless-v2-android/fstab.flox
```

The accepted transport image supplies the exact Phase 4 kernel, BusyBox and NBD layout contract. The builder rejects the image unless the extracted kernel SHA-256 matches `diskless-v2/phase4-accepted.env`.

Accepted initial build result:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1
output=out/diskless-v2-android/android-first-stage-probe.img
output_sha256=ffdfa8543b854f1a8085b73dce5db1b06b462201bd8b43cb5d97f644d070580d
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
android_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
android_init=preserved-as-/init.android
probe_init=single-nbd-supervisor
selinux_policy=stock-cmdline-unchanged
late_android_boot=intentionally-stopped-after-first-stage-mounts
DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_IMAGE_BUILT=1
android_init=preserved
android_rc_bypasses=none
probe_scope=first-stage-system-vendor-mounts-only
```

The probe ramdisk transformation is explicit:

```text
original /init payload -> /init.android unchanged
/init                  -> diskless single-NBD supervisor
/bin/busybox            -> copied from accepted Phase 4 transport image
/etc/diskless-v2-layout -> copied from accepted Phase 4 transport image
/fstab.flox             -> unchanged Phase 5 generated fstab
```

No Android rc file is patched. No SELinux permissive flag is added. No devwait, ADSP, installd or Android USB bypass is added.

## Runtime behavior

The supervisor:

1. mounts only minimal proc/sysfs/devpts needed for transport bring-up;
2. configures `usb0=172.16.42.1/24`;
3. attaches exactly one NBD session to Mac port `10810`;
4. validates p1/p2/p3/p5/p6/p7 sizes from `layout.json`;
5. does **not** mount system or vendor itself;
6. starts diagnostic HTTP on port 2325 and captures current `/proc/kmsg` to `/www/kmsg.txt`;
7. starts a passive mount watcher;
8. removes every probe-owned VFS mount (`/dev/pts`, `/sys`, then lazy-detached `/proc`) before `exec` of the exact original Lineage `/init` as `/init.android`.

The watcher observes `/proc/mounts` only. It never mounts Android partitions. Once `/system` is visible it increases polling frequency so it can stop PID 1 at the `/vendor` boundary before the original ramdisk is freed.

PASS requires Android itself to produce exactly:

```text
/dev/block/nbd0p1 -> /system
/dev/block/nbd0p2 -> /vendor
```

with the same kernel `/sys/block/nbd0/pid` that existed before Android handoff.

As soon as both mounts are visible, the watcher records:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS
```

and sends `SIGSTOP` to PID 1. This prevents SELinux setup, second-stage init, ADSP/devwait, installd or normal boot triggers from contaminating this first-stage-only experiment.

## P5D-001 — probe-owned `/dev/pts` broke Android SwitchRoot — RESOLVED

The first real-device probe established exactly one NBD connection and reached original Lineage first-stage init. Persistent ram-console evidence showed:

```text
nbd0: p1 p2 p3 p4 < p5 p6 p7 >
init.android: init first stage started!
init.android: [libfs_mgr]__mount(source=/dev/block/nbd0p1,target=/system,type=ext4)=0: Success
init.android: Switching root to '/system'
init.android: Unable to move mount at '/dev/pts': No such file or directory
init.android: InitFatalReboot: signal 6
```

This proves the single-NBD transport, partition discovery, corrected Android block namespace, stock first-stage fstab parsing and `/system` first-stage mount all worked. The failure was in the probe harness: it had mounted devpts before handoff but removed only `/sys` and `/proc`.

LineageOS 18.1 `SwitchRoot()` reads `/proc/mounts` and `MS_MOVE`s every old mount except `/` and the new root. After first-stage overlays `/dev` with its own tmpfs, the stale probe-owned `/dev/pts` mount cannot be moved and triggers `PLOG(FATAL)`.

Fix:

```text
probe handoff now unmounts /dev/pts first, then /sys, then lazy-detaches /proc
```

No Android source, fstab policy, kernel policy, NBD layout or rc file was changed for this fix.

## Host gate

`scripts/v2/phase5_first_stage_gate.sh` requires:

- `FIRST_STAGE_PASS` HTTP status;
- `/system` source exactly `/dev/block/nbd0p1`;
- `/vendor` source exactly `/dev/block/nbd0p2`;
- unchanged kernel NBD PID across Android handoff;
- PID 1 stopped at the first-stage boundary;
- exactly one successful Mac NBD client connection;
- no obvious NBD server/protocol error;
- a kmsg copy containing the first-stage PASS marker.

Formal success marker:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1
system_mount=/dev/block/nbd0p1
vendor_mount=/dev/block/nbd0p2
single_nbd_connection=PASS
android_late_boot=not-tested
```

Only after this marker may Phase 5 be considered complete and Phase 6 full Android integration begin.
