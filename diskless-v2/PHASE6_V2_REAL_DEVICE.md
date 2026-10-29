# Diskless v2 Phase 6 Audit V2 — controlled real-device continuation

Status: **6V2-A/B/C PASSED — 6V2-D REAL-DEVICE TRANSPORT ATTACH PASSED — 6V2-E NOT REACHED**.

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

The controlled hardware run started only after:

```text
DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
accepted_nbd_server_git_blob=6e7ce821c98f3c4f7a4ff4c337a20a4297c2bfd8
traced_nbd_server_git_blob=8046084119a1c12a72465b87d5afb450a2071311
partition_trace_map=deterministic-match
6V2_B_report=PASS
6V2_C_report=PASS
hardware_boot_permitted=controlled-6V2-D-only
```

`serve_disk_phase6_v2_trace.sh` also invoked the same preflight before exporting the disk.

## 6V2-D — PASS

The traced NBD server accepted exactly one connection from the Nexus and then received a real NBD request after the oldstyle handshake:

```text
client 172.16.42.1:46433 connected
TRACE event=connection_open connection=1 peer=172.16.42.1:46433
TRACE event=nbd_first_request connection=1 request=1 cmd=READ offset=0 length=4096
```

The real-trace classifier reported:

```text
DISKLESS_V2_PHASE6_V2_D_TRANSPORT_ATTACH=PASS
connection=1
single_nbd_connection=PASS
first_request=1
first_request_cmd=READ
connection_close_reason=still-open-or-not-captured
transport_close_classification=no-close-event
```

Accepted interpretation:

- the Phase5D-derived continuation supervisor executed far enough to configure the USB network and launch the inherited NBD client path;
- the oldstyle NBD handshake completed;
- the kernel issued a real block request on `/dev/nbd0`;
- the previously revoked 6R1 failure mode (reboot before any NBD connection) is not present in this continuation image.

The first request was `READ offset=0 length=4096`; this is disk-header / partition-discovery traffic and is **not** Android stage evidence.

## 6V2-E — NOT REACHED

At the first post-run classification point, neither cache nor persist had completed the accepted filesystem evidence condition:

```text
DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=NOT_REACHED
```

No conclusion is permitted yet about whether Android is:

- still performing first-stage / p1/p2 work;
- blocked in first-stage after transport attach;
- blocked during SELinux setup;
- in second-stage before `fs` processing;
- or simply waiting on another subsystem.

The NBD connection had not closed, so transport failure is also not established.

The next binary question is therefore host-only and non-invasive: determine whether this already-established NBD connection is still carrying traffic or has become idle. Do not reboot or modify the running image before answering that question.

## 6V2-E evidence rule

Pinned Lineage first-stage filters the default fstab to `first_stage_mount` entries; cache, persist, and userdata are excluded from that stage. The continuation wrapper is audited not to perform content I/O on p3/p5/p6.

Successful filesystem-internal reads of cache or persist metadata on the same NBD connection therefore provide evidence that execution has progressed beyond first-stage and stock SELinux setup into second-stage-or-later Android activity.

Required evidence for either cache or persist is both:

```text
primary ext4 superblock
primary ext4 group descriptor table
```

Only then may the classifier emit:

```text
DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=PASS
```

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
