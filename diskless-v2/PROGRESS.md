# Diskless v2 — Current checkpoint

This file is intentionally concise. It is **not** the architecture source of truth.

Read, in order:

1. `AGENTS.md`
2. `DISKLESS_V2_EXECUTION.md`
3. this file
4. active Phase6 evidence documents and failure log

If this file disagrees with `DISKLESS_V2_EXECUTION.md`, hardware work stops until the discrepancy is reconciled.

---

## Governance state

```text
working protocol        ESTABLISHED
hardware                PAUSED
reason                  documentation/governance reconciliation after Phase6 Run1
conversation memory     NOT AUTHORITY
script existence        NOT HARDWARE AUTHORIZATION
```

No further real-device Phase6 boot is currently authorized.

The recently added panic-hold scripts are `PROPOSED_DIAGNOSTIC` only and must be re-reviewed under `AGENTS.md` before use.

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

Interpretation accepted so far:

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

Unknowns still include:

```text
kernel panic/oops        UNKNOWN
kernel hang/deadlock     UNKNOWN
watchdog reset           UNKNOWN
userspace/init reboot    UNKNOWN
other reset path         UNKNOWN
```

The last p1 read overlapping `/system/lib/libkeystore_aidl.so` is forensic context only and must not be used as a caller/root-cause claim.

---

## Runtime facts that must not be rediscovered from scratch

The accepted continuation code currently requests before Android handoff:

```text
panic_on_oops=1
panic_timeout=5
```

Evidence class: `IMPLEMENTED_UNPROVEN` as independently read-back runtime state. Pinned source semantics are `SOURCE_PROVEN`; this is not itself proof that Run1 reboot was a panic.

The pinned MSM watchdog source defaults to enabled unless disabled; exact Run1 watchdog runtime state was not measured.

Full runtime contract and evidence classes are maintained in `DISKLESS_V2_EXECUTION.md`.

---

## Active evidence documents

```text
DISKLESS_V2_EXECUTION.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
diskless-v2/PHASE6_V2_RUN1_POSTMORTEM.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/PHASE6_FAILURE_F6_013.md
```

Phase documents are evidence/history. Their embedded old “current state” sections do not override this checkpoint or the total design document.

---

## Existing diagnostic proposals

These files exist but are **not currently authorized for hardware**:

```text
scripts/v2/phase6_v2_crash_capture_preflight.sh
scripts/v2/phase6_v2_capture_last_kmsg.sh
scripts/v2/phase6_v2_panic_hold_host_gate.sh
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
```

Run1 `last_kmsg` provenance is not controlled after the fact, so it cannot automatically be treated as Run1 evidence.

The panic-hold idea must be re-reviewed under the rebuilt work protocol before any boot command is issued.

---

## Next action

```text
1. No hardware boot.
2. Re-read/reconcile Phase6 evidence and failure history under AGENTS.md.
3. Select exactly one reset/failure-classification binary question.
4. Document its single delta, evidence classes, stop/INCONCLUSIVE rules and artifact capture.
5. Only then authorize a real-device run in DISKLESS_V2_EXECUTION.md.
```
