# Diskless v2 implementation progress

This file records the current accepted implementation state. Detailed evidence remains in the phase-specific documents.

## Phase 1 — deterministic diskless kernel

Status: **PASSED / FROZEN**.

Accepted kernel identity:

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

Accepted invariants include built-in NBD, USB ECM gadget, Android gadget disabled, persistent RAM console, diskless USB/suspend guards, and SDCC1/eMMC registration disabled.

## Phase 2 — single partitioned NBD disk

Status: **PASSED / FROZEN**.

Accepted layout:

```text
p1 system    RO
p2 vendor    RO
p3 cache     RW
p4 extended
p5 userdata  RW
p6 persist   RW
p7 metadata  raw/reserved
nbd.max_part=8
```

One raw disk is exported through exactly one NBD TCP session on port 10810.

## Phase 3 — transport supervisor

Status: **PASSED / FROZEN**.

Real-device acceptance included USB ECM, one NBD session, exact partition validation, userdata write/remount checksum, and 10-minute simultaneous RO/RW stress.

Accepted result included:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
```

Important proven runtime convention:

```text
/bin/busybox
#!/bin/busybox sh
/etc/diskless-v2-layout
```

## Phase 4 — protect USB root transport

Status: **PASSED / FROZEN**.

Accepted results include the diskless OTG guard, PM_SUSPEND_PREPARE system-suspend guard, unchanged NBD session during the suspend gate, and another 10-minute transport stress PASS.

## Phase 5 — deterministic Android fstab/image and first-stage handoff

Status: **PASSED / FROZEN**.

Accepted fstab identity:

```text
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
```

Accepted block mapping:

```text
system    /dev/block/nbd0p1
vendor    /dev/block/nbd0p2
cache     /dev/block/nbd0p3
userdata  /dev/block/nbd0p5
persist   /dev/block/nbd0p6
metadata  /dev/block/nbd0p7
```

Accepted clean system identity:

```text
a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
```

Accepted original boot init identity:

```text
cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
```

Phase5D real-device gate proved original Lineage first-stage mounted:

```text
/system <- /dev/block/nbd0p1
/vendor <- /dev/block/nbd0p2
```

while preserving the same single NBD kernel session.

The Phase5D supervisor/packaging contract is now the immutable runtime reference for Phase6 continuation:

```text
/init                    diskless supervisor
/init.android            exact original Lineage boot init
/bin/busybox              exact accepted BusyBox payload
/etc/diskless-v2-layout  exact accepted layout contract
```

Detailed Phase5D evidence is in `PHASE5_FIRST_STAGE.md`.

---

## Phase 6 — full Android integration

Status: **SECOND AUDIT ACTIVE / HARDWARE PAUSED**.

Authoritative documents:

```text
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
```

The first Phase6 implementation was abandoned after invalid Nexus-side log observers and incorrect boot-ramdisk rc assumptions.

The first Phase6 reset/audit is also superseded. Its 6R1 host gate passed, but its first real-device image rebooted before USB reachability or any NBD connection. The reset had changed the real-device-proven BusyBox path/invocation to `/diskless-busybox`, a runtime-critical regression that both builder and auditor incorrectly encoded as a requirement.

Current acceptance state:

```text
Phase 1–5                    ACCEPTED / FROZEN
first Phase6 implementation  ABANDONED
first Phase6 audit           SUPERSEDED
old 6R0 artifact checks      retained only as artifact FACT checks
old 6R1                      REVOKED / real-device FAIL before NBD
old 6R2 host tooling         host self-tests only
old 6R2 real-device result   NOT REACHED
old 6R3                      NOT REACHED; rc-extent proof semantics revoked
Phase6 Audit V2              IN PROGRESS
hardware                     PAUSED
```

### Audit V2 replacement rule

Phase6 must continue from the Phase5D real-device PASS by **subtraction**, not redesign.

The replacement supervisor must retain Phase5D runtime conventions, including `/bin/busybox`, `/etc/diskless-v2-layout`, device setup, NBD launch/retry behavior, partition validation, and `/init -> /init.android` handoff.

The only intended functional continuation change is to remove the Phase5D observer/SIGSTOP machinery so original Android is allowed to continue beyond the already-proven first-stage boundary.

No `rdinit=/diskless-init` redesign is currently accepted or needed.

### Future host evidence direction

The original R2 idea inferred second-stage from physical extents of rc files. That semantic interpretation is revoked because NBD observes block requests rather than the userspace caller.

Audit V2 instead uses source-proven partition-stage isolation:

```text
p1 system   first-stage
p2 vendor   first-stage
p3 cache    second-stage fs / mount_all --early
p6 persist  second-stage fs / mount_all --early
p5 userdata later mount_all --late
```

A future host tracer must distinguish partition-table/EBR traffic from filesystem-internal p3/p5/p6 I/O, and its NBD protocol behavior must be differentially checked against the accepted Phase3/4 server before hardware use.

No additional Phase6 real-device boot is authorized yet.
