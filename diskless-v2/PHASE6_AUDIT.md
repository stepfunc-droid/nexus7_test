# Diskless v2 Phase 6 audit

Status: **PAUSED — no Phase 6 acceptance gate has passed**.

This document resets Phase 6 after a sequence of diagnostic experiments introduced assumptions that were not validated first. No further real-device Phase 6 boot should be run until the reset gates below are implemented and reviewed.

## 1. Safe reset point

The last accepted implementation state is the Phase 5 completion commit:

```text
2e5a6ba791816bcf746ae53817122f9fb916b2f8
```

GitHub comparison from that commit to the Phase 6 audit start showed that all later Phase 6 work was isolated to newly added Phase 6 files. Accepted Phase 1–5 kernel, disk, fstab, transport and Phase 5 probe files were not modified by the abandoned Phase 6 work.

Therefore Phase 1–5 remain accepted. Phase 6 can be rewritten without revalidating earlier phases.

## 2. Accepted inputs inherited from Phase 1–5

These are not under review in Phase 6:

```text
kernel zImage sha256:
eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05

generated fstab sha256:
834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf

clean system p1 sha256:
a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880

original Lineage init sha256:
cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44

accepted transport BusyBox sha256:
cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

Accepted Android block mapping:

```text
system    /dev/block/nbd0p1
vendor    /dev/block/nbd0p2
cache     /dev/block/nbd0p3
userdata  /dev/block/nbd0p5
persist   /dev/block/nbd0p6
metadata  /dev/block/nbd0p7
```

Accepted Phase 5D real-device result proved that original Lineage first-stage init mounted `/system` and `/vendor` from the same single NBD session and reached the intentional first-stage stop boundary.

## 3. Phase 6 empirical evidence that remains valid

### 3.1 Diagnostic permissive boot reached second stage

A boot with explicit:

```text
androidboot.selinux=permissive
```

produced real Android logs containing:

```text
init: init second stage started!
```

and continued through Android triggers including `early-init`, `init`, `late-init`, `early-fs`, `fs`, later `zygote-start`, and the flo Qualcomm `devwait` path. Services including logd, servicemanager, hwservicemanager and vold were observed starting.

This proves that the accepted NBD-backed system/vendor artifacts are capable of progressing beyond first-stage under a diagnostic permissive policy.

It does **not** prove that SELinux enforcing itself is the blocker.

### 3.2 Enforcing state is currently unknown beyond first-stage

An enforcing run showed first-stage system/vendor mounts, switch-root and SELinux initialization before the live logger stopped. Subsequent audit proved the logger itself could lose visibility at the SELinux transition. Therefore the absence of later log lines is not evidence that PID 1 stopped there.

No enforcing Phase 6 second-stage gate has passed or failed conclusively.

## 4. Invalid assumptions and resolved architecture questions

### P6-001 — `/proc/kmsg` live logger is not enforcing-safe

A BusyBox process started before SELinux policy load read `/proc/kmsg` and received an AVC denial under permissive mode. Under enforcing mode the same diagnostic reader can become blind while Android continues.

Conclusion: `/proc/kmsg` cannot be the Phase 6 progress gate.

### P6-002 — modern readable `/dev/kmsg` semantics do not exist on this kernel

The pinned Linux 3.4 flo kernel documents major 1 minor 11 `/dev/kmsg` as a write-to-printk device. Its `kmsg_fops` exposes write, not the modern readable per-reader cursor interface.

Conclusion: the `/dev/kmsg` Phase 6 observer and its host gate were invalid. They are retired.

### P6-003 — `/proc/last_kmsg` is best-effort, not a hard gate

A later RAM boot can overwrite or make the previous persistent console unavailable. A transport recovery boot returned HTTP 404 for `last_kmsg.txt` after one Phase 6 run.

Conclusion: persistent console remains useful when available, but Phase 6 acceptance cannot depend on it always surviving the next RAM boot.

### P6-004 — Android rc files were searched in the wrong filesystem layer

The Phase 6 marker experiment first assumed `/init.rc` and then `/init.flox.rc` existed in the boot ramdisk. The actual accepted Phase 5 boot ramdisk contains no Android `.rc` files.

Lineage second stage loads `/system/etc/init/hw/init.rc`; that file imports `/init.${ro.hardware}.rc`. For flo, `init.flox.rc` is installed into `TARGET_ROOT_OUT` and becomes `/init.flox.rc` after first-stage switches root to `/system`.

Conclusion: the boot-ramdisk marker builder is architecturally invalid and retired.

### P6-005 — Phase 6 unnecessarily renamed stock `/init`

The abandoned builder replaced `/init` with the transport wrapper and moved the exact Android binary to `/init.android`.

The pinned Linux 3.4 kernel explicitly implements `rdinit=`. Phase 6 therefore does not need to rename Android init at all.

Correct target architecture:

```text
kernel cmdline: rdinit=/diskless-init
        |
        v
/diskless-init          # transport supervisor, PID 1 initially
        |
        `-- exec /init  # exact stock Lineage path and bytes
```

This reduces the handoff surface and preserves Android's expected path exactly.

### P6-006 — pre-policy diagnostic child processes contaminate the enforcing experiment

The abandoned Phase 6 supervisor started BusyBox child processes before Android loaded SELinux policy. The HTTP server and kernel-log readers were purely diagnostic and had no reason to survive into Android.

Phase 6 enforcing baseline must hand off with no pre-policy diagnostic process remaining. Only the process required to keep the NBD session alive may remain.

### P6-007 — pre-policy NBD socket is **not** blocked by SELinux enforcing — RESOLVED BY SOURCE AUDIT

This was initially the highest-priority architecture concern, but the pinned kernel source resolves it.

Facts from the pinned Linux 3.4 SELinux implementation:

1. The initial task security SID is explicitly initialized as `SECINITSID_KERNEL`.
2. A socket created before policy load inherits the creating task SID; therefore the NBD TCP socket is created with the kernel initial SID.
3. The socket permission helper contains an explicit early return:

```c
if (sksec->sid == SECINITSID_KERNEL)
    return 0;
```

4. `selinux_socket_sendmsg()` and `selinux_socket_recvmsg()` call that helper.
5. Linux 3.4 NBD performs its TCP send/receive through `kernel_sendmsg()` / `kernel_recvmsg()` while the userspace NBD handler remains blocked in `NBD_DO_IT`.

Therefore loading/enabling Android SELinux policy does not by itself revoke socket send/receive permission from the already-created NBD transport socket. The socket's initial kernel SID is explicitly exempted by this kernel's SELinux socket permission path.

Conclusion: **do not treat SELinux denial of the NBD TCP socket as the Phase 6 root cause.** 6R2 still verifies post-transition transport empirically, but now as a runtime integrity gate rather than an unresolved policy-architecture question.

### P6-008 — BusyBox build provenance is not pinned; Phase 6 must reuse the accepted binary exactly

The Phase 3 transport builder discovers an externally supplied static ARM BusyBox rather than rebuilding it from a repository-pinned source commit. Phase 5D nevertheless recorded the exact BusyBox payload used by the accepted transport artifact:

```text
cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

Phase 6 must therefore extract and reuse those exact bytes from the accepted Phase 4 transport boot image. It must not call `find_busybox()` or silently substitute another local BusyBox.

A later reproducibility cleanup may pin BusyBox source/build inputs globally, but that is outside the Phase 6 reset and must not invalidate the accepted Phase 4 transport baseline.

## 5. Documentation/process failures

The old Phase 6 document drifted away from the implementation: it continued to describe TCP/11000 live-kmsg after the wrapper changed. The progress file also did not reflect the experiments.

Rule for the reset: every Phase 6 gate must state its evidence source and that source must be independently validated before a real-device run.

## 6. Phase 6 reset architecture

### 6R0 — host-only artifact and source audit

No device boot.

Required outputs:

- enumerate the actual accepted boot ramdisk contents;
- prove stock `/init` path and bytes will remain unchanged;
- prove `rdinit=/diskless-init` is supported by the pinned kernel;
- record exact accepted kernel/fstab/system/Lineage-init/BusyBox identities;
- verify the Android-test disk still embeds the exact accepted system and fstab-only vendor payloads;
- map where second-stage rc files actually live after switch-root;
- inventory all processes and open resources allowed to exist at Android handoff;
- close the NBD client SELinux/network question from pinned kernel source.

**Gate:** a written host manifest with zero unresolved assumptions about file location, init path, logger mechanism, NBD socket SELinux semantics or handoff processes.

### 6R1 — minimal clean full-boot supervisor

Rebuild Phase 6 from accepted Phase 5 artifacts with:

- `/init` untouched, byte-for-byte and path-for-path;
- new `/diskless-init` wrapper selected only by `rdinit=/diskless-init`;
- exact accepted BusyBox bytes extracted from the Phase 4 transport artifact;
- exactly one NBD session;
- no `/proc/kmsg` reader;
- no `/dev/kmsg` reader;
- no HTTP server;
- no shell server;
- no Android rc modification;
- no SELinux permissive flag in the baseline;
- no devpts mount unless proven necessary;
- all temporary proc/sysfs mounts removed normally before `exec /init`;
- no extra diagnostic fd inherited by Android init;
- exactly one long-lived pre-policy child at handoff: the accepted BusyBox `nbd-client` handler required by Linux 3.4 NBD.

**Gate:** deterministic host-side image audit before any device boot.

### 6R2 — prove NBD transport remains live across enforcing transition

This gate comes before interpreting Android second-stage behavior.

Binary question:

> Does the same single NBD session continue servicing successful block I/O during the enforcing Android transition, without session replacement or protocol failure?

The pinned SELinux source already shows that the pre-policy kernel-SID NBD socket is not denied by the enforcing socket permission path. The real-device gate is therefore an integrity confirmation, not a policy-discovery experiment.

Evidence must not depend on a Nexus-side logger that is itself affected by SELinux.

Preferred evidence source: Mac-side NBD request trace/activity plus exact one-session validation.

**Gate:** one unchanged NBD connection demonstrably services requests after the point where stock Android must load/execute system content beyond first-stage.

### 6R3 — observe enforcing second-stage without modifying Android

Preferred design: host-side NBD read tracing.

`nbd_test_server.py` already sees every read request offset/length before returning data. A host-only trace mode can scan returned READ payloads for multiple independently chosen byte markers from second-stage configuration files. Candidate files include `/system/etc/init/hw/init.rc` and flo device init content that becomes `/init.flox.rc` after switch-root.

This must account for block cache and readahead. One coincidental range overlap is insufficient; multiple independent markers from separate configuration content and a documented ordering/interpretation are required.

**Gate:** stock enforcing Android causes host-observed reads strongly proving second-stage configuration parsing, with no Nexus-side diagnostic process or Android image modification.

### 6R4 — continue stock boot to first genuine blocker

Only after 6R2 and 6R3 pass:

- continue stock enforcing userspace;
- classify the first genuine blocker;
- one experiment per binary question;
- no v1 devwait/ADSP/installd bypass unless explicitly labelled diagnostic and justified by captured evidence.

## 7. Files from the abandoned Phase 6 attempt

The following are experimental and must not be treated as accepted Phase 6 architecture:

```text
diskless-v2/PHASE6_ANDROID_BOOT.md
initramfs/diskless-v2-android-full-init
scripts/v2/build_android_full_boot.py
scripts/v2/build_android_full_boot.sh
scripts/v2/build_android_full_boot_permissive.sh
scripts/v2/build_phase6_second_stage_marker.py
scripts/v2/phase6_second_stage_gate.sh
scripts/v2/phase6_second_stage_marker_gate.py
scripts/v2/phase6_second_stage_permissive_gate.sh
```

The public build/gate entry points are intentionally fail-closed while the reset is in progress.

## 8. Current stop condition

Do not run another Phase 6 device boot yet.

Immediate work is 6R0 host/source audit followed by 6R1 clean image construction and independent host verification. Hardware resumes only after both gates pass.
