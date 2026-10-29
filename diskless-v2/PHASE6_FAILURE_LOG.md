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

**Root cause**

BusyBox is a multicall binary whose invocation behavior depends on `argv[0]` / basename. The accepted implementation invoked the binary as `busybox`; the 6R1 redesign introduced an unvalidated basename `diskless-busybox`. The supervisor therefore could fail before usb0/NBD setup. PID 1 exit combined with `panic=5` matches the observed rapid reboot.

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

## Current acceptance state after F6-007

```text
Phase 1–5      ACCEPTED
6R0 artifacts  useful evidence, but audit methodology under re-review
6R1            REVOKED / FAILED ON REAL DEVICE
6R2 host tools host-self-tested only; no real-device 6R2 result
6R3            NOT REACHED
6R4            NOT STARTED
```

No further real-device Phase 6 boot is authorized until the second audit closes F6-009 and a replacement 6R1 gate is built from unchanged Phase 5 runtime conventions.
