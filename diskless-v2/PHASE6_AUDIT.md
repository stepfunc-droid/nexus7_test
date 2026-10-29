# Diskless v2 Phase 6 audit

Status: **PAUSED — no Phase 6 acceptance gate has passed**.

This document resets Phase 6 after a sequence of diagnostic experiments introduced assumptions that were not validated first. No further real-device Phase 6 boot should be run until the reset gates below are implemented and reviewed.

## 1. Safe reset point

The last accepted implementation state is the Phase 5 completion commit:

```text
2e5a6ba791816bcf746ae53817122f9fb916b2f8
```

GitHub comparison from that commit to the current `diskless-v2` head shows that all later Phase 6 work is isolated to newly added Phase 6 files. Accepted Phase 1–5 kernel, disk, fstab, transport and Phase 5 probe files were not modified by Phase 6 work.

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

## 4. Invalid assumptions discovered

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

The Phase 6 marker experiment first assumed `/init.rc` and then `/init.flox.rc` existed in the boot ramdisk. The actual Phase 6 boot ramdisk contains no Android `.rc` files.

Lineage second stage loads `/system/etc/init/hw/init.rc`; that file imports `/init.${ro.hardware}.rc`. For flo, `init.flox.rc` is installed into `TARGET_ROOT_OUT` and becomes `/init.flox.rc` after first-stage switches root to `/system`.

Conclusion: the boot-ramdisk marker builder is architecturally invalid and retired.

### P6-005 — Phase 6 unnecessarily renamed stock `/init`

The current experimental builder replaces `/init` with the transport wrapper and moves the exact Android binary to `/init.android`.

The pinned kernel explicitly supports `rdinit=`. Phase 6 therefore does not need to rename Android init at all.

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

The experimental Phase 6 supervisor starts BusyBox child processes before Android loads SELinux policy. The HTTP server is purely diagnostic and has no reason to survive into Android.

Phase 6 enforcing baseline should hand off with no pre-policy diagnostic process remaining. Only the process required to keep the NBD session alive may remain.

### P6-007 — NBD client SELinux lifetime is an unresolved architecture question

This is now the highest-priority Phase 6 question.

The old Linux 3.4 NBD driver runs `NBD_DO_IT` in the userspace `nbd-client` task and performs socket I/O through `kernel_sendmsg()` / `kernel_recvmsg()`. Those paths invoke Linux security socket hooks using the current task context.

The NBD client is started before Android loads policy, so it begins in the initial/kernel domain. After SELinux enforcing is enabled, the same long-lived task continues servicing NBD network I/O.

Lineage policy grants normal TCP socket permissions to `netdomain`; the initial/kernel domain is not obviously a `netdomain` and no kernel-domain TCP grant has yet been identified in the audited policy.

This makes SELinux denial of the long-lived NBD transport a plausible structural failure mode, but it is **not yet proven**. Do not call it the root cause until a binary experiment or authoritative policy proof establishes it.

## 5. Documentation/process failures

The Phase 6 document drifted away from the implementation: it continued to describe TCP/11000 live-kmsg even after the wrapper changed. The progress file also did not reflect the experiments.

Rule for the reset: every Phase 6 gate must state its evidence source and that source must be independently validated before a real-device run.

## 6. Phase 6 reset architecture

### 6R0 — host-only artifact and source audit

No device boot.

Required outputs:

- enumerate the actual boot ramdisk contents;
- prove stock `/init` path and bytes will remain unchanged;
- prove `rdinit=/diskless-init` is supported by the pinned kernel;
- record exact accepted kernel/fstab/system/vendor identities;
- map where second-stage rc files actually live after switch-root;
- inventory all processes and open resources that exist at Android handoff;
- audit NBD client SELinux/network requirements.

**Gate:** a written manifest with zero unresolved assumptions about file location, init path, logger mechanism or handoff processes.

### 6R1 — minimal clean full-boot supervisor

Rebuild Phase 6 from accepted Phase 5 artifacts with:

- `/init` untouched, byte-for-byte and path-for-path;
- new `/diskless-init` wrapper selected only by `rdinit=/diskless-init`;
- exactly one NBD session;
- no `/proc/kmsg` reader;
- no `/dev/kmsg` reader;
- no HTTP server surviving handoff;
- no shell server;
- no Android rc modification;
- no SELinux permissive flag in the baseline;
- all temporary proc/sysfs/devpts mounts removed before `exec /init`;
- no extra diagnostic fd inherited by Android init.

**Gate:** deterministic host-side image audit before any device boot.

### 6R2 — prove NBD transport survives SELinux enforcing

This gate comes before interpreting Android second-stage behavior.

Binary question:

> After SELinux policy becomes enforcing, does the original single NBD session continue performing successful block I/O without session replacement or protocol failure?

Evidence must not depend on a Nexus-side logger that is itself affected by SELinux.

Preferred evidence source: Mac-side NBD request trace/activity, plus exact one-session validation. If necessary, add a narrowly scoped diagnostic policy experiment, but do not modify Android rc files merely to obtain progress markers.

**Gate:** same NBD session demonstrably services reads after the enforcing transition.

### 6R3 — observe enforcing second-stage without modifying Android

Preferred design: host-side NBD read tracing.

`nbd_test_server.py` already sees every read request offset/length before returning data. A host-only preflight can locate several unique byte markers in accepted p1 files that second-stage parses, such as `/system/etc/init/hw/init.rc` and device init files. The NBD server can then record when returned READ payloads contain those unique markers.

This must be designed to account for block cache and readahead; one coincidental range overlap is insufficient. Multiple independent markers and ordering should be required.

**Gate:** stock enforcing Android causes host-observed reads proving second-stage configuration parsing, with no Nexus-side diagnostic process or Android image modification.

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

They may be reused only after being brought into the 6R0/6R1 contracts above.

## 8. Current stop condition

Do not run another Phase 6 device boot yet.

Immediate work is host/source audit and redesign only. Phase 6 resumes on hardware only after 6R0 and 6R1 are complete and independently checked.
