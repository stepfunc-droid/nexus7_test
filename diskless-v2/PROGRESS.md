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
/bin/busybox             exact accepted BusyBox payload
/etc/diskless-v2-layout  exact accepted layout contract
```

Detailed Phase5D evidence is in `PHASE5_FIRST_STAGE.md`.

---

## Phase 6 — full Android integration

Status: **AUDIT V2 REAL-DEVICE RUN 1 COMPLETE / RESET-CAUSE CLASSIFICATION ACTIVE**.

Authoritative documents:

```text
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
diskless-v2/PHASE6_V2_RUN1_POSTMORTEM.md
```

The first Phase6 implementation and first reset/audit remain superseded. The old 6R1 changed the proven BusyBox invocation contract and failed before any NBD connection; that path remains revoked.

### Audit V2 host gates

All replacement host gates have passed:

```text
6V2-A frozen facts                    PASS
6V2-B continuation semantic diff      PASS
6V2-B deterministic/image audit       PASS
6V2-C NBD differential protocol       PASS
6V2-C partition evidence classifier   PASS
```

The accepted continuation is a subtraction-only derivative of the Phase5D real-device PASS:

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
new_executable_lines=0
busybox=/bin/busybox
handoff=exec-/init.android
selinux=stock-enforcing-baseline
```

No `rdinit=/diskless-init` redesign is used.

### 6V2-D controlled real-device run 1

Status: **PASS for transport attach; after NBD I/O stopped, the user observed the device reboot**.

The Nexus successfully executed the Phase5D-derived continuation supervisor, configured USB ECM, established exactly one NBD session, completed the oldstyle handshake and issued real block requests.

Final host-side server summary recovered from terminal output:

```text
requests=1755
reads=1755
writes=0
read_bytes=75442176
phase=request-header-recv
last=[READ offset=0x1ce00000 (484442112) length=94208 fua=0]
connection_close=transport-error:TimeoutError(60, 'Operation timed out')
```

Important interpretation:

- the NBD path did not fail immediately; 1755 READs / 75,442,176 bytes were completed;
- `phase=request-header-recv` means the final READ had already been serviced and the host was waiting for the next request;
- macOS errno 60 is ETIMEDOUT, not a configured 60-second application timeout;
- the host timeout occurred after Nexus-side progress stopped and is not accepted as the reset cause;
- the user's observation establishes that a reboot occurred after NBD I/O stopped, but the existing host trace does not establish what triggered that reboot;
- no p3 cache / p6 persist filesystem evidence was observed, so 6V2-E remains NOT REACHED.

Reverse mapping of the final successful p1/system READ:

```text
/system/lib/libkeystore_aidl.so
p1-relative=0x1cd00000:0x1cd17000
file_offset=16384:110592
```

This is a forensic hint only. Physical block overlap does **not** prove that keystore or any specific userspace process caused the reboot; no root-cause claim is made from the ELF mapping.

### Current blocker

The first genuine Phase6 blocker is now:

```text
NBD transport proven alive
    -> substantial p1/system I/O completed
    -> Nexus stops issuing NBD requests
    -> user observes a subsequent device reboot
    -> p3/p6 second-stage filesystem evidence not observed
```

Root cause is currently **UNKNOWN**.

The active classification question is:

```text
Did a kernel panic/oops path cause the observed reboot,
or did a non-panic path (userspace/init, watchdog/reset, or another restart path) cause it?
```

### Source-audit result that changes the next experiment

The accepted continuation wrapper already executes before Android handoff:

```text
kernel.panic_on_oops = 1
kernel.panic         = 5
```

The pinned kernel source at `0da5107137f93b8d8f697e949ab0784f5ace450c` establishes:

1. ARM `die()` calls `panic("Fatal exception")` when `panic_on_oops` is nonzero.
2. `panic()` waits `panic_timeout` seconds and calls `emergency_restart()` when `panic_timeout != 0`.
3. With `panic_timeout == 0`, `panic()` stays in its terminal loop instead of calling `emergency_restart()`.
4. The flo/MSM watchdog panic notifier explicitly disables the watchdog when `panic_timeout == 0`; when nonzero it extends watchdog bark/bite to `panic_timeout + 4` seconds.

Therefore the next highest-information experiment is not to infer a cause from the last system block read and not to rely on stale Run-1 `/proc/last_kmsg` provenance.

### Current next action — single-variable panic-hold A/B

A diagnostic-only image is built from the exact accepted continuation with one runtime change only:

```text
/proc/sys/kernel/panic: 5 -> 0
panic_on_oops:           remains 1
all transport code:      unchanged
Android init/fstab/rc:   unchanged
kernel:                  unchanged
SELinux baseline:        unchanged
```

Host gate:

```text
scripts/v2/phase6_v2_panic_hold_host_gate.sh
```

It does not replace or modify the accepted continuation wrapper/image. It creates a temporary wrapper, proves the one-line delta, builds twice for reproducibility, and reuses the independent continuation image auditor.

Binary interpretation for the next controlled real-device run:

```text
same failure boundary + device no longer reboots and remains halted
    -> strong evidence that Run-1 reboot followed the kernel panic path
       (this does not yet identify the panic stack/root cause)

same failure boundary + device still reboots
    -> panic_timeout auto-restart is insufficient to explain the reset;
       move to non-panic reset/userspace/watchdog/restart classification

failure boundary materially changes or run is not reproducible
    -> INCONCLUSIVE; do not infer reset cause
```

If the panic path is supported, the following run should restore a finite panic timeout and immediately recover same-run persistent RAM evidence to obtain the panic stack.

### Hardware state

```text
accepted continuation      unchanged / frozen
new Android changes        NONE
next host action           run phase6_v2_panic_hold_host_gate.sh
next hardware experiment   diagnostic panic-hold image only, after host PASS
purpose                    classify kernel-panic auto-restart vs non-panic reset
```

Do not change NBD, USB, fstab, Android rc, SELinux policy, or the accepted continuation architecture before this binary experiment is resolved.
