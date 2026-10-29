# Diskless v2 Phase 6 Audit V2 — host-only gates

Status: **IMPLEMENTED — LOCAL HOST RUN PENDING — HARDWARE PAUSED**.

This document is the executable contract for Audit V2 gates 6V2-A/B/C.  These
gates perform no Nexus boot.  A real-device continuation is not authorized until
all three host gates pass on the Mac that owns the accepted build artifacts and
Android-test disk.

## 6V2-A — frozen Phase1–5 facts

Run:

```bash
cd ~/nexus7_test
git pull
bash scripts/v2/phase6_v2_frozen_fact_gate.sh
```

Required final marker:

```text
DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS
```

Report:

```text
out/diskless-v2-android/phase6-v2-frozen-facts.txt
```

This gate revalidates only accepted artifact facts.  It intentionally does not
inherit the old 6R0 runtime-design claims.

## 6V2-B — Phase5D semantic-diff continuation image

Run only after 6V2-A passes:

```bash
bash scripts/v2/phase6_v2_continuation_host_gate.sh
```

Required markers include:

```text
DISKLESS_V2_PHASE6_V2_WRAPPER_SEMANTIC_DIFF=PASS
new_executable_lines=0
p3_p5_p6_content_io_by_supervisor=absent
DISKLESS_V2_PHASE6_V2_CONTINUATION_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS
```

Output image:

```text
out/diskless-v2-android/phase6-v2-continuation.img
```

The image is built with the exact Phase5D image builder.  The continuation
wrapper is accepted Phase5D executable code with the HTTP/live-kmsg/observer
/SIGSTOP path removed; no new executable shell line is allowed.

Important: the old Phase5D builder still prints its historical descriptive line
`late_android_boot=intentionally-stopped-after-first-stage-mounts`.  Audit V2
does **not** use that string as an acceptance fact.  The semantic-diff gate
proves directly that the continuation wrapper contains no SIGSTOP gate.

## 6V2-C — traced-server differential and evidence semantics

Run only after 6V2-B passes:

```bash
bash scripts/v2/phase6_v2_tracer_host_gate.sh
```

Required markers include:

```text
DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_MAP=PASS
DISKLESS_V2_PHASE6_V2_NBD_DIFFERENTIAL=PASS
rw_handshake_and_replies=byte-identical
readonly_handshake_and_replies=byte-identical
DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_SELFTEST=PASS
nbd_first_request_single_shot=PASS
superblock_plus_primary_gdt_required=PASS
DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS
```

Report/map:

```text
out/diskless-v2-android/phase6-v2-tracer-host-audit.txt
out/diskless-v2-android/phase6-v2-partition-trace-map.json
```

The differential self-test pins the accepted Phase3/4 `nbd_test_server.py` Git
blob and compares the traced server against it for read-write and read-only
exports.  Covered protocol paths are:

```text
READ
WRITE
WRITE+FUA
FLUSH
TRIM
invalid READ
invalid WRITE
unsupported command
DISC
```

Handshake/reply bytes and final backing-image bytes must be identical.

## Partition evidence semantics

Audit V2 no longer treats p1/p2 rc-file extent coverage as proof that init parsed
a file.

The trace map is derived from `layout.json` through the same accepted
`assemble_disk.calculate_layout()` algorithm used to build the disk, and then
cross-checked against the realized disk manifest and on-disk ext4 superblocks.

First-stage source/fstab audit proves that these partitions are excluded from
first-stage mounting:

```text
p3 cache
p6 persist
p5 userdata
```

The continuation supervisor may inspect their geometry through
`/proc/partitions`, but the 6V2-B gate forbids it from performing filesystem
content I/O on p3/p5/p6.

A host-side stage event therefore requires successful NBD READ replies on the
same connection covering both independent ext4 metadata windows:

```text
primary superblock
primary group descriptor table
```

A read of the MBR/EBR, a generic read merely inside a partition range, or a
superblock-only read is not enough.

Interpretation reserved for the later real-device run:

```text
nbd_first_request
    -> 6V2-D transport attach evidence

p3(cache) OR p6(persist) superblock+GDT on same connection
    -> 6V2-E stock enforcing Android reached second-stage fs processing

p5(userdata) superblock+GDT after 6V2-E
    -> 6V2-F progressed into late-fs userdata processing
```

## Host-audit bugs caught before hardware

During implementation of 6V2-C, two incorrect schema assumptions were caught
before any device run:

1. `diskless-v2.raw.img.manifest.json` does not own a `filesystem` field;
   filesystem semantics come from `layout.json`.
2. `layout.json` does not contain realized `start_lba`; those values are computed
   by `assemble_disk.calculate_layout()` and recorded in the manifest.

The final map generator therefore uses:

```text
layout.json                       semantic source of truth
assemble_disk.calculate_layout() deterministic geometry calculation
*.manifest.json                  realized geometry cross-check
raw disk ext4 superblock         on-disk filesystem cross-check
```

## Stop condition

After A/B/C pass, stop and return their output.  Do not boot
`phase6-v2-continuation.img` yet.  The controlled 6V2-D commands are issued only
after those local host results have been reviewed.
