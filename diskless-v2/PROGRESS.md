# Diskless v2 implementation progress

This file records the current accepted implementation state. Detailed evidence remains in the phase-specific documents.

## Phase 1 — deterministic diskless kernel

Status: **PASSED / FROZEN**.

Accepted kernel identity:

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e22342f01de
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

Status: **AUDIT V2 REAL-DEVICE RUN COMPLETE / CRASH CLASSIFICATION ACTIVE**.

Authoritative documents:

```text
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
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

The replacement continuation is a subtraction-only derivative of the Phase5D real-device PASS:

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
new_executable_lines=0
busybox=/bin/busybox
handoff=exec-/init.android
selinux=stock-enforcing-baseline
```

No `rdinit=/diskless-init` redesign is used.

### 6V2-D controlled real-device run

Status: **PASS for transport attach; run ended in automatic reboot**.

The Nexus successfully executed the Phase5D-derived continuation supervisor, configured USB ECM, established exactly one NBD session, completed the oldstyle handshake and issued real block requests.

Final host-side server summary from the run:

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
- the transport timeout is therefore not accepted as the reboot cause; it may be a consequence of the Nexus reboot and USB peer disappearance;
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
    -> Nexus automatically reboots
    -> p3/p6 second-stage filesystem evidence not observed
```

Root cause is currently **UNKNOWN**.

The active binary question is no longer which system library was read last. It is:

```text
Was the automatic reboot caused by a kernel panic/oops/watchdog,
or by Android/userspace/init requesting a reboot?
```

### Current next action — persistent crash evidence

This returns to the original v2 execution plan: recover previous-boot persistent RAM console evidence after a kernel failure.

Use the already real-device-accepted Phase3 transport image as a separate recovery/capture boot. Its accepted init snapshots `/proc/last_kmsg` into `/www/last_kmsg.txt` before NBD attach and exposes `/www` over USB Ethernet HTTP.

New host-side helpers:

```text
scripts/v2/phase6_v2_crash_capture_preflight.sh
scripts/v2/phase6_v2_capture_last_kmsg.sh
```

The recovery boot does not modify the continuation image or Android rc files and does not require the NBD server.

`/proc/last_kmsg` remains best-effort evidence: if present, classify explicit kernel panic/oops/watchdog evidence; if absent, report UNKNOWN. Absence must never be interpreted as proof of a userspace reboot.

### Hardware state

```text
continuation rerun   PAUSED
new Android changes  NONE
next hardware boot   accepted Phase3 transport recovery image only
purpose              recover Run-1 persistent crash evidence
```

Do not start another continuation run until the Run-1 reboot class has been extracted or the persistent-RAM path is proven unavailable.
