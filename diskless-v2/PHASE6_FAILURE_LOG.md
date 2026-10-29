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
