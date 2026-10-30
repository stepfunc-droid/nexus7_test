# Diskless v2 Phase 6 — Audit V2

Status: **HOST GATES PASS / P2 AUTO RETURN TO eMMC / PREVIOUS NBD CONSOLE CAPTURED / HARDWARE PAUSED**.

Current authority: `DISKLESS_V2_EXECUTION.md` and `PROGRESS.md`. The design below contains historical gate requirements. F6-018 was repaired and complete host validation rerun successfully in batch 2026-10-30-C (`HOST_FACT`; evidence under `audits/2026-10-30-f6018-host/`). Run1 cause remains UNKNOWN. No historical authorization statement here authorizes a new run.

This audit supersedes the first Phase 6 reset architecture. The first reset successfully revalidated many artifact identities, but it also introduced a new unproved runtime design (`rdinit=/diskless-init`, renamed BusyBox path, changed NBD launch style). The first real-device boot of that design failed before any NBD connection.

The governing rule for Audit V2 is:

> Phase 6 is a continuation of the last real-device PASS, not an opportunity to redesign already-working transport code.

Every runtime-critical behavior must be classified as one of:

- **FACT** — already proved on this real device;
- **SOURCE_PROVEN** — proved from the exact pinned source used by the project;
- **NEW_DELTA** — required change not yet accepted on hardware.

A host builder/auditor agreement cannot turn a `NEW_DELTA` into a fact.

## 1. Frozen acceptance boundary

### FACT — Phase 1–5 remain accepted

No Phase 6 commit modified the accepted Phase 1–5 implementation files. The safe real-device boundary remains Phase 5D.

Accepted identities include:

```text
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
android_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
busybox_sha256=cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

### FACT — Phase 5D real-device runtime contract

The following conventions are not to be changed unless a new failure proves they must change:

```text
/bin/busybox
#!/bin/busybox sh
BB=/bin/busybox
PATH=/bin:/sbin
/etc/diskless-v2-layout
usb0=172.16.42.1/24
single NBD export on 172.16.42.2:10810
/dev/nbd0 + nbd0p1..p15 temporary nodes
kernel /sys/block/nbd0/pid as NBD liveness authority
Phase5 start_nbd()/retry behavior
partition size validation for p1/p2/p3/p5/p6/p7
/dev/pts removed before Android handoff
probe-owned /sys and /proc detached before Android handoff
```

Phase 5D proved on hardware that the same NBD session survived handoff and original Lineage first-stage mounted:

```text
/system <- /dev/block/nbd0p1
/vendor <- /dev/block/nbd0p2
```

## 2. Audit of the first reset

### 2.1 Artifact portion of 6R0 — retained as factual revalidation

The first 6R0 gate correctly revalidated accepted boot/vendor/system/disk/kernel/fstab/BusyBox bytes. Those identity checks remain useful.

### 2.2 Runtime-design lines in 6R0 — revoked

The old report also emitted proposed architecture as though it were part of the PASS, for example:

```text
target_handoff=/diskless-init->exec-/init
handoff_process_contract=pid1-diskless-init-plus-one-nbd-handler-only
rdinit_target=/diskless-init
```

These were design requirements, not artifact facts. They are revoked as acceptance claims.

### 2.3 6R1 — fully revoked

The old 6R1 host PASS is invalidated by its first hardware run.

The design changed real-device-proven:

```text
/bin/busybox
#!/bin/busybox sh
```

to:

```text
/diskless-busybox
#!/diskless-busybox sh
```

BusyBox source confirms applet dispatch depends on invocation basename. `diskless-busybox` does not preserve the `busybox` multicall invocation contract. The observed boot rebooted before USB reachability/NBD connection; the Mac trace contained zero `connection_open` events.

The old image `out/diskless-v2-android/phase6-r1-full-boot.img` is **REJECTED** and must not be booted again.

### 2.4 `rdinit=/diskless-init` — source-supported but unnecessary

The pinned Linux 3.4 kernel supports `rdinit=` and script execution. That makes the mechanism possible, but not necessary.

Phase 5D already proved this chain:

```text
/init                    Phase5 supervisor
  -> exec /init.android  exact original boot-ramdisk Lineage init
  -> FirstStageMain()
  -> DoFirstStageMount()
  -> /system + /vendor
  -> exec /system/bin/init selinux_setup
```

Pinned Lineage `FirstStageMain()` explicitly executes `/system/bin/init selinux_setup` after first-stage mount. Therefore the boot-ramdisk executable name `/init.android` does not propagate into SELinux setup or second stage.

Conclusion: replacing this real-device-proven chain solely to preserve the cosmetic `/init` path violates the minimal-delta rule. Audit V2 does not use the rdinit redesign.

## 3. Replacement 6R1 design — subtract from Phase 5D

Replacement 6R1 is not a new supervisor implementation. It is the accepted Phase 5D supervisor with diagnostic-only behavior removed.

### 3.1 Behaviors that MUST remain byte/semantic-equivalent to Phase 5D

- `#!/bin/busybox sh`;
- `BB=/bin/busybox`;
- exact accepted BusyBox payload under `/bin/busybox`;
- `/etc/diskless-v2-layout`;
- Phase5 device-node preparation;
- Phase5 `usb0` wait/configuration;
- Phase5 `start_nbd()` invocation and retry logic;
- kernel NBD pid/capacity liveness test;
- partition rescan behavior;
- p1/p2/p3/p5/p6/p7 partition validation;
- `/dev/pts` unmount before handoff;
- Phase5 handoff namespace behavior unless a demonstrated issue requires changing it;
- original boot init preserved as `/init.android` exactly as in Phase5D.

### 3.2 Diagnostic-only behavior to remove

These are removed because they are not required for root transport and can contaminate later enforcing behavior:

- HTTP server;
- shell server;
- `/proc/kmsg` reader;
- `/dev/kmsg` diagnostic writer FD used by the observer;
- TCP 11000/11001 progress marker;
- `/proc/last_kmsg` dependency (the exact accepted continuation retains an optional best-effort copy; no acceptance gate depends on it);
- pinned fd 6 `/sys/block/nbd0/pid` post-handoff observer;
- SIGSTOP first-stage gate.

No Android rc file is modified.

### 3.3 The only functional continuation delta

Phase5D intentionally stopped PID 1 after proving `/system` and `/vendor` mounts.

Replacement 6R1 simply does not stop it. After the same proven handoff, Android is allowed to continue naturally into:

```text
/system/bin/init selinux_setup
```

This is the smallest possible Phase 6 continuation.

## 4. Replacement 6R1 host gate requirements

The old idea of “builder and auditor independently agree” is insufficient. The new gate must include a semantic diff against the accepted Phase5D wrapper.

Every executable-code difference must be classified:

```text
UNCHANGED_FROM_PHASE5D
REMOVED_DIAGNOSTIC
REQUIRED_CONTINUATION_DELTA
```

Any other changed executable line is a hard failure:

```text
UNJUSTIFIED_RUNTIME_DELTA
```

Required checks include:

- exact `/bin/busybox` path and accepted SHA;
- exact `#!/bin/busybox sh` shebang;
- exact `/etc/diskless-v2-layout` path;
- no `/diskless-busybox`;
- no `rdinit=/diskless-init` redesign;
- no changed NBD launcher/retry semantics;
- no changed device-node set without explicit necessity;
- no Android rc modification;
- stock `/init.android` payload SHA equals accepted original init SHA;
- no kmsg/HTTP/nc observer surviving handoff;
- no intentional SIGSTOP.

No hardware run is authorized until this semantic-diff gate exists and passes.

## 5. Re-audit of R2/R3 host evidence

### 5.1 What remains valid

The host trace tooling demonstrated useful independent properties:

- oldstyle NBD handshake implementation works in localhost self-test;
- returned READ payload bytes match the backing disk;
- ext4 path/inode/extent mapping reconstructs the expected files;
- assembled-disk offset mapping is byte-verified;
- JSONL connection/request logging works.

These are tool facts only. They do not prove Android stage semantics.

### 5.2 Old rc-extent second-stage proof — revoked

A Mac NBD server sees physical block READs, not the userspace caller. Full physical extent coverage for `init.rc` or `init.flox.rc` can be influenced by page cache/readahead and is therefore not accepted as a hard statement that init parsed that file.

The old gate output:

```text
DISKLESS_V2_PHASE6_R3_ENFORCING_SECOND_STAGE=PASS
```

is retired in its current form.

## 6. Stronger host-side stage boundary: partition isolation

Audit V2 identifies a better causal boundary already present in the accepted design.

### SOURCE_PROVEN — first stage only receives `first_stage_mount` entries

Lineage `ReadFirstStageFstab()` removes every default-fstab entry that does not have `first_stage_mount`.

The accepted flo fstab has:

```text
p1 system   first_stage_mount
p2 vendor   first_stage_mount
p3 cache    NOT first_stage_mount, NOT latemount
p5 userdata NOT first_stage_mount, latemount
p6 persist  NOT first_stage_mount, NOT latemount
```

Therefore Android first-stage does not mount cache, userdata, or persist.

### SOURCE_PROVEN — second-stage `fs` trigger mounts non-late filesystems

Pinned flo `init.flox.rc` contains:

```text
on fs
    mount_all ./fstab.flox --early
    restorecon_recursive /persist

on late-fs
    ...
    mount_all ./fstab.flox --late
```

`fs_mgr_mount_all()` excludes `latemount` entries in `MOUNT_MODE_EARLY` and excludes non-late entries in `MOUNT_MODE_LATE`.

Therefore:

```text
second-stage fs / --early  -> p3 cache + p6 persist
second-stage late-fs       -> p5 userdata
```

### SOURCE_PROVEN — these triggers occur after SELinux transition

`SetupSelinux()` loads policy, enables enforcing (stock baseline), then execs `/system/bin/init second_stage`.

`SecondStageMain()` then loads boot scripts and queues `early-init`, `init`, and `late-init`; the root `init.rc` late-init chain triggers `fs`, `post-fs`, `late-fs`, and `post-fs-data`.

### Consequence for future host evidence

A replacement supervisor must itself never read inside p3/p5/p6 filesystem contents. It may validate partition table geometry, but content I/O inside these partitions is reserved to Android later stages.

With that invariant audited, successful same-connection filesystem I/O inside:

```text
p3 cache or p6 persist
```

is a stronger host-side proof that stock enforcing Android passed first-stage/SELinux setup and entered second-stage `fs` processing.

The earlier claim that p5 userdata I/O provides a `late-fs` marker is `REVOKED` (F6-013). Root init starts vold in `early-fs`, so p5 I/O is observational only and must report `late_fs_claim=NOT_PROVEN`.

The future tracer should therefore classify partition-internal I/O rather than infer userspace file parsing from p1/p2 extents.

## 7. Audit V2 gate sequence

```text
6V2-A  frozen-fact audit
       Re-run only Phase1–5 artifact identities and record them as FACT.

6V2-B  Phase5D semantic-diff gate
       Build continuation image by subtracting diagnostics from Phase5D.
       Reject every unjustified executable-code change.

6V2-C  host tracer semantic gate
       Prove tracer distinguishes partition-table/EBR traffic from
       filesystem-internal p3/p5/p6 traffic.

6V2-D  first real-device continuation
       Use the Phase5-derived image and host-only trace.
       First acceptance question: does the proven NBD transport attach at all?

6V2-E  enforcing second-stage evidence
       Require the same NBD connection plus filesystem-internal p3/p6 I/O.

6V2-F  late-fs evidence: NOT PROVEN by p5 I/O.
       Userdata activity is observational only; a hard late-fs gate is not established.

6V2-G  classify the first genuine later Android blocker.
```

No step may be skipped because a later diagnostic looks promising.

## 8. Current state

```text
Phase 1–5                    ACCEPTED / FROZEN
first Phase6 implementation  ABANDONED
first Phase6 audit           SUPERSEDED
old 6R0 artifact checks      PARTIALLY RETAINED AS FACT CHECKS ONLY
old 6R1                      REVOKED / REAL-DEVICE FAIL
old 6R2 host tooling         SELFTESTED TOOLING ONLY
old 6R2 real-device result   NOT REACHED
old 6R3                      NOT REACHED / proof semantics revoked
Audit V2                     IN PROGRESS
6V2-A/B/C                    HISTORICAL HOST PASS
6V2-D                        REAL_DEVICE_FACT / transport attach PASS
6V2-E                        NOT REACHED
Run1 failure/reset cause     UNKNOWN
current full host preflight  PASS / HOST_FACT / F6-018 VERIFIED
P2                           later auto return to eMMC; initial hold support REVOKED
screen                       user observed Lineage boot animation
hardware                     PAUSED / P2 authorization consumed
```

See `PHASE6_FAILURE_LOG.md` for the append-only record of mistakes and regression-prevention rules.
