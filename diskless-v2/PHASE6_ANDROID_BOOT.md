# Diskless v2 Phase 6 — Android boot integration

Status: **IN PROGRESS — Phase 6A stock second-stage entry prepared; real-device run pending**.

## Purpose

Phase 5 proved that original LineageOS first-stage init can mount `/system` and `/vendor` from the single partitioned NBD disk with the same NBD session and no v1 rc bypasses.

Phase 6 now removes the intentional first-stage `SIGSTOP` and lets the same original Lineage userspace continue normally.

The baseline remains deliberately stock-as-possible:

- accepted Phase 4 kernel unchanged;
- accepted Phase 5 fstab unchanged;
- same Android-test single-NBD disk unchanged;
- SELinux enforcing baseline; no permissive cmdline flag;
- no devwait, ADSP, installd, Android USB or other v1 rc bypass;
- live kernel log streamed to Mac TCP/11000 before Android handoff;
- `panic=5` and `panic_on_oops=1` retained for evidence recovery.

## Phase 6A — stock second-stage entry

This first sub-gate answers one binary question:

> After the already-proven NBD-backed first-stage mounts, can stock Lineage proceed through SELinux setup and enter `SecondStageMain()` without a fatal reboot, panic or transport replacement?

The LineageOS 18.1 second-stage entry emits:

```text
init second stage started!
```

The Phase 6A host gate therefore requires:

1. `DISKLESS_V2_PHASE6_LIVE_KMSG_STREAM=1` from the supervisor;
2. exact first-stage `/system` mount success from `/dev/block/nbd0p1`;
3. exact first-stage `/vendor` mount success from `/dev/block/nbd0p2`;
4. `init second stage started!`;
5. exactly one successful Mac NBD connection;
6. no NBD server/protocol error.

It fails early if it sees `InitFatalReboot`, kernel panic, attempted init kill, or reboot before second-stage.

Formal Phase 6A success marker:

```text
DISKLESS_V2_PHASE6_SECOND_STAGE_REACHED=1
system_mount=/dev/block/nbd0p1
vendor_mount=/dev/block/nbd0p2
single_nbd_connection=PASS
selinux_policy=stock-enforcing-baseline
android_rc_bypasses=none
full_android_boot=continuing
phase6_final_gate=not-yet-passed
```

This marker does **not** complete Phase 6. It only closes the SELinux/second-stage transition gate.

## Full-boot supervisor

`initramfs/diskless-v2-android-full-init` is separate from the accepted Phase 5D probe wrapper.

It performs only transport responsibilities before Android:

1. mount temporary proc/sysfs/devpts;
2. configure `usb0=172.16.42.1/24`;
3. attach exactly one NBD session to Mac port 10810;
4. validate p1/p2/p3/p5/p6/p7 sizes;
5. start live kmsg stream to Mac TCP/11000;
6. remove probe-owned devpts/sysfs/proc namespace mounts;
7. `exec /init.android`.

There is no first-stage mount watcher and no `SIGSTOP` in Phase 6.

The supervisor does not keep an extra `/dev/kmsg` file descriptor across `exec`; the handoff marker is written once before Android starts so the original init receives no extra diagnostic fd from the wrapper.

## Deterministic Phase 6 image

Build script:

```text
scripts/v2/build_android_full_boot.sh
```

Builder:

```text
scripts/v2/build_android_full_boot.py
```

The builder consumes the already accepted artifacts:

```text
out/diskless-v2-android/boot-fstab-only.img
out/diskless-v2-transport.img
out/diskless-v2-android/fstab.flox
diskless-v2/phase4-accepted.env
```

and produces:

```text
out/diskless-v2-android/android-full-boot.img
out/diskless-v2-android/android-full-boot-manifest.txt
```

It fails closed unless:

- the kernel SHA matches accepted Phase 4;
- the input boot contains the exact accepted Phase 5 fstab;
- the original Android `/init` is preserved byte-for-byte as `/init.android`;
- the full-boot supervisor contains no first-stage `SIGSTOP` policy;
- SELinux permissive is absent from the resulting cmdline;
- no Android rc bypass is introduced.

## After Phase 6A

Once second-stage entry is proven, the device is allowed to continue running while live kmsg remains captured on the Mac. The next failure is classified before any workaround is added.

Subsequent Phase 6 work proceeds one failure at a time through:

```text
second-stage init
→ early-init/init
→ late-init/post-fs/post-fs-data
→ ADSP/devwait
→ zygote/framework
→ boot trigger
→ launcher
```

The final Phase 6 gate remains the execution-plan target: reach launcher repeatedly, ultimately 10 consecutive cold RAM boots, with no transport loss and no hidden v1 bypasses.
