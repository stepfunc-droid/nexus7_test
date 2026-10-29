# Diskless v2 Phase 5D — Android first-stage mount probe

Status: **PASSED on real device**.

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

Phase 5C rebuilt the separate Android-test disk and passed:

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

Accepted invariant identities:

```text
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
android_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
android_init=preserved-as-/init.android
probe_init=single-nbd-supervisor
selinux_policy=stock-cmdline-unchanged
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

1. mounts minimal proc/sysfs/devpts needed for transport bring-up;
2. configures `usb0=172.16.42.1/24`;
3. attaches exactly one NBD session to Mac port `10810`;
4. validates p1/p2/p3/p5/p6/p7 sizes from `layout.json`;
5. does **not** mount system or vendor itself;
6. starts diagnostic HTTP on port 2325;
7. streams live kernel evidence to Mac port `11000`;
8. removes or lazy-detaches all probe-owned VFS mounts before executing the exact original Lineage `/init` as `/init.android`;
9. observes Android's own fs_mgr mount-success records in the live kmsg stream;
10. after both `/system` and `/vendor` are proven from the NBD partitions, verifies the same kernel NBD PID and sends `SIGSTOP` to PID 1.

PASS requires Android itself to produce exactly:

```text
/dev/block/nbd0p1 -> /system
/dev/block/nbd0p2 -> /vendor
```

with the same `/sys/block/nbd0/pid` as before Android handoff.

## P5D-001 — probe-owned `/dev/pts` broke Android SwitchRoot — RESOLVED

The first real-device probe proved `/system` mount, then failed in Lineage `SwitchRoot()`:

```text
nbd0: p1 p2 p3 p4 < p5 p6 p7 >
init.android: init first stage started!
init.android: [libfs_mgr]__mount(source=/dev/block/nbd0p1,target=/system,type=ext4)=0: Success
init.android: Switching root to '/system'
init.android: Unable to move mount at '/dev/pts': No such file or directory
init.android: InitFatalReboot: signal 6
```

The failure was in the probe harness: it had mounted devpts before handoff but left it mounted. Lineage `SwitchRoot()` enumerates `/proc/mounts` and `MS_MOVE`s old mounts into the new root; the hidden stale `/dev/pts` mount therefore triggered `PLOG(FATAL)`.

Fix: remove probe-owned `/dev/pts` before Android handoff. No Android source, fstab policy, kernel policy, NBD layout or rc file changed.

## P5D-002 — persistent last_kmsg could be overwritten — RESOLVED

A subsequent normal boot can overwrite persistent ram-console evidence from the failed probe. Phase 5D therefore no longer relies on a later `/proc/last_kmsg` fetch as its primary evidence path.

Fix: stream the current probe's `/proc/kmsg` live to Mac port `11000`, storing it in `~/phase5d-live-kmsg.txt` before any later reboot can overwrite persistent RAM.

## P5D-003 — probe-owned sysfs descriptor blocked normal umount — RESOLVED

The first live-kmsg implementation pinned `/sys/block/nbd0/pid` through an open file descriptor, then attempted a normal `umount /sys`, causing the supervisor itself to stop before Android handoff:

```text
DISKLESS_V2_ANDROID_PROBE_STATUS=FAIL
detail=umount /sys failed before Android handoff
```

Fix: lazy-detach the probe-owned sysfs mount while retaining the already-open NBD PID descriptor needed for the post-mount identity check. The live-kmsg transport was also simplified to remove the FIFO false-positive connection path and emits an explicit stream handshake before Android handoff.

## Final real-device Phase 5D gate — PASSED

Accepted result:

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
evidence=~/phase5d-live-kmsg.txt
```

This proves on real hardware that:

- the accepted Phase 4 diskless kernel remains in use;
- one NBD TCP session exposes the partitioned root-storage disk;
- Android first-stage recreates and resolves `/dev/block/nbd0pN` correctly;
- the original Lineage first-stage init mounts `/system` from p1 and `/vendor` from p2;
- the NBD kernel session does not change across first-stage handoff;
- no v1 Android rc bypass is required for this gate.

Phase 5 is therefore complete. Phase 6 may now test full Android integration beyond the intentionally stopped first-stage boundary.
