# Diskless v2 Phase 6 failure / regression log

Status: **ACTIVE — append-only engineering record**.

Purpose: record every Phase 6 mistake, invalid assumption, false gate, and regression introduced during development. This file is intentionally separate from the design document so that later cleanup does not erase the failure history.

Rule: a Phase 6 gate is not considered trustworthy merely because its builder and auditor agree. Runtime-critical contracts must be independently justified from a previously accepted real-device implementation, pinned source behavior, or an isolated executable self-test.

## F6-001 — `/proc/kmsg` observer was not enforcing-safe

**Symptom**

The enforcing run appeared to stop near SELinux policy load, while the permissive run progressed further.

**Mistake**

A pre-policy BusyBox process reading `/proc/kmsg` was treated as a neutral observer.

**Evidence / root cause**

The permissive run itself showed AVC denial against the BusyBox `/proc/kmsg` reader. Under enforcing the observer could lose visibility even while Android continued.

**Impact**

The early interpretation that enforcing itself blocked second-stage was unsupported.

**Permanent rule**

No Phase 6 acceptance gate may depend on a Nexus-side `/proc/kmsg` reader.

---

## F6-002 — `/dev/kmsg` was assumed to have modern readable semantics

**Symptom**

The new enforcing logger emitted only supervisor handshake lines and no kernel records.

**Mistake**

Modern Linux `/dev/kmsg` per-reader semantics were assumed on the pinned flo Linux 3.4 kernel.

**Evidence / root cause**

Pinned kernel source/documentation shows this `/dev/kmsg` implementation is write-to-printk, not the modern readable cursor interface.

**Impact**

A second invalid observation gate was created and briefly interpreted as Android evidence.

**Permanent rule**

Kernel-interface semantics must be verified against the pinned kernel before introducing a diagnostic mechanism.

---

## F6-003 — `/proc/last_kmsg` availability was treated too strongly

**Symptom**

Recovery attempt returned no usable `last_kmsg` artifact.

**Mistake**

Persistent console availability after a later RAM boot was treated as reliable enough for a hard gate.

**Root cause**

`last_kmsg` is best-effort and can be overwritten/unavailable across later boots.

**Permanent rule**

Persistent crash evidence is useful when present but cannot be the sole Phase 6 acceptance channel.

---

## F6-004 — Android rc files were searched in the boot ramdisk

**Symptom**

Marker builder failed first on missing `/init.rc`, then on missing `/init.flox.rc`; the boot ramdisk contained no `.rc` files.

**Mistake**

The second-stage post-switch-root filesystem view was confused with the boot ramdisk filesystem.

**Root cause**

Lineage second-stage reads `/system/etc/init/hw/init.rc`; flo `init.flox.rc` is installed into `TARGET_ROOT_OUT` and becomes `/init.flox.rc` only after switch-root to system.

**Impact**

The boot-ramdisk rc marker design was architecturally invalid.

**Permanent rule**

Every path used as evidence must be mapped to its actual boot stage and filesystem layer before a builder is written.

---

## F6-005 — permissive evidence was overinterpreted as isolating enforcing

**Symptom**

A diagnostic report initially stated that the enforcing transition had been isolated as the blocker.

**Mistake**

The difference between permissive and enforcing was interpreted without first proving equal observability in both modes.

**Root cause**

The enforcing observer itself was not enforcing-safe.

**Permanent rule**

A/B experiments require an observation channel proven equivalent in both branches before causal conclusions are allowed.

---

## F6-006 — host checker produced a false failure from a comment

**Symptom**

6R1 build failed with `forbidden diagnostic/runtime fragment: httpd` although no executable `httpd` command existed.

**Mistake**

A forbidden-token checker scanned raw source text including comments.

**Root cause**

The word `httpd` appeared only in a comment describing that no HTTP server was used.

**Impact**

No runtime regression, but the gate itself was noisy and brittle.

**Permanent rule**

Static shell checks must distinguish executable shell text from comments; comments may neither satisfy required contracts nor trigger forbidden-runtime checks.

---

## F6-007 — 6R1 changed the proven BusyBox invocation contract and broke PID 1

**Symptom**

First 6R1 real-device boot rebooted within seconds. Mac USB Ethernet never became reachable. The traced NBD server remained listening but saw zero TCP connections and an empty JSONL trace.

**Mistake**

To make the ramdisk layout look cleaner, the accepted transport convention:

```text
/bin/busybox
#!/bin/busybox sh
```

was changed to:

```text
/diskless-busybox
#!/diskless-busybox sh
```

although changing the BusyBox path/name was not required by the Phase 6 goal.

**Evidence / root cause**

BusyBox applet dispatch uses the basename/`argv[0]` name. Its applet dispatcher enters `busybox_main()` only when the invocation name is prefixed by `busybox`; otherwise it attempts to execute the invocation name as an applet. `diskless-busybox` is not prefixed by `busybox`, so the new shebang did not preserve the proven interpreter contract. The supervisor could therefore fail before usb0/NBD setup. PID 1 exit combined with `panic=5` matches the observed rapid reboot.

**Impact**

The previously reported 6R1 host PASS is revoked. 6R2/R3 real-device conclusions were never reached because NBD never connected.

**Permanent rules**

1. Real-device accepted conventions are immutable unless the current problem requires changing them.
2. Phase 6 must reuse the accepted `/bin/busybox` path and `#!/bin/busybox sh` interpreter contract.
3. A host audit must not merely check that the image contains the same path its builder intentionally wrote; runtime-critical interpreter semantics need an independent source/provenance check.
4. Cosmetic/minimal-layout refactors are forbidden during functional bring-up.

---

## F6-008 — 6R1 host gate proved self-consistency, not runtime validity

**Symptom**

6R1 reported all of:

```text
DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS
```

but the first real-device boot failed before any NBD connection.

**Mistake**

The builder and independent auditor shared the same unproven assumption: both explicitly required `#!/diskless-busybox sh` and `/diskless-busybox`. Their agreement was mistaken for runtime validation.

**Root cause**

The gate independently checked bytes and structure, but did not independently validate the semantic contract of the interpreter invocation.

**Permanent rules**

Every new runtime-critical Phase 6 assumption must be classified as exactly one of:

- inherited unchanged from a real-device PASS;
- proved from pinned source;
- proved by an isolated executable self-test.

If none applies, the host gate must FAIL as `UNPROVEN_RUNTIME_ASSUMPTION`.

---

## F6-009 — design drift away from the last known-good supervisor

**Symptom**

The reset attempted to redesign multiple supervisor details at once while claiming to reduce variables.

**Examples**

- BusyBox path/name changed;
- layout path changed;
- NBD launcher style changed from the Phase 5 proven path;
- ramdisk directory layout was optimized for neatness rather than inheritance.

**Mistake**

“Cleaner architecture” was prioritized over delta minimization from the last real-device PASS.

**Permanent rule**

The next 6R1 must be derived by a documented semantic diff against the Phase 5D accepted supervisor. Every difference needs an explicit necessity statement. Unnecessary differences are rejected.

---

## F6-010 — 6R0 PASS mixed observed facts with unproved design requirements

**Symptom**

The first reset audit report contained lines such as:

```text
target_handoff=/diskless-init->exec-/init
handoff_process_contract=pid1-diskless-init-plus-one-nbd-handler-only
rdinit_target=/diskless-init
```

inside a report whose PASS marker primarily revalidated accepted artifacts.

**Mistake**

Artifact/source facts and proposed Phase 6 architecture were reported under one acceptance status.

**Impact**

A reader could incorrectly interpret a host artifact audit as proving the new runtime handoff architecture.

**Permanent rule**

Second-audit reports must separate three classes explicitly:

- `FACT`: inherited/observed accepted evidence;
- `SOURCE_PROVEN`: behavior proved from pinned source;
- `DESIGN_REQUIREMENT`: proposed behavior not yet runtime accepted.

A `DESIGN_REQUIREMENT` can never become true merely because an artifact audit passes.

---

## F6-011 — R2 rc-file extent coverage was over-specified as a hard second-stage proof

**Symptom**

The first R2/R3 design proposed that complete NBD READ coverage of the physical extents for `init.rc` and `init.flox.rc`, after a policy-file read, would prove that second-stage init parsed those files.

**Mistake**

The NBD server observes physical block requests, not the userspace caller or semantic file read. Page cache population, ext4 read-ahead, and nearby block reads can make an extent visible at the NBD layer without proving which userspace operation consumed it.

**Impact**

The tracer implementation and host protocol self-tests remain useful, but the old `DISKLESS_V2_PHASE6_R3_ENFORCING_SECOND_STAGE=PASS` interpretation is revoked until a stage marker with stronger causal isolation is defined.

**Permanent rule**

Host-side block evidence must be tied to a resource that earlier boot stages provably cannot access. Partition-stage isolation is preferred over file-extent inference when available.

---

## F6-012 — Audit V2 trace-map code guessed schema ownership instead of reading the producer

**Symptom**

During host-only implementation of 6V2-C, the first trace-map generator version made two invalid assumptions:

1. it required `filesystem=ext4` in the assembled-disk manifest;
2. it expected realized `start_lba` fields in `layout.json`.

Both assumptions were caught during source re-audit before any host gate or real-device run.

**Mistake**

Fields were inferred from their conceptual meaning instead of checking the code that actually produces each artifact.

**Evidence / root cause**

`assemble_disk.py` shows the ownership split explicitly:

```text
layout.json
    -> logical partition definition, filesystem/source/readonly semantics

assemble_disk.calculate_layout()
    -> deterministic start_lba/sectors calculation

*.manifest.json
    -> realized number/name/start_lba/sectors/size_bytes geometry
```

The manifest intentionally does not duplicate the layout's `filesystem` field, and the source layout intentionally does not contain computed `start_lba` values.

**Impact**

Had this not been caught, 6V2-C would have produced a false host failure even though the disk itself was valid. No Nexus run occurred and no accepted artifact was changed.

**Permanent rules**

1. For every cross-artifact gate, identify the producer code for each field before writing assertions.
2. Do not treat a realized manifest and its source specification as interchangeable schemas.
3. Geometry checks for the v2 disk must recompute layout through the accepted `assemble_disk.calculate_layout()` implementation and cross-check the manifest, rather than inventing duplicate fields.
4. Host-gate implementation itself must be source-audited before it is allowed to gate hardware.

---

## Current acceptance state after Audit V2 host implementation

```text
Phase 1–5      ACCEPTED / FROZEN
6R0             artifact facts retained; runtime-design claims revoked
6R1             REVOKED / FAILED ON REAL DEVICE
6R2 old tools   historical selftests only; old semantic acceptance revoked
6R3             NOT REACHED; old rc-extent proof semantics revoked
6V2-A           IMPLEMENTED / LOCAL HOST RUN PENDING
6V2-B           IMPLEMENTED / LOCAL HOST RUN PENDING
6V2-C           IMPLEMENTED / LOCAL HOST RUN PENDING
6V2-D           NOT AUTHORIZED UNTIL A/B/C PASS ARE REVIEWED
```

No further real-device Phase 6 boot is authorized until the local Mac returns the Audit V2 A/B/C host PASS outputs.

---

## F6-018 — preflight call chain was documented as refreshing facts without invoking the fact gate

**Discovery (2026-10-30 takeover)**

At starting HEAD `cc649ef92886ff2854128c936c58fddfa98f92ee`, both the experiment document and previous batch ledger said the panic-hold real preflight refreshes frozen facts. Static inspection shows it invokes `phase6_v2_real_preflight.sh`, which checks existing reports, selected identities and a reconstructed trace map, but does not invoke `phase6_v2_frozen_fact_gate.sh`. The panic-hold host gate then consumes an existing frozen-fact report. Evidence class: `HOST_FACT` for the inspected local call chain, not device behavior.

**Impact / revoked claim**

The claim that this call chain re-executes the frozen-fact gate is `REVOKED`. A complete current-input preflight cannot be accepted on that assumption. This does not invalidate Phase1–5 acceptance or independently prove any runtime failure.

An existing untracked panic-hold PASS report also names original-host paths. Local wrapper and boot-image audits passed during takeover, but those narrower checks do not establish the old report's execution provenance or rerun its writer scan and deterministic rebuild. Current device execution of that diagnostic is `UNKNOWN`; no hardware command was issued during takeover.

**Correction / next batch**

Authoritative documents now describe the actual implementation and require host-only repair and verification of fresh frozen-fact validation before a complete preflight is accepted. Resolve relocated input paths explicitly. Runtime and host scripts were left unchanged in this documentation/audit batch. Exact local evidence is in `audits/2026-10-30-takeover.txt`.

**Permanent rules**

1. Check the complete executable call chain before claiming that a preflight refreshes a report.
2. An existing PASS marker is not evidence that current-input validation executed in the current batch.
3. Imported reports, newly rerun host checks, and real-device results must be recorded separately.

**Current-state clarification**

The “Current acceptance state after Audit V2 host implementation” section above is historical. Current state: Phase1–5 accepted/frozen; 6V2-A/B/C historical host PASS; 6V2-D real-device transport attach PASS; 6V2-E not reached; Run1 cause `UNKNOWN`; local takeover image/wrapper audits `HOST_FACT`; full preflight repair/revalidation pending; hardware paused and no new real-device run authorized. See `DISKLESS_V2_EXECUTION.md` + `PROGRESS.md`.

---

## F6-019 — Git index inspection through the coordinator's SMB view disagreed with remote Git

**Discovery (2026-10-30 remote-host onboarding)**

The coordinator checkout is an SMB view of `/Users/zhangjw/nexus7_test` on the Mac. After remote commit `29d78b4150a6382ec7d5a7a435e588b390294f2a`, coordinator-side Git read the new HEAD but reported inconsistent staged/unstaged changes; a subsequent status failed with an unrecognized index extension and `fatal: index file corrupt`. Direct remote Git continued to succeed and showed only the original untracked outputs. Remote `.git/index` SHA256 at that check was `2736bdc20134a62c2022e6d83262e02779a9b60e1966b131e3f2fe612c6d606f`.

**Evidence / limit**

These are `HOST_FACT` observations of differing access paths. The filesystem/cache/race mechanism remains `UNKNOWN`; the coordinator error is not proof that the remote repository's index is corrupt. No reset, index rewrite, source overwrite or hardware command was used in response.

**Permanent rule / correction**

Perform Git inspection, status/index operations, staging and commits through SSH on the remote Mac, along with Mac builds and full host validation. Do not alternate Git operations through the SMB view and the remote filesystem or attempt index repair from a coordinator-only error. Coordinator editing and independently staged SCP transfers remain the user-directed workflow.

---

## Resolution 2026-10-30-C — F6-018 current-input validation verified

The panic-hold real preflight now invokes `phase6_v2_frozen_fact_gate.sh` and requires its fresh PASS output before any base-preflight/diagnostic gate. It binds disk/manifest identities across children, scopes the fact report separately from the diagnostic report, and routes continuation/diagnostic image overrides independently.

`HOST_FACT`: isolated orchestration tests reject stale PASS reports on frozen-gate failure, absent fresh marker and base-preflight failure; the successful custom-path case executes in frozen/base/host order. A real frozen-gate missing-input check also exits 1 without producing a diagnostic image or final PASS despite an old fact PASS report.

Complete real-input validation on the remote Mac passed with exit 0: fresh frozen facts, continuation A/B builds and independent audit, tracer differential/partition self-tests, accepted-image writer scan, diagnostic A/B builds/audits and repaired complete preflight. New raw stdout/stderr and identities are preserved under `audits/2026-10-30-f6018-host/`.

F6-018 implementation/host-verification gap is closed. Its historical mistake and permanent rules remain above. No new real-device fact, runtime mechanism or reset-cause inference follows; every current host PASS still says `hardware_authorized=no`. The nonliteral/programmatic sysctl writer limitation remains.

---

## F6-020 — host USB inspection initially assumed a list-root plist

During preparation D, the first read-only ioreg inspection helper attempted list traversal of a dictionary-root plist and failed before any device boot. The actual macOS plist root was inspected; the committed observer now handles both dictionary and list roots, verified by a self-test and an actual USB dry run (`HOST_FACT`).

Permanent rule: inspect the actual producer's data shape before treating a host observer as an experiment precondition. An observer parse failure means missing evidence, never a device reset or liveness fact. This did not invalidate any hardware result; no P1 boot had occurred.

---

## F6-021 — proposed wildcard RW export exceeded the required destination scope

Automatic approval review rejected P1's initial listener-start action because a read-write export bound to `0.0.0.0` could expose the backing disk to other reachable clients. The tool action was rejected before execution; no listener, observer process or device boot was started by that action. This was an experiment-host exposure issue, not a Nexus failure.

The safer procedure is now explicit: observe USB before boot, wait for the dedicated `172.16.42.2` host endpoint, bind the RW export only there, then collect SIGUSR1 snapshots. The accepted client retry behavior remains unchanged. No management/wildcard listener is authorized. A missing endpoint/listener/attach remains INCONCLUSIVE; do not widen the bind address to make a failed precondition pass.

Permanent rule: scope diagnostic exports to the required transport destination before executing them. Prior script defaults are not authorization for broader read/write exposure.

---

## F6-022 — host lk2nd identity guard assumed a nonempty version field

P1's bootstrap RAM boot succeeded and the same serial/physical USB port reenumerated at PID `0xd00d`. The helper only probed product after finding “lk2nd” in `version-bootloader`; the actual version field is empty, while product is `lk2nd-msm8960`. Its guard therefore timed out without launching the diagnostic. Direct read-back confirmed the real fields (`REAL_DEVICE_FACT`). No diagnostic kernel, NBD export or reset experiment ran.

P1 was closed and hardware pause restored; the device remains in lk2nd fastboot. A future attempt must verify the actual product plus serial/physical USB identity and exact loaded-artifact provenance, without assuming the stock product or a version string is retained. Do not repeat a bootstrap merely to satisfy a faulty host predicate. Record the tool failure separately from device/kernel failures.

---

## F6-023 — finite idle window was accepted before the later boot identity was resolved

P2's NBD/USB observations met the proposed >=90s hold rule and were prematurely accepted as panic-timeout dependency support. Later the device automatically returned to eMMC. ADB availability/boot animation was initially discussed before the backing mounts/current kernel identity were checked. The support claim is REVOKED; finite hold data alone did not establish the reset mechanism. Current eMMC success is not diskless success.

Permanent rules: preserve raw observations but verify the later kernel/boot ID/cmdline/storage identity before causal or boot-success acceptance. A finite idle/no-reenumeration interval is not exclusive panic evidence; continue observation through the relevant terminal transition or leave the causal result UNKNOWN. Do not use current eMMC crashes as previous diskless-run evidence.

Subsequent root capture retrieved a prior NBD console after the user enabled rooted debugging. Its ring head is missing and exact P2 attribution remains qualified; old cached recovery logs were rejected. Explicit source/runtime identity and provenance limits remain mandatory even when content looks relevant.

## F6-024 — first-stage fstab audit did not establish the second-stage namespace

The captured previous NBD console shows second-stage `mount_all ./fstab.flox` waiting for/skipping eMMC cache/persist/userdata paths, then read-only data failures. This is not contradicted by Phase5's proven first-stage p1/p2 mounts or correct boot/vendor fstab bytes. Those gates did not prove the post-SwitchRoot root file consumed by later init.

Current correction is host-audit direction only: inspect the exact accepted system root fstab and caller namespace. Keep the first-stage/transport/kernel mechanisms frozen. Do not claim a second-stage mount contract merely because an identically named boot/vendor file is patched, and do not bypass BoringSSL or the last visible failure line as a substitute for fixing a demonstrated earlier mismatch.

---

## F6-025 — historical experiment headings still looked like current selection

Before R1 activation, the total design's detailed P1/P2 section still said Selected next experiment, while the latest checkpoint/§15 already selected the root-fstab direction and consumed P1/P2. No transition was issued against that ambiguity. The headings/table and historical enumeration were explicitly scoped as P1/P2 history, and the current blocker/activation now point to R1. This is a documentation defect, not a device failure or new runtime fact.

Permanent rule: when experiment direction changes, reconcile current-selection headings and summaries in the project-wide authority as well as appending new evidence. Preserve old designs as clearly labelled history; never use an old gate's binary question or permission marker as current run authorization. HOST_PASS remains separate from committed design authorization.

---

## F6-026 — passive automatic-reboot waiting remained the only active console path

R1 had already answered its p3-AND-p6 question and stopped normal request progress. Although observation had a2100s cap, the agent continued passive waiting for an automatic fallback as the only active route to console evidence. The user correctly distinguished a sufficiently long startup stall from the still-unknown cause, then rejected continued waiting and chose a manual hard reboot. An already-armed collector saved the NBD console at successor uptime15.57s before later eMMC instability, demonstrating the value of prepared capture rather than waiting for a spontaneous transition.

Permanent rule: define a bounded startup-stall decision separately from reset/cause classification, and prepare an actionable controlled-successor/live-console route before the next hardware run. A recording cap is not a requirement to remain passive until it expires. A finite stall can justify failed startup validation without proving panic, watchdog or transport cause. User-directed transitions override the proposed route and must be recorded for provenance. Preserve exact previous-console bytes first; do not bypass the last visible init action or final panic as a substitute for locating initial I/O loss.

---

## F6-027 — precision of user keypress recall is not a diagnostic prerequisite

After user asked whether the captured late panic coincided with hard reboot, the agent calculated wall/uptime/USB times but then asked the user to recall a precise16:28-vs16:33 button time. That was an unreasonable burden and distracted from the established long startup stall. Preserve the host timing and mark panic/manual-action independence UNKNOWN; do not require the user to reconstruct minute-level events, weaken the failed-startup assessment, or use uncertainty to justify more passive waiting. Future experiments must obtain required timing automatically or prearrange a controlled transition.

## F6-028 — ARM ELF disassembly needs actual instruction-mode and symbol validation

The first netd LLVM dump defaulted to ARM mode for Thumb code and displayed nearest exported C++ symbols unrelated to the local function. It was rejected before any static behavior was accepted. The exact executable's embedded GNU mini-debug symbols established function ranges, and explicit thumbv7 decoding plus original-byte branch/vtable checks established the actual code. Treat wrong-mode/nearest-symbol output as unusable; neither a plausible string nor an unrelated printed label is an exact-artifact call-chain proof.

## F6-029 — primary panic origin differs from other CPUs' stopping stacks

Q1's primary panic originates in subsystem_restart_wq_func after repeated GSS failure during recovery. Another CPU was interrupted in qtaguid/TCP/NBD receive and printed its stopping stack. Those frames do not establish the panic cause. Use the explicit panic message/emitting stack first; later host timeout cannot supersede it. Preserve demonstrated route progress while isolating the new GSS blocker.

## F6-030 — isolated installer environment and output channels need independent preflight

Phase7 host-only preparation U exposed three disposable-VM issues before any new Nexus boot. A's minimal guest lacked the CRC32C provider required by new installer-media ext4 checksums; the explicit mount error stopped before GApps. B could execute ARM directly but update-binary's external uname still resolved to native x86, selecting a nonexistent helper. C installed with exit0 but sharing UI /proc/self/fd/1 with ordinary file stdout caused offsets/append writes to overwrite UI records; the independent auditor rejected missing completion evidence. These are HOST_FACT about the host preparation, not Nexus/GApps runtime failures. Sources/candidates/logs retained separately; none accepted from QEMU exit0 alone.

Corrections: explicitly include/load the actual crypto module dependency; require binfmt-mediated ARM applet execution and recovery PATH before the exact installer; separate its UI control FD3 from stdout/stderr and preserve both. Keep the original ZIP/installer unchanged and audit actual file content/metadata/filesystem after installation. Missing channels or a successful process exit never substitutes for complete artifact gates. No frozen Nexus mechanism was altered in response.

## F6-031 — copied-file labels do not cover installer-created parents and symlinks

U's exact original installer D completed/exit0; initial35 listed-file checks passed. Expanded directory checking found new /system/app/LatinIME parents and keyboard symlinks without SELinux xattrs in the isolated Linux guest. The initial report is REVOKED as a complete GApps-image acceptance gate; its listed-file observations remain HOST_FACT. No new Nexus boot occurred. Unlike recovery with Android SELinux policy loaded, this guest did not compute Android create-time labels; original script chcon calls do not cover every node.

Final correction uses a separate D clone, libselinux lookup against exact ROM plat_file_contexts and explicit per-inode xattr writes only for installer-added/changed nodes. Independent consumer checks corresponding target rule classes and read-back for files, directories, and symlinks; system/lib uses system_lib_file, product overlays vendor_overlay_file. Keep policy/enforcing/kernel untouched. A prior PASS report is retained as history and invalidated at the start of a rerun; consumer never accepts a stale PASS after an expanded gate fails. This is host packaging metadata restoration, not a device subsystem bypass.

U amendment: E's initial physical /system/product lookup selected a generic Linux /system match for PlayStoreOverlay; independent explicit-overlay gate rejected it. The exact root filesystem proves /product -> /system/product, and target rules explicitly cover both namespaces. Product lookups now use /product; independent consumer still checks physical path labels. E/F are rejected preparatory candidates, not accepted final artifacts. No policy bytes changed.

## F6-032 — optional GApps keyboard aliases can be unresolved on the exact SAR layout

Expanded F audit found three new optional keyboard symlinks with missing targets, despite original installer exit0. Exact supplied installer and file tree establish the cause: default swypelibs branch adds both legacy /system and /system/product aliases, while this package supplies only one gesture library and no keyboarddecoder target. Do not accept all exit0-generated links or patch nonexistent libraries into the ROM by guesswork. Select the original installer's skipswypelibs configuration, retain AOSP keyboard and re-run on fresh p1, then audit all new/changed symlink resolution/labels. This omits optional gesture libraries only; no Google core service or device subsystem bypass. No Nexus boot used these rejected candidates.

## F6-033 — host launcher rejected the documented relative-path invocation

HOST_FACT: armed run20261030T133135-560727Z/PID22550 is live as Python nexus7.py serve disks/daily.raw.img, but boot() requires the absolute ROOT/nexus7.py in ps output. Thus the documented relative invocation is incorrectly rejected. No10810 listener yet is expected before the gadget appears. Host identification defect, not missing user setup/device failure. Workaround is absolute script/disk paths for serve. User cancelled script refactoring; no script/image/server mutation or hardware boot during this audit. Future gates must positively exercise documented invocations as well as negative cases.

## F6-034 — public operational entrypoints were incomplete and inconsistent across releases

Users were asked to supply internal Python subcommands/disk paths, while saved Q2 and GApps scripts exposed different commands. User's Q2 stop-nbd consequently failed at argument parsing; adding only start-nbd.sh still left stop and device start inconsistent. Provide all three no-argument entrypoints in both releases, synchronize the supported host backend/USB helper, and verify wrapper arguments plus CLI support. Preserve image hashes and the fastboot-before-root-stop guard. Do not call an archive operationally complete merely because ROM bytes were copied successfully.
