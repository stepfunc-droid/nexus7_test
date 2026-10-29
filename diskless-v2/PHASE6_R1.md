# Diskless v2 Phase 6R1 — clean full-boot supervisor

Status: **PASSED — host gate accepted; real-device boot still gated on 6R2 host evidence design**.

Phase 6R0 host/source audit passed:

```text
DISKLESS_V2_PHASE6_R0_ARTIFACT_AUDIT=PASS
DISKLESS_V2_PHASE6_R0_HOST_AUDIT=PASS
```

Phase 6R1 host acceptance passed:

```text
DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS
```

## Purpose

6R1 removes the diagnostic contamination introduced by the abandoned first Phase 6 attempt. It does not itself prove Android second-stage behavior. It proves that the next full-boot image is constructed from accepted Phase 4/5 artifacts with a minimal transport supervisor and an exact stock Lineage `/init` handoff.

Target boot path:

```text
kernel rdinit=/diskless-init
        |
        v
/diskless-init                  PID 1, temporary
        |
        +-- configure usb0
        +-- attach exactly one /dev/nbd0 session
        +-- validate p1/p2/p3/p5/p6/p7
        +-- normal umount /sys and /proc
        |
        `-- exec /init          exact stock Lineage path and payload
```

The NBD handler created before SELinux policy load is the only intentional userspace process that survives the handoff besides PID 1. Source audit of the pinned Linux 3.4 SELinux hooks shows that the pre-policy NBD socket carries `SECINITSID_KERNEL`, and `sock_has_perm()` explicitly permits that socket SID. Therefore 6R1 does not add an SELinux exception or permissive mode for the transport.

## Ramdisk transformation

The accepted Phase 5B Android boot ramdisk is preserved entry-for-entry. 6R1 adds only:

```text
/diskless-init
/diskless-busybox
/diskless-v2-layout
```

It does **not** rename, replace, or copy `/init`.

Required `/init` identity remains:

```text
cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
```

`/diskless-busybox` is the exact accepted transport BusyBox payload:

```text
cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

The accepted Phase 4 kernel remains:

```text
eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

## Explicitly forbidden in 6R1

- `/init.android`;
- `/proc/kmsg` or `/dev/kmsg` reader;
- HTTP server;
- shell server;
- TCP progress marker;
- Android rc modification;
- `androidboot.selinux=permissive`;
- SIGSTOP gate;
- diagnostic file descriptors intentionally inherited by Android init;
- probe-owned devpts mount.

The supervisor does not mount system/vendor itself. Android first-stage remains responsible for `/system` and `/vendor`, as already proven in Phase 5D.

## Host gate — PASSED

Gate:

```bash
bash scripts/v2/phase6_r1_host_gate.sh
```

The accepted gate:

1. required the accepted 6R0 report;
2. built the 6R1 image twice;
3. proved the two images byte-identical;
4. independently compared every original Android ramdisk entry metadata and payload against the Phase 5B input;
5. verified the only added entries are the three diskless root files;
6. verified stock `/init`, Phase 5 fstab, accepted kernel, BusyBox and layout identities;
7. verified `rdinit=/diskless-init` exactly once and no SELinux override;
8. verified no Android rc changes, diagnostic network service, logger or shell-owned background job.

Accepted markers:

```text
DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS
```

Output artifact:

```text
out/diskless-v2-android/phase6-r1-full-boot.img
```

Report:

```text
out/diskless-v2-android/phase6-r1-host-audit.txt
```

## Stop condition

6R1 is accepted, but hardware remains paused until 6R2 host tracing itself passes its host-only gate. 6R2 will observe the existing NBD protocol from the Mac side and must not add a Nexus-side logger or Android rc marker.
