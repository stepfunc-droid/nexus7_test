# Diskless v2 Phase 6 — Android boot integration

Status: **PAUSED — prior Phase 6 implementation superseded by `PHASE6_AUDIT.md`**.

Phase 5 remains accepted. No Phase 6 acceptance gate has passed.

The earlier version of this document described a live-kmsg based second-stage gate. That design is retired because the audit established that:

- a pre-policy BusyBox `/proc/kmsg` reader can lose access when SELinux enforcing becomes active;
- the pinned Linux 3.4 flo kernel does not provide modern readable `/dev/kmsg` semantics;
- `/proc/last_kmsg` is useful only when available and cannot be the sole Phase 6 acceptance source;
- Android rc files used by second-stage are not stored in the Phase 6 boot ramdisk as the abandoned marker experiment assumed;
- the experimental Phase 6 builder unnecessarily renamed stock `/init` to `/init.android`, despite the pinned kernel supporting `rdinit=`;
- long-lived pre-policy processes, especially the required NBD client, need an explicit SELinux lifetime audit before enforcing boot behavior can be interpreted.

The authoritative Phase 6 document is now:

```text
diskless-v2/PHASE6_AUDIT.md
```

## Accepted inheritance from Phase 5

Phase 6 starts from the accepted Phase 5 state and must not alter these identities:

```text
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
```

Phase 5D already proved on real hardware:

```text
/system = /dev/block/nbd0p1
/vendor = /dev/block/nbd0p2
same single NBD kernel session across first-stage handoff
original Lineage first-stage init
no v1 Android rc bypasses
```

## Reset sequence

Phase 6 resumes only in this order:

```text
6R0 host/source architecture audit
  -> 6R1 clean rdinit=/diskless-init supervisor artifact
  -> 6R2 prove NBD survives SELinux enforcing
  -> 6R3 observe stock enforcing second-stage without Android modification
  -> 6R4 continue to first genuine late-boot blocker
```

Do not boot another Phase 6 image until 6R0 and 6R1 are complete and audited.
