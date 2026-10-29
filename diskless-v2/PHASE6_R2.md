# Diskless v2 Phase 6R2/R3 — host-side NBD enforcing/second-stage trace

Status: **6R2 HOST GATE PASSED — first controlled real-device trace run authorized**.

Prerequisites accepted:

```text
DISKLESS_V2_PHASE6_R0_HOST_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS
DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS
DISKLESS_V2_PHASE6_R2_TRACE_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_SERVER_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_HOST_GATE=PASS
```

## Purpose

The abandoned first Phase 6 attempt tried to observe Android progress from Nexus-side `/proc/kmsg`, `/dev/kmsg`, HTTP and rc markers. Those observers either became blind under SELinux, assumed modern kernel semantics that Linux 3.4 does not have, or modified the system being observed.

6R2/R3 therefore uses only the Mac-side NBD server as the observer.

The accepted 6R1 image contains no Nexus-side progress logger and no Android rc modification.

## Source-proven ordering

LineageOS 18.1 first-stage executes:

```text
/system/bin/init selinux_setup
```

after the first-stage mounts and switch-root.

`SetupSelinux()` then performs:

```text
SelinuxInitialize()
    -> LoadPolicy()
    -> security_setenforce(1)       # stock enforcing baseline
restorecon /system/bin/init
exec /system/bin/init second_stage
```

Second-stage init subsequently reads its configuration, including the platform init rc and flo device rc.

Therefore the following host-observed file-data order is an enforcing barrier without any Nexus-side marker:

```text
1. /vendor/etc/selinux/precompiled_sepolicy
       complete read while LoadPolicy() is executing
       |
       v
   security_setenforce(1)
       |
       v
2. /system/etc/init/hw/init.rc
       second-stage-only configuration read
       |
       v
3. /init.flox.rc
       imported flo second-stage device configuration
```

The exact filesystem paths inside the raw ext4 source images are resolved host-side; the trace map records the resolved raw-image paths and physical extents rather than assuming them.

## Why `/system/bin/init` is not a marker

`/system/bin/init` is executed twice:

1. first-stage -> `selinux_setup`, before enforcing is enabled;
2. `SetupSelinux()` -> `second_stage`, after enforcing is enabled.

A host read of the init binary alone cannot distinguish those executions. It is intentionally excluded as the post-enforcing acceptance marker.

## Host trace-map generation

`scripts/v2/prepare_phase6_r2_trace.py` uses the dependency-free read-only ext4 resolver in:

```text
scripts/v2/ext4_readonly.py
```

For each marker it:

- resolves the path through the real ext4 directory/inode tree;
- follows ext4 symlinks when necessary;
- parses extent trees;
- reconstructs the exact file bytes;
- maps each file logical range to an absolute byte range in the combined NBD disk;
- verifies those ranges byte-for-byte against the accepted source image and assembled Android disk;
- requires dense coverage of the complete marker file.

No filesystem is mounted and no image is modified.

Output:

```text
out/diskless-v2-android/phase6-r2-trace-map.json
```

Accepted marker:

```text
DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS
```

## Independent traced NBD server

Phase 3/4's accepted `scripts/nbd_test_server.py` is not modified.

6R2 uses the separate:

```text
scripts/v2/nbd_trace_server.py
```

It implements the same oldstyle NBD request/reply path and additionally records marker coverage after successful READ replies. Trace output is append-only JSONL.

A marker completes only after READ replies on the same connection have covered every logical byte of that marker file according to the validated trace map.

## Host-only self-tests — PASSED

`scripts/v2/phase6_r2_host_gate.sh` passed all host-only checks:

1. real ext4 path/inode/extent resolution;
2. byte verification of every marker extent against the assembled disk;
3. coverage/order unit self-test;
4. localhost oldstyle-NBD end-to-end test;
5. byte-for-byte validation of every returned localhost NBD READ payload;
6. validation that marker completion order is exactly 1 -> 2 -> 3 on one connection.

Accepted host-only markers:

```text
DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS
DISKLESS_V2_PHASE6_R2_TRACE_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_SERVER_SELFTEST=PASS
DISKLESS_V2_PHASE6_R2_HOST_GATE=PASS
```

The hardware pause is now lifted only for the controlled traced run described below.

## Controlled real-device run

Launch the traced server with:

```text
scripts/v2/serve_disk_trace.sh
```

It writes:

```text
~/phase6-r2-nbd-trace.jsonl
```

The real-device run must use the already accepted:

```text
out/diskless-v2-android/phase6-r1-full-boot.img
```

No new boot image is created for 6R2/R3.

After the run, the host trace is evaluated by:

```text
scripts/v2/phase6_r2_trace_gate.py
```

It requires exactly one NBD connection and the exact completion sequence:

```text
pre_enforce_vendor_precompiled_sepolicy
post_enforce_second_stage_init_rc
post_enforce_flox_rc
```

If accepted, the run yields two logical gates from one unmodified boot:

```text
DISKLESS_V2_PHASE6_R2_TRANSPORT_AFTER_ENFORCING=PASS
DISKLESS_V2_PHASE6_R3_ENFORCING_SECOND_STAGE=PASS
```

Interpretation:

- 6R2 PASS proves the same single NBD connection continues successfully from pre-enforcing policy load into post-enforcing block reads;
- 6R3 PASS proves stock enforcing Android actually entered second-stage and parsed both platform and flo rc configuration;
- neither conclusion depends on a Nexus-side logger, permissive mode, Android rc modification, or a second NBD connection.
