# Diskless v2 Phase 6R2/R3 — first host-trace design (SEMANTICS REVOKED)

Status: **TOOL SELFTESTS PASSED; REAL-DEVICE 6R2 NOT REACHED; R3 PROOF SEMANTICS REVOKED**.

Superseded by:

```text
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
```

The host tooling did successfully self-test these mechanics:

```text
DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS
DISKLESS_V2_PHASE6_R2_TRACE_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_SERVER_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_HOST_GATE=PASS
oldstyle_nbd_handshake=PASS
read_payload_byte_validation=PASS
```

Those results mean only that the trace-map, oldstyle NBD server, payload return path, and JSONL coverage machinery worked in host-only tests.

They do **not** constitute a real-device 6R2 result. The first hardware run used the now-rejected old 6R1 image and rebooted before any NBD connection. The trace log was empty and contained zero `connection_open` events.

The original R3 interpretation is also revoked. It treated complete physical NBD READ coverage of the extents backing:

```text
/vendor/etc/selinux/precompiled_sepolicy
/system/etc/init/hw/init.rc
/init.flox.rc
```

as a hard semantic proof that second-stage init parsed those files. The NBD server observes block requests, not the userspace caller. Page-cache population, filesystem readahead, or adjacent reads can cover a file's physical extents without proving which userspace operation consumed the data.

Therefore the old gate must no longer emit:

```text
DISKLESS_V2_PHASE6_R3_ENFORCING_SECOND_STAGE=PASS
```

from rc-file extent coverage.

Audit V2 identifies a stronger future host-side boundary based on partition-stage isolation:

- first-stage fstab filtering retains only `first_stage_mount` entries, which are system p1 and vendor p2;
- cache p3 and persist p6 are non-late second-stage `mount_all --early` filesystems;
- userdata p5 is `latemount` and belongs to the later `mount_all --late` path;
- the replacement transport wrapper must itself never read filesystem contents inside p3/p5/p6.

Once those invariants are independently gated, filesystem-internal I/O inside p3/p6 on the same NBD connection is a causally stronger indication of post-SELinux second-stage `fs` processing, and p5 activity is a later-stage marker.

The existing `ext4_readonly.py`, trace-map code, and NBD trace server remain experimental host tooling and may be reused after their acceptance semantics are redesigned. No hardware run is currently authorized.
