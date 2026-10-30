# Diskless v2 Phase 6 V2 — reset/failure classification experiment

Status: **P2 PRESPECIFIED HOLD OUTCOME MET / ROOT CAUSE UNKNOWN / HARDWARE PAUSED**.

This document records the selected Phase6 reset-classification experiment and its implementation requirements under `AGENTS.md`. It does not authorize a real-device boot by itself.

Starting selection point:

```text
branch=diskless-v2
selection_start_HEAD=8b123faa06413c0beb1e49ac4080ee220748f7e3
implementation_start_HEAD=fff80df12c5071f68043b912e4c1cd69a17dcf41
Phase1-5=ACCEPTED/FROZEN
6V2-D=PASS (REAL DEVICE transport attach)
6V2-E=NOT REACHED
Run1 failure/reset cause=UNKNOWN
hardware=PAUSED
```

## 1. Binary question

> **Did the Run1-like observed reboot depend on the Linux `panic()` `panic_timeout` auto-restart path?**

This is deliberately narrower than “kernel panic vs userspace reboot”. A negative result does not prove userspace; it leaves watchdog/hang/other reset paths open.

## 2. Why this question was selected

Run1 proved that the accepted continuation can establish USB ECM, one NBD connection, and substantial p1/system I/O. The final completed NBD request had already been replied to when the host returned to `request-header-recv`. After Nexus-side I/O stopped, the user observed a later reboot. No p3/p6 second-stage evidence was accepted.

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

A source search for direct `panic_timeout = ...` assignments found target-independent initialization plus non-ARM assignments in MIPS/PowerPC/x86 trees. No target ARM/flo runtime assignment was identified that would autonomously restore the value after the supervisor writes it. The MSM watchdog reads `panic_timeout`; it does not restore it.

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

## 4. Android-side overwrite audit

The experiment is invalid if Android later restores `panic_timeout` to a nonzero value.

Source audit established:

- LineageOS 18.1 `rootdir/init.rc` writes `/proc/sys/kernel/panic_on_oops 1` during `on init`, which is consistent with the experiment target;
- the audited root `init.rc` does not write `/proc/sys/kernel/panic`;
- pinned flox `rootdir/etc/init.flox.rc` at device commit `936d74531565ca36e663e71dbcd43212fa93071b` does not write `/proc/sys/kernel/panic`.

Evidence class: `SOURCE_PROVEN` for those exact source files.

Because source trees are not identical to the final accepted filesystem artifacts, the prepared host implementation additionally scans the exact accepted system and patched-vendor images for canonical direct panic-timeout writer literals.

The image scanner is conservative:

```text
/proc/sys/kernel/panic_on_oops   allowed
kernel.panic_on_oops            allowed
/proc/sys/kernel/panic           FAIL
kernel.panic                     FAIL
```

It binds system/vendor identities to the accepted frozen-fact report and scans read-only via `mmap` so token classification cannot be corrupted by chunk boundaries.

Important limitation: absence of a literal does not mathematically prove that no program can use a nonliteral/programmatic sysctl interface. This limitation is recorded in every host report and must remain part of any negative-result interpretation.

Current status (2026-10-30-C): the writer scan was rerun on the designated Mac against freshly validated accepted system/vendor inputs and passed (`HOST_FACT`), with one allowed panic_on_oops literal and zero canonical direct panic-timeout literals. Its nonliteral/programmatic-writer limitation remains unchanged. Evidence: `audits/2026-10-30-f6018-host/panic-hold-host-gate.txt`.

## 5. Alternatives considered

### A. Re-run accepted continuation unchanged and immediately recover `last_kmsg`

Advantage: zero runtime delta.

Not selected as primary classifier because a reboot may immediately start another kernel before controlled recovery, making previous-boot provenance dependent on bootloader behavior. `last_kmsg` remains valuable only when same-run provenance is controlled.

### B. Read Qualcomm IMEM restart reason

Pinned `arch/arm/mach-msm/restart.c` uses an IMEM restart-reason word and distinguishes normal restart values from panic-related values when `CONFIG_MSM_DLOAD_MODE=y`.

However the accepted flo configuration has `CONFIG_DEVMEM` disabled and the current diskless runtime has no accepted userspace interface for reading that IMEM word. Exposing it would require a new kernel/runtime interface and therefore touch the frozen Phase1 mechanism.

Not selected because it introduces a larger and less-proven delta than the wrapper-only panic-timeout experiment.

### C. Panic-timeout hold A/B

Selected because it:

- changes no Phase1-5 source or accepted transport mechanism;
- changes no Android rc/fstab/system/vendor image;
- preserves stock enforcing baseline;
- manipulates a source-proven kernel runtime control already used by the accepted continuation;
- has a direct observable effect on one reset path.

## 6. Single intended causal variable

Accepted continuation runtime target:

```text
panic_timeout=5
```

Diagnostic runtime target:

```text
panic_timeout=0
```

The intended causal variable is **only** the runtime value of `kernel.panic`.

`panic_on_oops` remains `1`.

The diagnostic wrapper necessarily adds fail-closed measurement lines to prove the causal precondition. Those lines are precondition validation, not a second causal variable.

Frozen:

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
system/vendor filesystem bytes
SELinux enforcing baseline
host NBD protocol implementation
```

## 7. Mandatory runtime preconditions

F6-017 records that proving an image contains a sysctl write is not proof the running kernel accepted the value.

The revised diagnostic wrapper therefore fails closed **before usb0 wait and before NBD attach** unless all are true:

```text
/proc/sys/kernel/panic_on_oops is writable
write panic_on_oops=1 succeeds
read-back panic_on_oops == 1
/proc/sys/kernel/panic is writable
write panic=0 succeeds
read-back panic == 0
```

If the diagnostic run later establishes an NBD connection, that host-visible fact proves these fail-closed preconditions passed earlier in the same wrapper execution.

If no NBD connection appears, the reset-classification experiment is `INCONCLUSIVE`.

## 8. Prepared host implementation

Complete host implementation validation passed through SSH on the designated Mac in batch 2026-10-30-C (`HOST_FACT`), including actual current-input frozen facts, continuation and diagnostic reproducible builds, independent audits, writer scan and tracer differential/semantic self-tests. Exact raw output, exit statuses and identities are preserved under `audits/2026-10-30-f6018-host/`. No diagnostic hardware run was performed.

### Independent wrapper auditor

```text
scripts/v2/audit_phase6_v2_panic_hold_wrapper.py
```

It pins the accepted continuation wrapper SHA, constructs the expected diagnostic block independently, and requires the replacement wrapper to equal:

```text
exact accepted prefix
+ exact approved panic precondition block
+ exact accepted suffix
```

It also proves the read-back block occurs before usb0 wait and NBD attach and rejects revoked/permissive fragments.

### Accepted-image writer auditor

```text
scripts/v2/audit_phase6_v2_panic_runtime_writers.py
```

It binds the actual system/vendor images to the frozen-fact identities and rejects canonical direct panic-timeout writer literals. Its limitation regarding nonliteral programmatic writers is explicit.

### Host gate

```text
scripts/v2/phase6_v2_panic_hold_host_gate.sh
```

It:

1. requires the accepted frozen-fact report;
2. runs the accepted-image writer audit;
3. creates the diagnostic wrapper from the exact accepted continuation;
4. runs the independent wrapper auditor;
5. builds two images using the accepted Phase5 builder and requires byte identity;
6. reuses the accepted independent continuation image auditor;
7. records all identities, causal scope, writer-audit limitation, and `hardware_authorized=no`.

### Real preflight

```text
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
```

F6-018 is repaired: it first executes the frozen-fact gate, requires its fresh PASS marker, then executes the accepted Audit-V2 real preflight and panic-hold host gate and verifies image SHA/report fields. Fact/diagnostic report paths and baseline/diagnostic image overrides are distinct; disk/manifest inputs are bound across validation steps. Regression checks prove that stale PASS reports cannot bypass a failed current-input gate. Full real-input execution passed in batch C. Its final output still includes:

```text
hardware_authorized=no
```

Host PASS is therefore necessary but not sufficient for a real-device run.

## 9. Comparable failure-boundary requirement

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

## 10. Outcome table

### Outcome A — persistent hold

After a comparable failure boundary, NBD I/O stops and the device does **not** reboot/reenumerate for at least 90 seconds.

Interpretation:

```text
panic_timeout_dependency=SUPPORTED
```

This is strong A/B evidence that the Run1 reboot depended on a path affected by Linux panic timeout, most naturally a `panic()` path. It does not identify the panic call site or stack by itself.

After classification, a controlled manual transition to bootloader/recovery may be used to attempt same-run persistent-RAM capture. That capture is best-effort and must be labelled with controlled provenance.

### Outcome B — reboot still occurs

After a comparable failure boundary, the device still reboots while the pre-NBD runtime `panic_timeout=0` and `panic_on_oops=1` preconditions were proven.

Interpretation:

```text
panic_timeout_auto_restart=INSUFFICIENT_TO_EXPLAIN_RESET
```

This does **not** prove userspace reboot. Remaining classes include non-panic watchdog/reset, hang followed by watchdog/secure-side reset, userspace/init reboot, PMIC/other reset, another path, and the documented residual possibility of a nonliteral programmatic late panic-timeout writer.

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

## 11. Evidence to preserve for a future authorized hardware run

Under one run directory:

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

## 12. Stop rules

Stop and classify `INCONCLUSIVE` if:

- any preflight/hash check differs from documented accepted inputs;
- accepted-image writer audit fails;
- runtime sysctl read-back is not proven before transport attach;
- more than one NBD connection appears;
- the run fails before the comparable Run1 boundary;
- evidence capture is incomplete;
- any Phase1-5 mechanism changes unexpectedly.

Do not patch Android, NBD, USB, SELinux, or the last-read system library as a consequence of an inconclusive run.

## 13. Current authorization

```text
experiment design             SELECTED
host implementation           VALIDATED / HOST_FACT
accepted-image writer scan    PASS / HOST_FACT / documented scope limit
runtime read-back gate        HOST-AUDITED / DEVICE EXECUTION UNKNOWN
host implementation gate      PASS / HOST_FACT
host preflight chain          PASS / HOST_FACT / F6-018 VERIFIED
real-device run               P2 COMPLETED / AUTHORIZATION CONSUMED
hardware                      PAUSED
```

P1 closed after bootstrap and before diagnostic boot because the host helper incorrectly expected lk2nd identity in the version field. Actual product is `lk2nd-msm8960` with an empty version field. No reset experiment or NBD connection occurred; result is NOT_EXECUTED / INCONCLUSIVE. See P1 evidence and F6-022. Hardware pause is restored. A subsequent attempt requires separate committed authorization from the current verified lk2nd state, using the same diagnostic inputs and observation rules.

The total design now conditionally authorizes P2 under `PHASE6_V2_PANIC_HOLD_RUN_P2.md`, with no second bootstrap and exactly one diagnostic boot after fresh gates. Artifact identities and the binary question are unchanged. Restore hardware pause after P2 and commit its result before any new attempt.

Current result: P2 completed and met the prespecified comparable-boundary/hold observation: one connection, >=16MiB completed p1 replies, no accepted p3/p6 evidence, final inactivity 495.464s and continuous same USB entry for >=455.260s. `panic_timeout_dependency=SUPPORTED`, not a proven panic/stack/cause. User observed Lineage boot animation; the partition gate's absence is not proof that second stage did not execute. P2 is closed/consumed and hardware paused. Exact evidence and limits: P2 phase document and `audits/2026-10-30-P2/`. Next direction is host-only preparation of same-run persistent-console capture.
