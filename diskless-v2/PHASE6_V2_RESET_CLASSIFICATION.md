# Diskless v2 Phase 6 V2 — reset/failure classification experiment

Status: **EXPERIMENT SELECTED / IMPLEMENTATION NOT YET ACCEPTED / HARDWARE PAUSED**.

This document records the evidence-selection batch performed under `AGENTS.md` after Audit-V2 Run1. It does not authorize a real-device boot by itself.

Starting point:

```text
branch=diskless-v2
starting_HEAD=8b123faa06413c0beb1e49ac4080ee220748f7e3
Phase1-5=ACCEPTED/FROZEN
6V2-D=PASS (REAL DEVICE transport attach)
6V2-E=NOT REACHED
Run1 failure/reset cause=UNKNOWN
hardware=PAUSED
```

## 1. Question to answer

The next experiment asks exactly one binary causal question:

> **Did the Run1-like observed reboot depend on the Linux `panic()` `panic_timeout` auto-restart path?**

This is deliberately narrower than “kernel panic vs userspace reboot”. A negative result does not prove userspace; it leaves watchdog/hang/other reset paths open.

## 2. Why this question is highest-information now

Run1 proved that the accepted continuation can establish USB ECM, one NBD connection, and substantial p1/system I/O. The last completed NBD request was already replied to when the host returned to `request-header-recv`. After Nexus-side I/O stopped, the user observed a later reboot. No p3/p6 second-stage evidence was accepted.

The failure boundary therefore remains unclassified among at least:

```text
kernel panic/oops
kernel hang/deadlock
watchdog reset
userspace/init reboot
other reset path
```

The accepted continuation already requests before Android handoff:

```text
panic_on_oops=1
panic_timeout=5
```

The pinned kernel source gives a source-proven way to manipulate only panic auto-restart behavior without changing the frozen kernel or transport.

## 3. Source-proven semantics

Pinned kernel commit:

```text
0da5107137f93b8d8f697e949ab0784f5ace450c
```

### 3.1 ARM oops -> panic

`arch/arm/kernel/traps.c` shows `die()` calls:

```text
panic("Fatal exception")
```

when `panic_on_oops` is nonzero.

Evidence class: `SOURCE_PROVEN`.

### 3.2 panic timeout behavior

`kernel/panic.c` shows:

```text
panic_timeout > 0  -> wait panic_timeout seconds
panic_timeout != 0 -> emergency_restart()
panic_timeout == 0 -> no emergency_restart(); remain in terminal panic loop
```

Evidence class: `SOURCE_PROVEN`.

### 3.3 MSM watchdog interaction

The pinned flo configuration inherits:

```text
CONFIG_MSM_WATCHDOG=y
```

and the diskless transform does not change that symbol.

`arch/arm/mach-msm/msm_watchdog.c` registers the watchdog with `late_initcall()`. Kernel `init/main.c` runs initcalls before executing `/init`, so a successful diskless supervisor boot occurs after watchdog initialization.

The watchdog panic notifier does:

```text
panic_timeout == 0 -> disable watchdog
panic_timeout != 0 -> reprogram watchdog bark/bite to panic_timeout + 4 seconds
```

The APQ8064 watchdog platform data uses:

```text
pet_time=10000 ms
bark_time=45000 ms
has_secure=true
```

Evidence class: `SOURCE_PROVEN`.

Consequence: if execution enters Linux `panic()` with `panic_timeout=0`, the normal panic auto-restart path is suppressed and the MSM watchdog panic notifier is expected to disable the watchdog before the terminal panic loop.

This does **not** suppress a watchdog/reset path that occurs without entering Linux `panic()`.

## 4. Alternatives considered and rejected for this experiment

### A. Re-run the accepted continuation unchanged and immediately recover `last_kmsg`

Advantage: zero runtime delta.

Rejected as the primary binary classifier because a reboot may immediately start another kernel before controlled recovery, making previous-boot provenance dependent on bootloader behavior. `last_kmsg` remains valuable only when same-run provenance is controlled.

### B. Read Qualcomm IMEM restart reason

Pinned `arch/arm/mach-msm/restart.c` uses an IMEM restart-reason word and distinguishes normal restart values from panic-related values when `CONFIG_MSM_DLOAD_MODE=y`.

However the accepted flo configuration has `CONFIG_DEVMEM` disabled and the current diskless runtime has no accepted userspace interface for reading that IMEM word. Exposing it would require a new kernel/runtime interface and therefore touch the frozen Phase1 mechanism.

Rejected for now because it introduces a larger and less-proven delta than the wrapper-only panic-timeout experiment.

### C. Panic-timeout hold A/B

Selected because it:

- changes no Phase1-5 source or accepted transport mechanism;
- changes no Android rc/fstab/system image;
- preserves stock enforcing baseline;
- manipulates a source-proven kernel runtime control already used by the accepted continuation;
- has a direct observable effect on one reset path.

## 5. Single intended experimental variable

Accepted continuation behavior:

```text
panic_timeout=5
```

Diagnostic behavior:

```text
panic_timeout=0
```

The intended experimental variable is **only** the runtime value of `kernel.panic`.

`panic_on_oops` must remain `1`.

All of the following are frozen:

```text
accepted kernel bytes
USB ECM/root-transport guards
NBD client attach/retry/liveness behavior
partition layout and disk contents
fstab
BusyBox payload/path/shebang
/init -> /init.android handoff
original Lineage init
Android rc files
SELinux enforcing baseline
host NBD protocol implementation
```

## 6. Mandatory runtime preconditions

The pre-governance panic-hold helper is not sufficient as written because it proves an image contains a command that *attempts* to write `panic=0`, but it does not prove the running kernel accepted the value.

A revised diagnostic wrapper must fail closed **before NBD attach** unless all of the following are true:

```text
/proc/sys/kernel/panic is writable
write 0 succeeds
read-back /proc/sys/kernel/panic == 0
read-back /proc/sys/kernel/panic_on_oops == 1
```

These read-backs are experiment precondition checks, not additional causal variables.

If the diagnostic run later establishes an NBD connection, that host-visible fact also proves the fail-closed preconditions were passed earlier in the wrapper.

If no NBD connection appears, the reset-classification experiment is `INCONCLUSIVE`.

## 7. Required host gates before any hardware authorization

The next implementation batch must revise the diagnostic builder/gates so they prove:

1. exact accepted continuation wrapper/input identity;
2. diagnostic wrapper delta is limited to:
   - `panic_timeout 5 -> 0`;
   - fail-closed read-back checks for `panic=0` and unchanged `panic_on_oops=1`;
3. accepted kernel bytes unchanged;
4. accepted Android init/fstab/BusyBox/layout unchanged;
5. no Android rc changes;
6. transport setup unchanged;
7. diagnostic image builds reproducibly;
8. real-device preflight re-runs the accepted 6V2-A/B/C identity gates;
9. all required host logs, including stderr, have explicit persisted paths.

Until those gates exist and pass, hardware remains `PAUSED`.

## 8. Comparable failure-boundary requirement

The A/B result is interpretable only if the diagnostic run reproduces the relevant Run1 boundary closely enough:

```text
exactly one NBD connection
valid NBD handshake and requests
substantial p1/system I/O after handoff
no accepted p3/p6 second-stage evidence before the stop/reset event
Nexus-side NBD request stream subsequently stops
```

Exact request count, last system block, or last library name need not match; those are not semantic stage markers.

If the diagnostic run materially diverges before this boundary, result = `INCONCLUSIVE`.

## 9. Outcome table

### Outcome A — persistent hold

After a comparable failure boundary, NBD I/O stops and the device does **not** reboot/reenumerate for a conservative observation interval of at least 90 seconds.

Interpretation:

```text
panic_timeout_dependency=SUPPORTED
```

This is strong A/B evidence that the Run1 reboot depended on a path affected by Linux panic timeout, most naturally a `panic()` path. It does not identify the panic call site or stack by itself.

After classification, a controlled manual transition to bootloader/recovery may be used to attempt same-run persistent-RAM capture. That capture is best-effort and must be labelled with its controlled provenance.

### Outcome B — reboot still occurs

After a comparable failure boundary, the device still reboots while runtime `panic_timeout=0` and `panic_on_oops=1` preconditions were proven before NBD attach.

Interpretation:

```text
panic_timeout_auto_restart=INSUFFICIENT_TO_EXPLAIN_RESET
```

This does **not** prove userspace reboot. Remaining classes include non-panic watchdog/reset, hang followed by watchdog/secure-side reset, userspace/init reboot, PMIC/other reset, or another path.

### Outcome C — boundary not comparable

Examples:

```text
no NBD connection
precondition check fails
transport fails before substantial p1 I/O
p3/p6 evidence appears and execution clearly proceeds farther
unexpected additional runtime delta is found
host evidence is incomplete
```

Interpretation:

```text
INCONCLUSIVE
```

No reset-cause inference is allowed.

## 10. Evidence to preserve for the future hardware run

A future authorized run must persist, under one run directory:

```text
preflight output
host-gate report
exact diagnostic image SHA256
NBD JSONL trace
NBD server stdout+stderr transcript
wall-clock run notes / observed reboot-or-hold state
post-run classifier output
optional same-run last_kmsg capture with provenance statement
```

Do not depend on terminal scrollback as the only copy of evidence.

## 11. Stop rules

Stop and classify `INCONCLUSIVE` if:

- any preflight/hash check differs from documented accepted inputs;
- runtime sysctl read-back is not proven before transport attach;
- more than one NBD connection appears;
- the run fails before the comparable Run1 boundary;
- evidence capture is incomplete;
- any Phase1-5 mechanism changes unexpectedly.

Do not patch Android, NBD, USB, SELinux, or the last-read system library as a consequence of an inconclusive run.

## 12. Current authorization

```text
experiment design          SELECTED
existing panic-hold code   NEEDS REVISION
host implementation gate   NOT YET PASSED UNDER THIS DESIGN
real-device run            NOT AUTHORIZED
hardware                   PAUSED
```

Next batch: revise the panic-hold host gate/wrapper to enforce runtime read-back, re-audit the exact artifact delta, then update this document and the project source of truth with the host result.