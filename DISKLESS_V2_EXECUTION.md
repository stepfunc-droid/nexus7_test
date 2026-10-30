# Nexus 7 flo/flox Diskless Android v2 — Design and Execution Source of Truth

This is the project-wide source of truth for diskless-v2 architecture, accepted runtime contracts, phase acceptance, and the currently authorized direction.

`AGENTS.md` defines how every work session must consume and maintain this document. `diskless-v2/PROGRESS.md` is the concise current checkpoint. `diskless-v2/WORKLOG.md` is the append-only batch ledger. Phase documents are detailed evidence/history and do not override this document.

If this document, `PROGRESS.md`, phase evidence, and implementation disagree, **hardware work stops until reconciled**.

---

## 1. Goal and non-negotiable architecture

Build a reproducible, RAM-boot-only LineageOS 18.1 runtime for Nexus 7 2013 flo/flox whose running Linux does not depend on the failed internal eMMC.

Final architecture requirements:

- boot with `fastboot boot`; never flash the device;
- Linux does not register/use failed SDCC1/eMMC in diskless mode;
- Nexus USB device port carries the root-storage network transport;
- one USB Ethernet interface and exactly one NBD session carry one partitioned virtual disk;
- Android mounts normal `/dev/nbd0pN` partitions through deterministic fstab data;
- root transport exists before Android and does not depend on netd/vold/Android USB ownership;
- kernel/boot artifacts are tied to exact source/config identities;
- Android remains as close to stock Lineage behavior as practical;
- diagnostic bypasses never silently become architecture;
- classify failures from evidence before changing runtime mechanisms.

v1 is frozen reference/debugging only. v2 exists specifically to avoid v1's ad-hoc patching and undocumented assumptions.

---

## 2. Evidence vocabulary

Every claim must use the correct class:

- **REAL_DEVICE_FACT** — directly demonstrated on the physical Nexus 7.
- **HOST_FACT** — deterministic host build/audit/self-test only.
- **SOURCE_PROVEN** — established from exact pinned source used by this project.
- **IMPLEMENTED_UNPROVEN** — present in code/artifact but not independently demonstrated at runtime.
- **PROPOSED_DIAGNOSTIC** — designed diagnostic, not accepted runtime architecture.
- **REVOKED** — explicitly invalidated.
- **UNKNOWN** — insufficient evidence.

Host agreement, source proof, or code presence never becomes a real-device fact merely by wording.

---

## 3. Phase 1–5 accepted/frozen boundary

Phase1–5 may change only if new evidence directly invalidates an accepted gate.

### 3.1 Phase1 deterministic diskless kernel

Evidence: `REAL_DEVICE_FACT + HOST_FACT`.

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

Accepted invariants include:

- flo machine support;
- built-in NBD;
- `nbd.max_part=8`;
- built-in USB Ethernet gadget;
- `CONFIG_USB_G_ANDROID=n`;
- ext4/TCP/IPv4 root-transport pieces built in;
- persistent RAM / Android ram_console;
- SDCC1/eMMC registration disabled for diskless builds;
- diskless USB guard;
- system-suspend guard at `PM_SUSPEND_PREPARE`.

Exact Phase4 kernel identity is also stored in `diskless-v2/phase4-accepted.env`.

### 3.2 Phase2 single partitioned NBD disk

Evidence: `HOST_FACT + REAL_DEVICE_FACT`.

```text
p1 system    ext4  RO
p2 vendor    ext4  RO
p3 cache     ext4  RW
p4 extended
p5 userdata  ext4  RW
p6 persist   ext4  RW
p7 metadata  raw   RW/reserved
sector_size=512
nbd.max_part=8
```

Logical layout source: `diskless-v2/layout.json`.

One raw disk is exported through one NBD/TCP session on port `10810`.

### 3.3 Phase3 transport supervisor

Evidence: `REAL_DEVICE_FACT`.

Frozen runtime conventions:

```text
/bin/busybox
#!/bin/busybox sh
BB=/bin/busybox
PATH=/bin:/sbin
/etc/diskless-v2-layout
Nexus usb0=172.16.42.1/24
Mac endpoint=172.16.42.2:10810
one /dev/nbd0 kernel session
```

Accepted stress result:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
```

Renaming BusyBox to `/diskless-busybox` is `REVOKED`.

### 3.4 Phase4 USB/root-transport protection

Evidence: `REAL_DEVICE_FACT`.

```text
USB_DISKLESS_GUARD=enabled
USB_SYSTEM_SUSPEND_GUARD=pm_notifier
USB_SYSTEM_SUSPEND_STAGE=PM_SUSPEND_PREPARE
```

Phase4 preserved the NBD session through the suspend gate and repeated transport stress.

A later USB/NBD disappearance is not, by itself, evidence that transport caused a later failure.

### 3.5 Phase5 deterministic Android fstab and first-stage handoff

Evidence: `REAL_DEVICE_FACT + HOST_FACT`.

Accepted fstab:

```text
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
/system  <- /dev/block/nbd0p1
/vendor  <- /dev/block/nbd0p2
/cache   <- /dev/block/nbd0p3
/data    <- /dev/block/nbd0p5
/persist <- /dev/block/nbd0p6
metadata <- /dev/block/nbd0p7
```

Accepted source identities:

```text
system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
original_lineage_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
busybox_sha256=cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

Frozen Phase5D packaging/handoff:

```text
/init                    diskless supervisor
/init.android            exact original Lineage boot init
/bin/busybox             exact accepted BusyBox
/etc/diskless-v2-layout  exact accepted layout
```

Phase5D proved on the real device that the same NBD session survived handoff and original Lineage first-stage mounted:

```text
/system <- /dev/block/nbd0p1
/vendor <- /dev/block/nbd0p2
```

Before handoff, supervisor-owned `/dev/pts`, `/sys`, and `/proc` mounts are detached according to the accepted Phase5 behavior, then `/init.android` is executed.

---

## 4. Accepted Phase6 continuation baseline

Phase6 continues from Phase5D by subtraction/minimal delta, not redesign.

The first reset design using `/diskless-busybox` and `rdinit=/diskless-init` is `REVOKED`; its first real-device boot failed before any NBD connection.

Audit-V2 continuation preserves Phase5D transport/handoff and removes diagnostic observers/SIGSTOP so Android may continue naturally.

Accepted continuation identity:

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
handoff=exec-/init.android
busybox=/bin/busybox
android_rc_modifications=none
selinux_policy=stock-enforcing-baseline
```

`HOST_FACT` (2026-10-30 takeover audit): the exact accepted wrapper still contains a best-effort copy of `/proc/last_kmsg` into `/www/last_kmsg.txt`, and applet availability checks for `httpd`/`nc`. It launches neither server and does not use that optional copy as a gate or as Run1 evidence. Preserve these accepted bytes; “observers removed” must not be read as “every diagnostic reference removed”.

6V2-A/B/C are host facts. They do not by themselves authorize hardware.

---

## 5. Current runtime contract relevant to Phase6

| Item | Current value | Evidence |
|---|---|---|
| `androidboot.diskless` | `1` | HOST_FACT / implemented input |
| `nbd.max_part` | `8` | REAL_DEVICE_FACT |
| `rdinit` | `/init` | HOST_FACT + observed continuation execution |
| SELinux | stock enforcing baseline | HOST_FACT |
| `panic_on_oops` | accepted wrapper requests `1` before handoff | IMPLEMENTED_UNPROVEN as Run1 read-back |
| `panic_timeout` | cmdline has `panic=5`; wrapper requests `5` | HOST_FACT / IMPLEMENTED_UNPROVEN as Run1 read-back |
| MSM watchdog | flo config enables it; source default enabled | SOURCE_PROVEN / Run1 exact runtime state UNKNOWN |

Pinned source establishes:

```text
ARM die() + panic_on_oops != 0 -> panic("Fatal exception")
panic_timeout > 0             -> wait timeout seconds
panic_timeout != 0            -> emergency_restart()
panic_timeout == 0            -> no emergency_restart(); terminal panic loop
MSM panic notifier + timeout=0 -> watchdog disabled
MSM panic notifier + nonzero   -> bark/bite moved to timeout+4s
```

APQ8064 watchdog data:

```text
pet_time=10000 ms
bark_time=45000 ms
has_secure=true
```

A target-source search found no ARM/flo code path that autonomously restores `panic_timeout` after the supervisor writes it. This is `SOURCE_PROVEN` scope, not proof that userspace cannot write it later.

---

## 6. Boot and stage flow

```text
stock fastboot
  -> lk2nd RAM boot / forced fastboot
  -> diskless-v2 kernel + supervisor
       -> minimal proc/sys/dev
       -> usb0
       -> one NBD attach
       -> validate partitions
       -> detach supervisor mounts
       -> exec /init.android
            -> original Lineage first-stage
            -> p1 system + p2 vendor
            -> SELinux setup/transition
            -> second-stage init
            -> fs: p3 cache + p6 persist
            -> late-fs: p5 userdata
            -> later services / launcher
```

Stage evidence rules:

- p1/p2 activity can occur during first stage;
- filesystem-internal p3 or p6 activity is stronger evidence of second-stage `fs` processing;
- p5 I/O alone must not be called late-fs evidence;
- NBD sees block traffic, not callers; file extent overlap cannot identify a process or semantic use.

---

## 7. Phase status

```text
Phase 0   v1 frozen/documented                       COMPLETE
Phase 1   deterministic diskless kernel              ACCEPTED / FROZEN
Phase 2   single partitioned NBD disk                ACCEPTED / FROZEN
Phase 3   transport supervisor + stress              ACCEPTED / FROZEN
Phase 4   USB/root-transport protection              ACCEPTED / FROZEN
Phase 5   Android fstab + first-stage handoff        ACCEPTED / FROZEN
Phase 6   full Android integration                   ACTIVE
Phase 7   normal runtime feature restoration         NOT REACHED
```

Audit-V2 state:

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

## 8. Phase6 Run1 — accepted observations only

```text
NBD connections=1
requests=1755
reads=1755
writes=0
read_bytes=75442176
phase=request-header-recv
last=[READ offset=0x1ce00000 (484442112) length=94208 fua=0]
connection_close=transport-error:TimeoutError(60, 'Operation timed out')
```

Accepted interpretation:

- 1755 READs / 75,442,176 bytes completed;
- final READ was already serviced; host was waiting for another request;
- host ETIMEDOUT is not accepted as the cause;
- Nexus-side NBD I/O then stopped;
- the user subsequently observed the device reboot;
- no accepted p3/cache or p6/persist filesystem evidence appeared;
- 6V2-E remains NOT REACHED;
- the failure/reset path remains UNKNOWN.

Current classification:

```text
transport_attach=PROVEN
transport_caused_failure=NOT_PROVEN
kernel_panic=UNKNOWN
kernel_hang=UNKNOWN
watchdog_reset=UNKNOWN
userspace_or_init_reboot=UNKNOWN
other_reset_path=UNKNOWN
second_stage_or_later=NOT_PROVEN
```

The final p1 block overlap with `/system/lib/libkeystore_aidl.so` is forensic context only and has no caller/root-cause meaning.

---

## 9. Current blocker

The blocker is the unclassified failure/reset boundary after substantial p1/system I/O and before accepted p3/p6 second-stage evidence.

Do not infer a result from stale Run1 `/proc/last_kmsg`; previous-boot provenance can no longer be reconstructed after the fact.

---

## 10. Selected next experiment — panic-timeout reset classification

Detailed design: `diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md`.

Binary question:

> **Did the Run1-like observed reboot depend on Linux `panic()` `panic_timeout` auto-restart?**

This is narrower than “kernel panic vs userspace reboot”.

Single intended causal variable:

```text
accepted continuation: panic_timeout=5
diagnostic:            panic_timeout=0
panic_on_oops:         remains 1
```

Frozen for the experiment:

```text
kernel bytes
USB/root-transport guards
NBD attach/retry/liveness
partition layout/disk contents
fstab
BusyBox payload/path/shebang
/init -> /init.android handoff
original Lineage init
Android rc/system/vendor bytes
SELinux enforcing baseline
host NBD protocol
```

Why selected:

- no Phase1–5 source change;
- source-proven effect on Linux panic auto-restart;
- Qualcomm IMEM restart-reason readout would require a new frozen-kernel/readout path because `/dev/mem` is disabled;
- old Run1 last_kmsg provenance is uncontrolled.

---

## 11. Experiment preconditions and prepared host implementation

F6-017 established that an image containing `echo 0 > /proc/sys/kernel/panic` does not prove the running kernel accepted the value.

The revised diagnostic wrapper is designed to fail closed **before usb0 and before NBD attach** unless:

```text
panic_on_oops sysctl writable
write panic_on_oops=1 succeeds
read-back panic_on_oops == 1
panic sysctl writable
write panic=0 succeeds
read-back panic == 0
```

Therefore a later host-observed NBD connection implies these preconditions passed earlier in the same wrapper execution.

Prepared host tools:

```text
scripts/v2/audit_phase6_v2_panic_hold_wrapper.py
scripts/v2/audit_phase6_v2_panic_runtime_writers.py
scripts/v2/phase6_v2_panic_hold_host_gate.sh
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
```

The independent wrapper auditor requires the diagnostic wrapper to equal the accepted continuation's exact bytes except for one approved precondition block. It proves the block occurs before usb0/NBD.

The accepted-image writer auditor binds to frozen system/vendor identities and conservatively rejects canonical direct panic-timeout writer literals while allowing `panic_on_oops`. It is read-only. Its explicit limitation is that it cannot prove absence of a writer using a nonliteral/programmatic sysctl interface.

Source audit also found:

- Lineage 18.1 root `init.rc` reasserts `panic_on_oops=1`;
- that audited root `init.rc` does not write `panic_timeout`;
- pinned flox `init.flox.rc` does not write `panic_timeout`.

**Current evidence class (2026-10-30 takeover):** an existing, untracked host-gate report claims PASS and names paths on the original host. Its complete execution provenance has not been revalidated. The local diagnostic wrapper and both continuation/diagnostic images independently passed the existing auditors in this session (`HOST_FACT`); the diagnostic image SHA256 is `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`. This is a narrower result than a complete preflight or deterministic rebuild. Evidence: `diskless-v2/audits/2026-10-30-takeover.txt`.

**Open host-preflight defect (F6-018):** the panic-hold preflight calls the base real preflight, but neither invokes `phase6_v2_frozen_fact_gate.sh`. The panic-hold host gate consumes an existing frozen-fact report. Earlier documentation claiming that this call chain refreshes frozen facts is `REVOKED`. The frozen-fact gate must actually be executed against current inputs before any full-preflight result can be accepted; the host chain needs repair and verification in a separate batch. No runtime or host script was changed during takeover.

---

## 12. Comparable-boundary and outcome rules

A future result is interpretable only if the diagnostic run reaches a Run1-comparable boundary:

```text
exactly one NBD connection
valid NBD handshake/requests
substantial p1/system I/O
no accepted p3/p6 evidence before stop/reset
Nexus request stream subsequently stops
```

Exact request count or final p1 file need not match.

Outcome A:

```text
comparable boundary + no reboot/reenumeration for >=90s
-> panic_timeout_dependency=SUPPORTED
```

This strongly supports a path affected by Linux panic timeout, most naturally `panic()`, but does not identify the panic stack/call site.

Outcome B:

```text
comparable boundary + reboot still occurs
-> panic_timeout_auto_restart=INSUFFICIENT_TO_EXPLAIN_RESET
```

This is **not** proof of userspace reboot. Remaining classes include non-panic watchdog/reset, hang+watchdog/secure-side reset, userspace/init reboot, PMIC/other reset, another path, and the documented residual possibility of a nonliteral late panic-timeout writer.

Outcome C:

```text
precondition failure / no NBD / non-comparable boundary / incomplete evidence
-> INCONCLUSIVE
```

No root-cause inference is allowed from an inconclusive run.

---

## 13. Failure evidence to preserve in any future authorized run

One run directory must contain:

```text
preflight output
host-gate report
exact diagnostic image SHA256
NBD JSONL trace
NBD server stdout+stderr transcript
wall-clock observation notes
post-run classifier result
optional same-run last_kmsg with explicit provenance
```

Terminal scrollback must never be the only copy.

---

## 14. Binding debugging rules

1. Classify before patching.
2. One experiment = one binary question.
3. Phase1–5 remain frozen without direct contradicting evidence.
4. Never patch the last visible file/log line merely because it was last.
5. NBD block traffic does not identify a userspace caller.
6. TCP state/timeout is not kernel-liveness proof or root cause by itself.
7. Missing `last_kmsg` is not evidence of userspace reboot.
8. `last_kmsg` for a specific run requires controlled previous-boot provenance.
9. Host builder/auditor agreement does not create runtime truth.
10. Runtime causal knobs require same-run validation/read-back when possible.
11. No Android rc bypass without a captured subsystem failure proving necessity.
12. Do not revisit power diagnosis without new evidence.
13. Every coherent work batch closes in `WORKLOG.md` before the next batch.
14. Every accepted/revoked runtime direction is synchronized here before hardware proceeds.
15. `UNKNOWN` and `INCONCLUSIVE` are valid results and preferred over unsupported explanations.

See `diskless-v2/PHASE6_FAILURE_LOG.md` and referenced F6 files for the permanent regression history.

---

## 15. Hardware authorization and immediate next action

Execution routing (user instruction, 2026-10-30): the current machine coordinates/edits; run Mac builds and full host/device operations through `ssh zhangjw@192.168.1.63` in `/Users/zhangjw/nexus7_test`. Transfer independent changes/snapshots by SCP and verify destination identities. The coordinator's `/Volumes/zhangjw/` is an SMB view of the remote user's directory, so do not treat these paths as separate checkouts. See `diskless-v2/REMOTE_WORKFLOW.md`. Notify the user if Debian compilation is required; no Debian host is designated.

Read-only remote enumeration confirmed Nexus `07a117ae`, product `flo`, bootloader `FLO-04.08` in fastboot (`REAL_DEVICE_FACT` at inspection time). User authorization covers these read-only queries; it does not lift the experiment pause.

F6-019: after a remote commit, coordinator-side Git through SMB reported inconsistent/unreadable index state while direct remote Git remained healthy. Perform Git inspection, staging and commits on the Mac too; do not reset the shared index from the coordinator. The underlying inconsistency mechanism is `UNKNOWN`.

```text
experiment design             SELECTED
host implementation           PREPARED
runtime read-back gate        HOST-AUDITED / DEVICE EXECUTION UNKNOWN
accepted-image writer scan    EXISTING PASS REPORT / REVALIDATION PENDING
host preflight                F6-018 REPAIR / CURRENT-INPUT RUN PENDING
real-device run               NOT AUTHORIZED
hardware                      PAUSED
```

Immediate next action is **host-only**:

1. The previous implementation batch was closed by `cc649ef92886ff2854128c936c58fddfa98f92ee`; do not repeat that completed handoff step.
2. Repair and verify F6-018: require actual frozen-fact validation before consuming its report, while preserving Phase1–5 runtime bytes.
3. Execute on the remote Mac, where `/Users/zhangjw/` input defaults exist. `/Volumes/zhangjw/` is the coordinator's SMB view, not a replacement path for remote execution. Path presence alone does not validate identity.
4. Run the complete host validation against exact current inputs and preserve stdout, stderr, exit status, and hashes. Review the existing imported report separately from newly produced evidence.
5. Update this document, `PROGRESS.md`, experiment evidence, and `WORKLOG.md` before considering hardware authorization.

No state-changing `fastboot` command is authorized at this checkpoint. Read-only enumeration/product queries are covered by the user's remote-inspection instruction.
