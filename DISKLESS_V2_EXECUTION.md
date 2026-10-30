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

Scope clarification: the fstab mapping above is an accepted artifact contract (`HOST_FACT`); the real-device Phase5 gate proved p1/p2 first-stage mounts only. It did not prove which `/fstab.flox` second-stage sees after SwitchRoot or that cache/persist/userdata mount from NBD. H later proved an independent stock system-root file. R1's explicit one-file derivative now separately proves successful NBD cache/persist/data mounts and late-fs (`REAL_DEVICE_FACT`); this does not retroactively extend Phase5 acceptance to the original clean system or establish full Android boot. Exact derivative/evidence is in §15 and the R1 phase document.

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
| P2 pre-NBD sysctls | fail-closed read-back of panic=0 and panic_on_oops=1 passed before the observed attach | REAL_DEVICE_FACT scoped to that precondition; later values UNKNOWN |
| Q2 working desktop profile | root-fstab derivative + Q1 peer rule + GPS HAL NULL entry; exact identities in §16 | REAL_DEVICE_FACT: setup completed, desktop reached; GPS unavailable accepted by user |

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
Phase 7   normal runtime feature verification        NEXT / GPS omission accepted
```

Audit-V2 state:

```text
6V2-A frozen facts                         PASS (HOST)
6V2-B continuation semantic/image audit    PASS (HOST)
6V2-C traced NBD differential/audit        PASS (HOST)
6V2-D transport attach                     PASS (REAL DEVICE)
6V2-E p3/p6 second-stage evidence          PASS (REAL DEVICE / root-fstab R1)
6V2-F late-fs evidence                     PASS (REAL DEVICE / R1 console)
6V2-G first genuine later blocker          Q1 GSS panic localized; Q2 GPS-unavailable profile reaches desktop
core diskless Android UI boot              PASS (REAL DEVICE / Q2 user desktop + continuous USB/NBD)
remaining runtime/feature acceptance        NOT COMPLETE / normal functions and long-term stability UNKNOWN
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

Q2 now completes setup and reaches the desktop with GPS HAL returning NULL. This is REAL_DEVICE_FACT for the explicit GPS-unavailable diskless profile, corroborated by continuous same USB gadget and one active NBD session beyond12 minutes. The user accepts GPS omission. No current startup blocker is established in this profile; ordinary feature behavior and long-term stability remain UNKNOWN. Preserve the live root export. Exact result/limits/handoff are in §16. The following paragraphs are historical pre-Q2 findings, not current device state.

The diskless Android run failed to finish startup and later automatically returned to eMMC. The finite P2 hold observation did not establish panic-timeout dependency; that causal support is REVOKED (F6-023). Current ADB is verified eMMC-backed and must not be called diskless success. The retained p3/p6 gate is an evidence gate, not proof that second-stage execution never occurred.

A root capture now preserves a previous NBD-backed kernel console (225,756 bytes, SHA256 `c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497`). It directly records second-stage `mount_all ./fstab.flox` waiting for/skipping eMMC cache/persist/userdata paths, leaving writable Android directories on a read-only filesystem. Much later it records NBD receive failure (-110), cascading I/O errors, and an explicit init `boringssl-self-check-failed` reboot. These are REAL_DEVICE_FACT about the captured previous NBD boot, not proof that BoringSSL or transport was the first cause.

Exact P2 attribution remains qualified: the ring head/cmdline is missing and later starts were not controlled. NBD identity/timing, user timeline and stable current boot ID corroborate association, but do not silently upgrade it to controlled named-run provenance. See `diskless-v2/PHASE6_V2_PREVIOUS_CONSOLE_CAPTURE.md`. This evidence justifies host auditing of the exact accepted system's post-SwitchRoot fstab namespace before any runtime change.

The root-fstab audit/correction/R1 are complete and prove NBD writable mounts/late-fs. Q1 subsequently validates progress with explicit peer-route protection. R1's exclusive initiating cause is not independently proven; the current remaining blocker is Q1's GSS panic above.

Do not infer a result from stale Run1 `/proc/last_kmsg`; previous-boot provenance can no longer be reconstructed after the fact.

---

## 10. Historical P1/P2 experiment — panic-timeout reset classification

P1/P2 are consumed and their early causal support is REVOKED. This section preserves historical design and boot-artifact provenance; it does not select or authorize a new run. Current direction/authorization is in §15 and `PHASE6_ROOT_FSTAB_RUN_R1.md`.

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

**Current evidence class (2026-10-30-C):** complete host validation passed through SSH on the designated Mac (`HOST_FACT`). Frozen-input validation, continuation reproducible A/B builds and image audit, tracer differential/semantic self-tests, accepted-image writer scan, diagnostic A/B builds and independent audits, and the repaired complete panic-hold preflight all returned exit 0. Diagnostic SHA256 remains `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`; continuation SHA256 remains the accepted `0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780`. New evidence supersedes reliance on the imported report. Full stdout/stderr, reports and run identities are committed under `diskless-v2/audits/2026-10-30-f6018-host/`.

**F6-018 repaired and verified:** `phase6_v2_panic_hold_real_preflight.sh` now executes the frozen-fact gate before the accepted base preflight and diagnostic host gate. It scopes the fact-report path independently of the diagnostic-report path, binds disk/manifest inputs across the checks, and distinguishes baseline and diagnostic image overrides. Isolated orchestration checks cover failing validation with stale PASS reports, absent fresh PASS marker, base-preflight failure and successful ordered execution with custom paths. A real-validator missing-input check also rejected a stale PASS report before producing an image. No frozen Phase1–5 runtime mechanism changed; no hardware boot was performed. Every host PASS still ends with `hardware_authorized=no`.

---

## 12. Historical P1/P2 comparable-boundary and outcome rules

A future result is interpretable only if the diagnostic run reaches a Run1-comparable boundary:

```text
exactly one NBD connection
valid NBD handshake/requests
substantial p1/system I/O
no accepted p3/p6 evidence before stop/reset
Nexus request stream subsequently stops
```

Exact request count or final p1 file need not match.

Historical Outcome A — causal interpretation REVOKED by F6-023:

```text
comparable boundary + no reboot/reenumeration for >=90s
-> finite_hold_observed (observation only)
-> causal_dependency=UNKNOWN until the later boot/reset sequence is resolved
```

P2 later automatically returned to eMMC. A finite idle/no-reenumeration window was insufficient to establish dependence on panic timeout; the earlier SUPPORTED claim is REVOKED. Runtime identity and terminal/later state must be checked before classifying, and a cached screen or later ADB connection does not establish continuity of the same kernel.

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

Historical pre-P1 enumeration confirmed Nexus `07a117ae`, product `flo`, bootloader `FLO-04.08` in fastboot (`REAL_DEVICE_FACT` at that inspection). P1/P2 transitions below are consumed history. Current R1 state is stated at the end of this section.

F6-019: after a remote commit, coordinator-side Git through SMB reported inconsistent/unreadable index state while direct remote Git remained healthy. Perform Git inspection, staging and commits on the Mac too; do not reset the shared index from the coordinator. The underlying inconsistency mechanism is `UNKNOWN`.

```text
historical P1/P2 design       CONSUMED
host implementation           VALIDATED / HOST_FACT
runtime read-back gate        HOST-AUDITED / DEVICE EXECUTION UNKNOWN
accepted-image writer scan    PASS / HOST_FACT / documented scope limit
host preflight                PASS / HOST_FACT / F6-018 VERIFIED
real-device run               P2 FAILED / LATER AUTO RETURN TO eMMC / AUTHORIZATION CONSUMED
hardware after P2             PAUSED (later R1 activation below governs)
```

Run-specific authority: `diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P1.md`. Batch D prepared and host-tested an external entrypoint pinned to the unchanged V2 server; protocol/final-disk differential tests pass in both modes, and completed-reply snapshots preserve idle-connection evidence. USB dry-run and physical observer availability are established (`HOST_FACT` for host tooling; no diagnostic runtime claim). Evidence: `diskless-v2/audits/2026-10-30-observation-host/`.

P1's historical exception allowed one existing lk2nd bootstrap RAM boot and one exact diagnostic RAM boot; it was consumed/closed before the diagnostic. Diagnostic SHA remains `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`; bootstrap SHA is bound in the historical plan; full pre-run disk SHA is `c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9`.

P1 export is restricted to `172.16.42.2:10810` on the dedicated USB endpoint. Start USB observation before boot; start NBD and its periodic statistics only after that host address appears, retaining the unchanged client retry behavior. A wildcard `0.0.0.0` export was rejected by automatic approval review before execution and is not authorized (F6-021). No device boot occurred before this revision.

P1 outcome: one bootstrap RAM boot succeeded, but the diagnostic command helper incorrectly expected lk2nd in `version-bootloader`. Actual device read-back is `product: lk2nd-msm8960`, empty version field, same serial `07a117ae` and physical location, USB PID `0xd00d` (`REAL_DEVICE_FACT`). The diagnostic was never booted and no NBD export/connection occurred. P1 is `NOT_EXECUTED / INCONCLUSIVE` and its authorization is consumed. Evidence: `diskless-v2/audits/2026-10-30-P1-preboot/`; F6-022 records the host guard error. This is not a kernel/Android failure.

P2 completed one diagnostic RAM boot and one USB-only NBD session: 1688 completed READ replies, 71,657,472 bytes total, 53,687,296 p1 bytes, zero writes. Its finite hold observations remain valid; `panic_timeout_dependency=SUPPORTED` is REVOKED after the later automatic eMMC transition. Panic auto-restart alone is insufficient to explain the observed sequence, subject to unknown late sysctl changes; the specific cause remains UNKNOWN. Preserve the initial raw report as historical evidence with this correction, not as current acceptance. See P2 phase document, `audits/2026-10-30-P2/` and `audits/2026-10-30-P2-late-transition/`.

P2 exception is consumed and hardware is paused. The current system is eMMC-backed, `sys.boot_completed=1`, ADB root enabled by the user. The inactive P2 server PID 92856 has been stopped. No recovery kernel was booted; planned recovery was cancelled after the intervening eMMC transition. Previous-console capture succeeded through ADB root, with provenance limits above. Current eMMC logcat/bugreport errors must not be used as P2 causal evidence.

Batch H HOST_FACT: exact accepted system root `/fstab.flox` is a regular 4295-byte inode 26, SHA `ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764`, still byte-identical to stock eMMC mapping. Its `/init.flox.rc` calls `mount_all ./fstab.flox --early/--late`; patched vendor is a separate file, not that root file's symlink target. This proves the artifact namespace gap without revoking Phase5's first-stage gate. Evidence/design: `diskless-v2/PHASE6_SECOND_STAGE_FSTAB.md`.

Batch I HOST_FACT: the separate Phase6 derivative now passes deterministic system builds and independent full-byte system/disk/namespace/geometry audits on the Mac. Derived system SHA `d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795`; derived disk SHA `060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a`; manifest SHA `e307d3285e61fc0a4419bdb6a89d672a45792ab65da39bfdddfaa61bed33b3a3`. Exactly 2566 bytes change within the existing 4295-byte root-fstab data; all other bytes compare unchanged, including inode/xattrs/geometry/tables/other partitions. Original sources remain pinned and unchanged; source/derived p1 hashes independently match source/derived system.

At I's host-only checkpoint, the derivative was PROPOSED_DIAGNOSTIC / IMPLEMENTED_UNPROVEN, with no real-device mount/boot PASS or hardware authorization. Kernel, P2 boot image, transport, init handoff and rc stayed fixed. Evidence: `diskless-v2/audits/2026-10-30-root-fstab-derivative/`. J/K/L below complete subsequent preparation and scoped runtime proof. The derivative never silently replaces the accepted clean-system source; original frozen checks stay intact and are composed with its explicit gate.

Batch J: automatic ADB console-first collector is host-tested through simulated disconnect/new boot/root return, including binary preservation and boot-change rejection (HOST_FACT). A current root baseline capture on the unchanged eMMC boot succeeds and preserves the same archived last_kmsg (REAL_DEVICE_FACT about access/current identity only). It does not prove capture during a real reset. Pair the watcher with full USB/NBD observation; first-visible ADB is not automatically first successor and named-run provenance remains independently assessed. See `diskless-v2/PHASE6_V2_AUTOMATIC_CONSOLE_CAPTURE.md`.

Batch K HOST_FACT: composed preflight freshly passes original frozen/P2 gates without weakening the clean-system contract, then separately verifies the precise derivative, disk structure and deterministic derivative-specific trace map SHA `4a70e1c1ceb1933ba840c73b77b67bfcbd1429a2fa2aa360f3381be2856fd90b`. Exact rebuilt boot remains P2 SHA09e277d6...b3119491. Proposed R1 asks whether both p3/cache and p6/persist filesystem READ evidence appears on a single session; this is distinct from the existing OR-based Phase6-E gate and does not prove mounts/full Android startup. Plan, frozen hashes, interpretation/stops and whole-session capture: `diskless-v2/PHASE6_ROOT_FSTAB_RUN_R1.md`. Host evidence: `diskless-v2/audits/2026-10-30-root-fstab-preflight/`. K performed no device commands/exports. Hardware remains PAUSED until a separate committed activation; no new runtime fact is accepted.

**Batch L / R1 conditional one-run activation:** following the user's continued diskless task, completed I/J/K gates and fresh exact-input/current-device readiness checks, this committed design activates only R1's documented sequence: one ADB transition from current rooted eMMC to stock bootloader, one pinned lk2nd RAM boot, and one exact P2 diagnostic RAM boot exporting the explicit root-fstab derivative on USB-only 172.16.42.2:10810. No flash/erase/retry/recovery boot or other experiment is authorized. Require healthy armed console/USB observation before the first transition, actual identity guards between transitions, and all R1 stops/whole-session preservation. Source/plan/launcher hashes and readiness are preserved with the execution batch. Any failed precondition stops; any diagnostic attempt consumes the exception and restores pause. The host gate still correctly says hardware_authorized=no; authorization comes only from this committed design and R1 plan. No new runtime result is accepted at activation.

**L/R1 interim runtime acceptance:** exactly one allowed sequence executed at HEADb872297, diagnostic completed08:10:49.526796UTC. One NBD session established within120s. REAL_DEVICE_FACT: completed READ replies cover both superblock/primary-GDT windows on cache/p3(request721), persist/p6(838), and userdata/p5(943). R1's AND question is YES; Phase6-E advances to PASS for the explicit root-fstab derivative. Snapshot1902 replies includes1875 READs/70,493,184 bytes and27 WRITEs/1,421,312 bytes. This accepts filesystem-read evidence only, not mount success, specific userspace caller, hard late-fs or full Android boot. Golden-source/first-stage contracts stay unchanged; the runtime-written derivative remains distinct.

The request stream later became idle, with gadget still observed and ADB unavailable; this was sufficient to treat startup validation as NOT_PASSED/request-flow stalled, while cause stayed UNKNOWN. User-directed manual successor capture replaced continued passive waiting. R1 permission is consumed and L is now closed as follows.

**L final REAL_DEVICE_FACT:** after the user manually hard-rebooted into eMMC, the armed collector saved117459-byte last_kmsg SHA `86741d43b64d590bde65d1238a752b327519e8b2eca1e4d81d2ea215b1379c4b`, at successor uptime15.57->16.43s with constant boot ID/root. Complete diskless ring head, sole controlled R1 boot/timing and newly corrected NBD mounts distinguish it from the pinned old baseline and establish R1 attribution; generic first-visible ADB is not itself first-successor proof. Console directly proves cache/persist/data NBD mounts successful, early mount_all498ms, late mount_all622ms, post-fs-data and netd/zygote starts. Phase6-F advances to PASS from direct console, not p5 physical reads alone.

The console then records NBD receive -110 at1077.926s, cascading journal/I/O errors and an explicit p5 ext4 kernel panic/stack at1078.293s. This proves the terminal panic, while the initial I/O/communication loss near20s remains UNKNOWN. Existing fsck SELinux denials are separate real errors; mounts succeed afterward, so they are not established as the blocker. Do not bypass the last fsverity_init action, remove errors=panic, or blame netd based only on timing. No automatic panic reboot was observed; the user provided the transition. Full Android startup remains NOT_PROVEN.

After the user entered stock fastboot, same device/port/product were verified and all R1-owned export/observation processes stopped safely. L full evidence/provenance/process-state close: `diskless-v2/audits/2026-10-30-root-fstab-R1/`, `diskless-v2/PHASE6_ROOT_FSTAB_RUN_R1.md`. Runtime-written derivative is evidence, not a pristine retry input. Current device is fastboot, hardware PAUSED/no new boot authorization. Next direction is a single read-only audit of initial I/O-loss boundary/existing transport protection; no runtime fix is selected before that audit. Passive reboot waiting must not be the only console-retrieval path (F6-026).

M SOURCE_PROVEN coverage clarification: the repository-added accepted guards implement USB/PHY power, early system-suspend rejection and gadget selection; they do not add IPv4 address/rule/route/netfilter protection. Accepted Phase4 power/stress facts stay frozen. Exact golden startup files and netd artifact SHA efb13b1f3b33289d85d2091b5c1c2a07d82fce2ee0e0fd02e879dd7bd833dbaf were resolved read-only (HOST_FACT). This is not proof that netd caused R1. Next source/artifact audit asks whether that compiled startup policy removes/bypasses main-table lookup for the original unmarked NBD socket, requiring exact identity linkage before proposing a diagnostic. See `diskless-v2/PHASE6_TRANSPORT_COVERAGE_AUDIT.md`. No runtime/hardware action is authorized by M.

N HOST_FACT: exact netd mini-debug symbols and original-byte Thumb audit establish its startup path flushes rules with nonzero priority, preserving0, then installs priority32000 unreachable on success. Exact ROM source commit is UNKNOWN; reference AOSP is context only. This does not demonstrate R1's runtime route state or prove initial loss cause. It justifies host-only preparation of one diagnostic rule: priority0,to172.16.42.2/32,lookup main, inserted/read back fail-closed before NBD in a separate P2 wrapper derivative. Accepted kernel/USB/NBD/handoff/rc/SELinux mechanisms stay fixed; this new policy is an explicitly proposed diagnostic delta, not a silent change to the frozen wrapper. Use a fresh R1-equivalent disk; no kernel compile or hardware boot is authorized. Require bounded stall handling and prepared successor capture before a run. Evidence/design: `diskless-v2/PHASE6_NETD_ROUTE_AUDIT.md`.

R1 timing clarification: kernel panic is present in the captured console; its independence from manual action remains UNKNOWN. Wall-time/uptime extrapolation and USB timeline differ, but physical button timing is not independently logged and the user is not required to remember it. The long startup/request stall already failed startup validation independently of that question. No new passive-wait phase follows from uncertainty.

O HOST_FACT: separate route image SHA50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799 passes deterministic builds/accepted and exact P2 delta audits; only reviewed root-peer rule/precondition is added before NBD. Fresh disk SHA060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a exactly equals R1 pre-run, independently byte-audited. Offline successor capture is tested and can be armed from verified fastboot. This remains PROPOSED_DIAGNOSTIC/IMPLEMENTED_UNPROVEN, no host-issued hardware permission. Detailed identities/evidence: `diskless-v2/PHASE6_ROOT_ROUTE_PREPARATION.md`. Next is Q1's separately committed one-run plan, with bounded stall decision and prepared successor capture; no kernel compilation needed.

P/Q1 conditional single-use activation, following the user's explicit request to start: only one pinned lk2nd RAM boot from verified current stock fastboot, then one exact O route diagnostic RAM boot with the pristine R1-equivalent disk is authorized after fresh original fact/current image/device checks and armed USB/offline ADB capture. Detailed binary question, identities, interpretations and stops are in `diskless-v2/PHASE6_ROOT_ROUTE_RUN_Q1.md`. Max active observation180s;60s no completed-reply progress leads directly to prepared user-controlled successor capture, not automatic-reboot waiting. No flash/erase/retry or other experiment. Export USB-only; preserve a possibly live NBD root until successor identity verified. Any diagnostic attempt consumes Q1 and restores pause. No runtime result is accepted at activation.

P/Q1 CLOSED/REAL_DEVICE_FACT: target rule marker6.153594s confirms pref0/to172.16.42.2/32/main readback before attach. One session18345 replies,719774720 read bytes/29736960 write bytes,97.950304s successful span,system_server reached. Binary YES; preserve this demonstrated route-protected Phase6 input and root-fstab correction for further isolated work. Original frozen Phase1–5/continuation identities remain unchanged; no post-netd RPDB/exclusive-cause claim.

Controlled successor capture saved130302-byte console SHA43d12aa2ed4bff986198335fa213e81c1c6101303c9d9f7faa6a1d2c35867cae at root/constant boot uptime15.92->16.78. Unique marker/full diskless head/sole Q1 load/USB-user sequence establish attribution. Primary failure is repeated GSS fatal/recovery then subsystem_restart_wq_func powerup panic107.166s. Internal GSS reason UNKNOWN; secondary CPU stopping stacks and later host TCP timeout are not initiating-cause proof. Full Android boot NOT_PROVEN. Device now verified stock fastboot, all Q1 processes stopped, permission consumed/hardware PAUSED. Evidence: `diskless-v2/PHASE6_ROOT_ROUTE_RUN_Q1.md`, `diskless-v2/audits/2026-10-30-root-route-Q1/`. Next: read-only pinned GSS/SSR/firmware audit; no new boot/kernel compile authorized.

Q SOURCE_PROVEN: exact pinned GSS open/SMSM_RESET/SSR powerup-lock-overlap path matches Q1's primary panic independently of NBD. HOST_FACT: exact firmware and GPS HAL identities/entry code audited; internal GSS failure still UNKNOWN. Property-only gps.disable does not guard the HAL C activation entry. Next host-only diagnostic is a four-byte GPS HAL entry replacement returning NULL, temporarily deferring GPS, while preserving Q1 boot/kernel/peer rule/root-fstab/other bytes. Captured subsystem failure justifies this narrowly scoped optional-feature diagnostic; it is not a permanent firmware fix or blanket bypass. Require independent ELF/filesystem/disk byte audits and fresh input. No kernel compile/Android rc edit or hardware boot is authorized. See `diskless-v2/PHASE6_GSS_AUDIT.md`.

R HOST_FACT: GPS-null derivative passes independent ELF/inode/extents/vendor/full-disk gates. Exactly4 bytes change versus pristine Q1; new disk SHA3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811,vendor7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996. Q1 boot/kernel/rc/firmware/route remain byte-identical. This is PROPOSED_DIAGNOSTIC/IMPLEMENTED_UNPROVEN, GPS temporarily unavailable, not normal-feature acceptance. `diskless-v2/PHASE6_GPS_NULL_PREPARATION.md` records hashes/evidence; no hardware authorization or compile from this host batch.

S/Q2 conditional single-use exception: after current gates/identities and armed offline USB/ADB observation,permit one pinned lk2nd and one exact Q1 boot using only R's four-byte GPS-deferral disk. No flash/retry/other boot. Question/outcomes/hashes/stops: `diskless-v2/PHASE6_GPS_NULL_RUN_Q2.md`. Initial180s,one120s extension only while completed I/O progresses,max300s;60s no progress leads to prepared user-controlled successor capture. No automatic-reboot waiting. Preserve live root storage until successor verified,then close/commit. Attempt consumes permission. Runtime remains unproven at activation.

## 16. Q2 accepted desktop milestone / current runtime preservation

Batch S execution HEAD9818dd26774fff4aee3da308a2011b583ec257e6; one lk2nd and one diagnostic RAM boot, no flash/erase/retry. Diagnostic command completed09:59:15.036924UTC on2026-10-30. REAL_DEVICE_FACT: user reached setup, completed normal initialization, then reported desktop without observed crash. At10:12:18UTC, same USB registry4295016541 since09:59:23UTC, one active NBD session,25742 completed replies,818136064 read bytes,89602048 write bytes, successful requests beyond742s. No fallback USB transition observed. Accept core diskless UI startup for this exact profile; no claim of every feature or indefinite crash-free operation.

```text
boot=out/phase6-v2-root-route-O/artifacts/diagnostic.img
boot_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
live_disk=out/phase6-v2-gps-null-R/disk.raw.img
PRE_RUN_disk_sha256=3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811
vendor_sha256=7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996
GPS_HAL_sha256=8cbc55bef118d680651e3a07a15d4d4bae44f7a34608dbcf0c7c4954454b81d9
manifest_sha256=9a040b59379961ce3039575fd459d86052b9760576c7d2523352d1f3d23f20e8
trace_map_sha256=23ba156c7c9859bc83ee03342f07d305e82fd96403613323d72041a954c1c5d9
archive=diskless-v2/audits/2026-10-30-gps-null-Q2/
server_pid=12963;bind=172.16.42.2:10810
idle_sleep_guard_pid=14159;caffeinate=-i -w12963
```

HOST_FACT: sole Q1-to-Q2 pristine disk delta was four GPS HAL entry bytes; kernel/route/root-fstab/firmware/rc/SELinux and other initial partitions stayed fixed. The GPS-unavailable limitation is now explicitly accepted by the user; GPS restoration is optional future work. GSS internal failure cause remains UNKNOWN; no firmware repair or absent activation claim is accepted. No Q2 console or sys.boot_completed readback exists. Direct home observation is the plan's stronger separate boot evidence; its console-specific GSS subcriterion remains NOT_EVALUATED. User-directed successful normal initialization supersedes failed-start capture/reset: do not reboot the working OS merely to obtain last_kmsg.

Current authorization: Q2 boot permission consumed; no new boot/flash/experiment. Preserve USB/Mac/live NBD server and idle-sleep guard. USB/ADB/sampler PIDs12844/12845/12849 have1200s caps; server independently persists beyond their exit. Runtime-written disk includes user setup and is no longer pristine; the hash above is pre-run only. Retain it privately and never overwrite or commit userdata. Phase1–5 remain frozen. Next work: normal feature verification and reproducible packaging of the working GPS-unavailable baseline. Any GApps integration is a separate reviewed image derivative, not authorization to modify live root storage.
