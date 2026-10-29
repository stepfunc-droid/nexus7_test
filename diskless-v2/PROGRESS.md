# Diskless v2 — Current checkpoint

This file is intentionally concise. It is **not** the architecture source of truth.

Read, in order:

1. `AGENTS.md`
2. `DISKLESS_V2_EXECUTION.md`
3. this file
4. latest entries in `diskless-v2/WORKLOG.md`
5. active Phase6 evidence documents and failure log

If this file disagrees with `DISKLESS_V2_EXECUTION.md`, hardware work stops until the discrepancy is reconciled.

---

## Governance state

```text
working protocol        ESTABLISHED
batch checkpointing     REQUIRED / APPEND-ONLY WORKLOG
hardware                PAUSED
conversation memory     NOT AUTHORITY
script existence        NOT HARDWARE AUTHORIZATION
```

Every coherent work batch must be closed in `diskless-v2/WORKLOG.md` before the next unrelated batch or hardware experiment begins.

---

## Accepted boundary

```text
Phase 1   deterministic diskless kernel              ACCEPTED / FROZEN
Phase 2   single partitioned NBD disk                ACCEPTED / FROZEN
Phase 3   transport supervisor + stress              ACCEPTED / FROZEN
Phase 4   USB/root-transport protection              ACCEPTED / FROZEN
Phase 5   Android fstab + first-stage handoff        ACCEPTED / FROZEN
Phase 6   full Android integration                   ACTIVE
Phase 7   normal runtime feature restoration         NOT REACHED
```

Accepted kernel:

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

Accepted Phase5 handoff contract:

```text
/init                    diskless supervisor
/init.android            exact original Lineage boot init
/bin/busybox             accepted BusyBox
/etc/diskless-v2-layout  accepted layout
single NBD               172.16.42.2:10810
```

Accepted continuation image:

```text
sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
handoff=exec-/init.android
android_rc_modifications=none
selinux=stock-enforcing-baseline
```

---

## Phase6 gate state

```text
6V2-A frozen facts                         PASS (HOST)
6V2-B continuation semantic/image audit    PASS (HOST)
6V2-C traced NBD differential/audit        PASS (HOST)
6V2-D transport attach                     PASS (REAL DEVICE)
6V2-E p3/p6 second-stage evidence          NOT REACHED
6V2-F late-fs evidence                     NOT REACHED
6V2-G first genuine later blocker          ACTIVE / UNKNOWN
```

---

## Run1 facts

Observed on the accepted continuation run:

```text
NBD connections=1
requests=1755
reads=1755
writes=0
read_bytes=75442176
phase=request-header-recv
last=[READ offset=0x1ce00000 (484442112) length=94208 fua=0]
```

Accepted interpretation:

- substantial p1/system I/O completed;
- the final READ had completed and the server was waiting for another request;
- Nexus-side NBD I/O then stopped;
- the user subsequently observed the device reboot;
- host ETIMEDOUT is not accepted as the cause;
- no accepted p3/cache or p6/persist filesystem evidence was observed;
- the cause/path of the reboot remains `UNKNOWN`.

Do **not** simplify this to “the system automatically rebooted because of X.”

---

## Current blocker

```text
transport attach is proven
        -> substantial system reads complete
        -> Nexus stops issuing NBD requests
        -> user observes subsequent reboot
        -> second-stage p3/p6 evidence not reached
```

Still unknown:

```text
kernel panic/oops        UNKNOWN
kernel hang/deadlock     UNKNOWN
watchdog reset           UNKNOWN
userspace/init reboot    UNKNOWN
other reset path         UNKNOWN
```

The last p1 read overlapping `/system/lib/libkeystore_aidl.so` is forensic context only and must not be used as a caller/root-cause claim.

---

## Runtime facts relevant to the selected experiment

Accepted continuation code requests before Android handoff:

```text
panic_on_oops=1
panic_timeout=5
```

These are `IMPLEMENTED_UNPROVEN` as real-device runtime values because Run1 did not read them back.

Pinned-source semantics are now audited:

```text
ARM die() + panic_on_oops -> panic()
panic_timeout != 0       -> panic eventually calls emergency_restart()
panic_timeout == 0       -> panic does not call emergency_restart()
MSM panic notifier + panic_timeout==0 -> watchdog disabled
```

Evidence class: `SOURCE_PROVEN`.

Pinned APQ8064 watchdog data:

```text
pet_time=10000 ms
bark_time=45000 ms
has_secure=true
```

---

## Selected next binary experiment

Detailed design:

```text
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
```

Question:

> Did the Run1-like observed reboot depend on Linux `panic()` `panic_timeout` auto-restart?

Single intended causal variable:

```text
panic_timeout: 5 -> 0
panic_on_oops: remains 1
```

Everything in Phase1-5, transport, Android init/fstab/rc/system, and SELinux baseline remains frozen.

The existing panic-hold implementation is **not yet acceptable** because it only attempted the sysctl write. F6-017 records that runtime read-back is mandatory.

Revised diagnostic must fail closed before NBD attach unless:

```text
/proc/sys/kernel/panic == 0
/proc/sys/kernel/panic_on_oops == 1
```

Interpretation:

```text
comparable Run1-like boundary + persistent >=90s hold
    -> panic_timeout dependency SUPPORTED

comparable Run1-like boundary + reboot still occurs
    -> panic_timeout auto-restart INSUFFICIENT to explain reset
       (NOT proof of userspace reboot)

no comparable boundary / missing evidence / precondition failure
    -> INCONCLUSIVE
```

---

## Active evidence documents

```text
DISKLESS_V2_EXECUTION.md
diskless-v2/WORKLOG.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
diskless-v2/PHASE6_V2_RUN1_POSTMORTEM.md
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/PHASE6_FAILURE_F6_013.md
diskless-v2/PHASE6_FAILURE_F6_014_TO_F6_016.md
diskless-v2/PHASE6_FAILURE_F6_017.md
```

Historical phase documents may contain stale embedded “current state” sections. They are evidence/history only; they do not override `DISKLESS_V2_EXECUTION.md` + this checkpoint.

---

## Existing diagnostic code status

```text
scripts/v2/phase6_v2_panic_hold_host_gate.sh       NEEDS REVISION
scripts/v2/phase6_v2_panic_hold_real_preflight.sh  NEEDS REVISION/REVIEW
scripts/v2/phase6_v2_crash_capture_preflight.sh    UTILITY ONLY
scripts/v2/phase6_v2_capture_last_kmsg.sh           UTILITY ONLY
```

Run1 `last_kmsg` provenance is uncontrolled after the fact and cannot automatically be treated as Run1 evidence.

---

## Hardware authorization

```text
hardware                PAUSED
experiment design       SELECTED
implementation          NOT YET ACCEPTED
host gate               NOT YET PASSED UNDER NEW DESIGN
real-device boot        NOT AUTHORIZED
```

---

## Next action

```text
1. Close the current evidence-selection batch in WORKLOG.md.
2. Start a new implementation batch from the resulting HEAD.
3. Revise panic-hold diagnostic wrapper/gates for fail-closed runtime read-back.
4. Rebuild/audit deterministically with accepted Phase5 builder + image auditor.
5. Re-run base 6V2 preflight and persist all evidence paths.
6. Update total design / experiment document / PROGRESS / WORKLOG with host result.
7. Only then decide whether one controlled hardware run is authorized.
```
