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
hardware                PAUSED
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

Prepared, **not yet executed on the user's accepted artifacts**:

```text
scripts/v2/audit_phase6_v2_panic_hold_wrapper.py
scripts/v2/audit_phase6_v2_panic_runtime_writers.py
scripts/v2/phase6_v2_panic_hold_host_gate.sh
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
```

The diagnostic wrapper fails closed before usb0/NBD unless same-run read-back proves:

```text
/proc/sys/kernel/panic == 0
/proc/sys/kernel/panic_on_oops == 1
```

The writer audit binds to accepted system/vendor image identities and rejects canonical direct panic-timeout writer literals. It explicitly cannot prove absence of a nonliteral/programmatic sysctl writer.

F6-017 permanently records why a write command alone is insufficient.

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
host implementation           PREPARED
runtime read-back gate        IMPLEMENTED / EXECUTION PENDING
accepted-image writer scan    IMPLEMENTED / EXECUTION PENDING
host preflight                NOT YET RUN
real-device run               NOT AUTHORIZED
hardware                      PAUSED
```

No `fastboot` command is authorized now.

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
```

---

## Immediate next action

Host-only:

```text
1. close the current implementation batch in WORKLOG.md;
2. git pull on the user's Mac;
3. run phase6_v2_panic_hold_real_preflight.sh and persist output;
4. review actual PASS/failure output;
5. only after review update authorization state.
```
