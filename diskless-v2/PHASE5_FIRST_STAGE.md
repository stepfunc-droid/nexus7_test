# Diskless v2 Phase 5D — Android first-stage mount probe

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

Phase 5B produced and independently verified:

```text
boot-fstab-only.img
vendor-fstab.raw.img
```

with the original Lineage `/init` unchanged and vendor changed only inside the exact stock fstab data range.

Phase 5C produced the separate Android-test disk:

```text
~/nexus7-diskless-v2/diskless-v2-android.raw.img
```

using:

```text
p1 = exact clean system.raw.img
p2 = exact fstab-only vendor copy
```

The previously accepted transport-only disk remains untouched.

## Probe image construction

`scripts/v2/build_android_first_stage_probe.sh` consumes:

```text
out/diskless-v2-android/boot-fstab-only.img
out/diskless-v2-transport.img
out/diskless-v2-android/fstab.flox
```

The accepted transport image supplies the exact Phase 4 kernel, BusyBox and NBD layout contract. The builder rejects the image unless the extracted kernel SHA-256 matches `diskless-v2/phase4-accepted.env`.

The Phase 5B Android boot artifact supplies the stock Lineage ramdisk with the exact generated fstab.

The probe ramdisk transformation is explicit:

```text
original /init payload -> /init.android unchanged
/init                  -> diskless single-NBD supervisor
/bin/busybox            -> copied from accepted Phase 4 transport image
/etc/diskless-v2-layout -> copied from accepted Phase 4 transport image
/fstab.flox             -> unchanged Phase 5 generated fstab
```

No Android rc file is patched. No SELinux permissive flag is added. No devwait, ADSP, installd or Android USB bypass is added.

The stock Android boot cmdline is preserved except for the explicit diskless transport policy:

```text
androidboot.diskless=1
nbd.max_part=8
panic=5
rdinit=/init
```

## Runtime behavior

The supervisor:

1. mounts only minimal proc/sysfs needed for transport bring-up;
2. configures `usb0=172.16.42.1/24`;
3. attaches exactly one NBD session to Mac port `10810`;
4. validates p1/p2/p3/p5/p6/p7 sizes from `layout.json`;
5. does **not** mount system or vendor itself;
6. starts diagnostic HTTP on port 2325 and captures current `/proc/kmsg` to `/www/kmsg.txt`;
7. starts a passive mount watcher;
8. unmounts its temporary sysfs/proc and `exec`s the exact original Lineage `/init` as `/init.android`.

The watcher observes `/proc/mounts` only. It never mounts Android partitions.

PASS requires Android itself to produce:

```text
*nbd0p1 -> /system
*nbd0p2 -> /vendor
```

with the same kernel `/sys/block/nbd0/pid` that existed before Android handoff.

As soon as both mounts are visible, the watcher records:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS
```

and sends `SIGSTOP` to PID 1. This intentionally prevents SELinux setup, second-stage init, ADSP/devwait, installd or normal boot triggers from contaminating this first-stage-only experiment.

## Host gate

`scripts/v2/phase5_first_stage_gate.sh` requires:

- `FIRST_STAGE_PASS` HTTP status;
- `/system` source ending in `nbd0p1`;
- `/vendor` source ending in `nbd0p2`;
- unchanged kernel NBD PID across Android handoff;
- exactly one successful Mac NBD client connection;
- a kmsg copy containing the first-stage PASS marker.

Formal success marker:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1
```

Only after this marker may Phase 5 be considered complete and Phase 6 full Android integration begin.
