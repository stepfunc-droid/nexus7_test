# Diskless v2 — Current checkpoint

This file is concise and is **not** the architecture source of truth.

Read in order:

1. `AGENTS.md`
2. `DISKLESS_V2_EXECUTION.md`
3. this file
4. latest `diskless-v2/WORKLOG.md` entries
5. active Phase6 evidence/failure documents

If this file disagrees with the total design, hardware work stops until reconciled.

---

## Governance

```text
working protocol        ESTABLISHED
batch checkpointing     REQUIRED
conversation memory     NOT AUTHORITY
script existence        NOT HARDWARE AUTHORIZATION
hardware                GENERAL PAUSE / CONDITIONAL SINGLE P2 EXCEPTION
```

---

## Accepted boundary

```text
Phase1 deterministic kernel             ACCEPTED / FROZEN
Phase2 partitioned NBD disk             ACCEPTED / FROZEN
Phase3 transport supervisor/stress      ACCEPTED / FROZEN
Phase4 USB transport protection         ACCEPTED / FROZEN
Phase5 Android fstab/first-stage        ACCEPTED / FROZEN
Phase6 full Android integration         ACTIVE
Phase7 runtime restoration              NOT REACHED
```

Accepted kernel:

```text
commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

Accepted continuation:

```text
image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
/init -> supervisor
/init.android -> exact Lineage init
/bin/busybox -> accepted BusyBox
single NBD -> 172.16.42.2:10810
SELinux -> stock enforcing baseline
Android rc modifications -> none
```

---

## Audit-V2 state

```text
6V2-A frozen facts                     PASS (HOST)
6V2-B continuation audit               PASS (HOST)
6V2-C NBD tracer audit                 PASS (HOST)
6V2-D transport attach                 PASS (REAL DEVICE)
6V2-E p3/p6 second-stage evidence      NOT REACHED
6V2-F late-fs evidence                 NOT REACHED
6V2-G later blocker                    ACTIVE / UNKNOWN
```

---

## Run1 accepted facts

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

- substantial p1/system reads completed;
- final READ had completed and server was waiting for another request;
- Nexus-side NBD requests then stopped;
- user subsequently observed device reboot;
- host ETIMEDOUT is not accepted as cause;
- no accepted p3/p6 evidence appeared;
- reset/failure cause remains `UNKNOWN`.

Still unknown:

```text
kernel panic/oops        UNKNOWN
kernel hang/deadlock     UNKNOWN
watchdog reset           UNKNOWN
userspace/init reboot    UNKNOWN
other reset path         UNKNOWN
```

The final p1 overlap with `libkeystore_aidl.so` is forensic context only.

---

## Selected next binary question

Detailed design:

```text
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
```

Question:

> Did a Run1-like reboot depend on Linux `panic()` `panic_timeout` auto-restart?

Single intended causal variable:

```text
panic_timeout: 5 -> 0
panic_on_oops: remains 1
```

This does not yet ask the broader “kernel vs userspace” question.

Pinned source proves:

```text
panic_timeout != 0 -> panic eventually emergency_restart()
panic_timeout == 0 -> no emergency_restart()
MSM panic notifier + timeout 0 -> watchdog disabled
```

---

## Prepared host implementation

Host-validated tools (2026-10-30-C, designated remote Mac):

```text
scripts/v2/audit_phase6_v2_panic_hold_wrapper.py
scripts/v2/audit_phase6_v2_panic_runtime_writers.py
scripts/v2/phase6_v2_panic_hold_host_gate.sh
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
scripts/v2/selftest_phase6_v2_panic_preflight.py
```

The diagnostic wrapper fails closed before usb0/NBD unless same-run read-back proves:

```text
/proc/sys/kernel/panic == 0
/proc/sys/kernel/panic_on_oops == 1
```

The writer audit binds to accepted system/vendor image identities and rejects canonical direct panic-timeout writer literals. It explicitly cannot prove absence of a nonliteral/programmatic sysctl writer.

F6-017 permanently records why a write command alone is insufficient.

2026-10-30 takeover (`HOST_FACT`): existing untracked panic-hold PASS report/image found. The wrapper and both local boot images passed independent existing audits; diagnostic image SHA256 is `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`. This does not validate the old report's complete provenance, rerun the image-writer scan, or prove reproducibility. See `audits/2026-10-30-takeover.txt`.

F6-018 is repaired and verified: the panic-hold preflight actually executes frozen-fact validation first and binds fact/diagnostic report paths and disk/manifest inputs. Isolated ordering/failure tests and a real-validator missing-input test both reject a stale PASS report.

New `HOST_FACT`: complete A/B/C host gates, accepted-image writer scan, diagnostic reproducible builds/audits and full repaired preflight passed with exit 0. Both image hashes match the earlier records. New logs/reports are committed under `audits/2026-10-30-f6018-host/`; the imported report is no longer the basis for host acceptance. Device diagnostic execution and Run1 cause remain UNKNOWN.

---

## Outcome discipline for a future authorized run

```text
Run1-comparable boundary + >=90s persistent hold
    -> panic_timeout_dependency=SUPPORTED

Run1-comparable boundary + reboot still occurs
    -> panic_timeout auto-restart INSUFFICIENT to explain reset
       NOT proof of userspace reboot

precondition fail / no NBD / non-comparable boundary / incomplete evidence
    -> INCONCLUSIVE
```

---

## Current authorization

```text
experiment design             SELECTED
host implementation           VALIDATED / HOST_FACT
runtime read-back gate        HOST-AUDITED / DEVICE EXECUTION UNKNOWN
accepted-image writer scan    PASS / HOST_FACT / documented scope limit
host preflight                PASS / HOST_FACT / F6-018 VERIFIED
real-device run               P2 ONLY / COMMITTED PLAN + FRESH PREFLIGHT REQUIRED
hardware                      GENERAL PAUSE / SINGLE P2 EXCEPTION
```

Run P1 is conditionally authorized by the total design and `PHASE6_V2_PANIC_HOLD_RUN_P1.md`, after preparation D is committed and fresh preflight/identity checks pass. Scope: one existing lk2nd RAM bootstrap plus one exact panic-hold diagnostic RAM boot, with no flash/erase/retry/recovery boot. The user is available to observe the screen. Return to hardware pause after the attempt.

**Current override:** P1 closed before diagnostic boot. The bootstrap succeeded; actual identity is same serial/port, USB PID `0xd00d`, `product: lk2nd-msm8960`, empty `version-bootloader` (`REAL_DEVICE_FACT`). The host helper's version-field assumption prevented diagnostic launch (F6-022). No NBD export/connection occurred. Authorization above is historical/consumed; hardware is paused pending a separate attempt from current verified lk2nd. Evidence: `audits/2026-10-30-P1-preboot/`.

P2 is now conditionally authorized by the total design and `PHASE6_V2_PANIC_HOLD_RUN_P2.md`: exactly one diagnostic RAM boot from the current reverified lk2nd, no additional bootstrap. Require fresh preflight/exact identities and the same USB-only export/observation criteria; empty version is allowed, actual product/serial/port/VID/PID are required. General pause resumes after this attempt.

Batch-D `HOST_FACT`: external completed-reply snapshots preserve the original pinned server/protocol; differential tests and idle-connection snapshots pass. USB dry-run succeeds; dedicated USB service is manual `172.16.42.2/24`, router `0.0.0.0`. Frozen full disk SHA is `c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9`. No P1 device result exists yet.

P1 pre-boot revision (F6-021): automatic review rejected a wildcard RW NBD listener before execution. Revised plan permits only `172.16.42.2:10810`; USB observation starts before boot, and export/statistics start after the dedicated host endpoint appears. Fresh preflight/full-disk verification passed; no export or device boot had occurred at revision time.

## Execution hosts

Coordinator edits locally; run Mac builds/full host validation/device operations through `ssh zhangjw@192.168.1.63` in `/Users/zhangjw/nexus7_test`. Use SCP for independent transfers and verify identities. Current `/Volumes/zhangjw/` is the remote user directory's SMB mount. Current remote inputs passed the complete frozen-fact gate in batch C. Tell the user if Debian compilation is needed; batch C required no Debian build.

Read-only device response: serial `07a117ae`, product `flo`, bootloader `FLO-04.08`, fastboot (`REAL_DEVICE_FACT` at inspection time). Only the conditional P1 exception above changes the general experiment pause. Details: `REMOTE_WORKFLOW.md` and P1 plan.

F6-019: use SSH for Git inspection/staging/commits as well. Coordinator Git through SMB reported index errors after a remote commit; remote Git remains healthy. Do not reset the shared index from the coordinator.

---

## Active evidence

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
diskless-v2/audits/2026-10-30-takeover.txt
diskless-v2/REMOTE_WORKFLOW.md
diskless-v2/audits/2026-10-30-f6018-host/SUMMARY.txt
diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P1.md
diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P2.md
```

---

## Immediate next action

Controlled P2 from current lk2nd:

```text
1. require committed P2 authorization and fresh preflight/full disk/identity checks;
2. start USB observation and arm the deferred USB-only NBD export;
3. reverify actual lk2nd identity, then boot the exact diagnostic once;
4. preserve/classify the complete run, consume the exception and restore hardware pause.
```
