# Diskless v2 Phase 6R1 — first reset design (REVOKED)

Status: **REVOKED — REAL-DEVICE FAILURE BEFORE NBD CONNECTION**.

This document is retained as failure history. It is superseded by:

```text
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
```

The old host gate reported:

```text
DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS
DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS
DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS
```

Those markers are **revoked** as acceptance results.

The first real-device boot of `phase6-r1-full-boot.img` rebooted before USB reachability/NBD attach. The Mac traced NBD server saw no connection at all.

The reset had unnecessarily changed the Phase5D real-device-proven BusyBox contract:

```text
/bin/busybox
#!/bin/busybox sh
```

to:

```text
/diskless-busybox
#!/diskless-busybox sh
```

BusyBox source confirms that multicall dispatch depends on the invocation basename. This was a runtime-critical regression that the builder and auditor both encoded as a required condition, so their agreement only proved self-consistency around the same wrong assumption.

Audit V2 also rejects the broader `rdinit=/diskless-init` redesign as unnecessary. Phase5D already proved the wrapper `/init -> /init.android` first-stage path on the real device, and Lineage first-stage subsequently execs `/system/bin/init selinux_setup`; the boot-ramdisk name does not need to be redesigned for Phase 6 continuation.

The old artifact:

```text
out/diskless-v2-android/phase6-r1-full-boot.img
```

is **REJECTED — DO NOT BOOT**.

Replacement Phase 6 work must be derived as a semantic subtraction from the accepted Phase5D supervisor, preserving `/bin/busybox`, `/etc/diskless-v2-layout`, NBD launch/retry behavior, device setup, and first-stage handoff conventions unless a demonstrated failure requires a change.
