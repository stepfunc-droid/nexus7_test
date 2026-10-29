# Diskless v2 Phase 6 Audit V2 — controlled real-device continuation

Status: **6V2-A/B/C PASSED ON LOCAL HOST — 6V2-D CONTROLLED HARDWARE RUN AUTHORIZED**.

Accepted host results:

```text
DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS
DISKLESS_V2_PHASE6_V2_WRAPPER_SEMANTIC_DIFF=PASS
new_executable_lines=0
p3_p5_p6_content_io_by_supervisor=absent
DISKLESS_V2_PHASE6_V2_CONTINUATION_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_V2_CONTINUATION_HOST_GATE=PASS
DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_MAP=PASS
DISKLESS_V2_PHASE6_V2_NBD_DIFFERENTIAL=PASS
DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_SELFTEST=PASS
DISKLESS_V2_PHASE6_V2_TRACER_HOST_GATE=PASS
```

Accepted continuation image:

```text
out/diskless-v2-android/phase6-v2-continuation.img
sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
```

The image is built with the accepted Phase5D builder and is a subtraction-only continuation of the Phase5D supervisor. It preserves the accepted `/bin/busybox`, `/etc/diskless-v2-layout`, NBD attach/retry, partition validation, and `/init -> /init.android` handoff behavior. HTTP/live-kmsg observer/SIGSTOP behavior is removed; no new executable wrapper line is introduced.

## Preflight

Before every hardware run:

```bash
bash scripts/v2/phase6_v2_real_preflight.sh
```

Required:

```text
DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS
```

The preflight binds the run to the already accepted continuation image bytes, continuation wrapper bytes, accepted/traced NBD server Git blobs, and a deterministic regeneration of the partition trace map.

`serve_disk_phase6_v2_trace.sh` also invokes this preflight automatically and refuses the export if it fails.

## 6V2-D acceptance question

The first hardware question is deliberately narrow:

> Does the Phase5D-derived continuation establish a real oldstyle NBD session and send at least one valid NBD request on exactly one connection?

Host evidence:

```text
connection_open
nbd_first_request
```

The post-run classifier emits:

```text
DISKLESS_V2_PHASE6_V2_D_TRANSPORT_ATTACH=PASS
```

only when exactly one connection is present and exactly one `nbd_first_request` event is recorded for it.

## 6V2-E acceptance question

A stronger next-stage observation uses first-stage-excluded partitions. Pinned Lineage first-stage filters the default fstab to `first_stage_mount` entries; cache, persist, and userdata are excluded from that stage. The continuation wrapper is also audited not to perform content I/O on p3/p5/p6.

Therefore successful filesystem-internal reads of cache or persist metadata on the same NBD connection provide evidence that execution has progressed beyond first-stage and stock SELinux setup into second-stage-or-later Android activity.

Required evidence for either cache or persist is both:

```text
primary ext4 superblock
primary ext4 group descriptor table
```

The classifier emits:

```text
DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=PASS
```

when that condition is met.

## Userdata evidence is observational only

The earlier Audit-V2 draft labeled p5 userdata filesystem evidence as a hard `late-fs` marker. That claim is withdrawn before hardware use.

Root `init.rc` starts `vold` in `early-fs`, before the later `late-fs` trigger. Consequently userdata filesystem I/O may occur before `mount_all --late`; p5 activity cannot by itself prove that `late-fs` was reached.

The classifier therefore reports only:

```text
userdata_filesystem_evidence=OBSERVED|NOT_OBSERVED
late_fs_claim=NOT_PROVEN
```

No 6V2-F PASS is emitted from p5 evidence.

## Observation policy

No Nexus-side kmsg reader, HTTP server, TCP progress marker, Android rc patch, permissive SELinux override, or diagnostic SIGSTOP is used. The Mac NBD server is the only progress observer.

If the hardware run fails before `nbd_first_request`, classify the failure before changing Android. If 6V2-D passes but 6V2-E does not, the next experiment must isolate the interval after NBD attach without broad Android patches.
