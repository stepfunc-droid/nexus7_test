# Diskless v2 implementation progress

This file records implementation state and issues encountered while executing `DISKLESS_V2_EXECUTION.md`.

## Phase 1 — deterministic diskless kernel

Status: **PASSED**.

Accepted invariants:

- kernel source pinned to LineageOS flo commit `0da5107137f93b8d8f697e949ab0784f5ace450c`;
- pristine `lineageos_flo_defconfig` loaded from the pinned commit;
- `ARCH=arm` explicit;
- `CONFIG_BLK_DEV_NBD=y`;
- `CONFIG_USB_ETH=y`;
- `CONFIG_USB_G_ANDROID=n`;
- persistent RAM / Android ram console enabled;
- SDCC1/eMMC registration disabled and verified;
- LineageOS ARM GCC 4.9 pinned at `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`;
- kernel/config/toolchain/zImage identities recorded in a manifest;
- unknown tracked kernel source modifications fail closed.

Resolved issues:

- **P1-001:** historical working-tree defconfig contamination. v2 reads the pristine pinned git object.
- **P1-002:** Linux 3.4 lacks `olddefconfig`; v2 uses `oldnoconfig` plus invariant checks.
- **P1-003:** Debian GCC 12 is incompatible with this tree; v2 pins LineageOS ARM GCC 4.9.

---

## Phase 2 — single partitioned NBD disk

Status: **PASSED**.

Accepted layout:

```text
/dev/nbd0
  p1 system    primary   ext4 RO   3072000 sectors
  p2 vendor    primary   ext4 RO    512000 sectors
  p3 cache     primary   ext4 RW    151552 sectors
  p4 extended                    8462336 sectors
  p5 userdata  logical   ext4 RW   8388608 sectors
  p6 persist   logical   ext4 RW     32768 sectors
  p7 metadata  logical   raw          32768 sectors
```

Host acceptance:

```text
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
```

One sparse raw disk is exported through exactly one NBD TCP session on port `10810`.

---

## Phase 3 — v2 initramfs transport supervisor

Status: **PASSED**.

Implemented:

- transport-only initramfs independent of Android init ordering;
- `usb0=172.16.42.1/24`;
- exactly one NBD session on `/dev/nbd0`;
- DOS/EBR partition discovery and exact size validation;
- p1/p2 RO, p3/p5/p6 RW, p7 raw/unmounted;
- userdata write/sync/checksum/unmount/remount/checksum test;
- persistent `/proc/last_kmsg` capture;
- HTTP diagnostics on 2325 and raw shell on 2324;
- NBD liveness from kernel `/sys/block/nbd0/pid`, not BusyBox launcher PID.

Accepted real-device transport result:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
uptime=617.14 1581.34
```

Resolved issues:

- **P2-001:** Android boot header v0 board name exceeded 16 bytes; fixed with `flo-v2-xport` plus preflight validation.
- **P2-002:** BusyBox `nbd-client` daemonization caused a false FAIL; liveness now uses the kernel NBD pid attribute.

---

## Phase 4 — protect USB root transport

Status: **isolation PASSED; early system-suspend policy implemented; rebuilt-kernel final gate pending**.

Audit document:

```text
diskless-v2/PHASE4_USB_AUDIT.md
```

### Layer 1 — USB/OTG root-transport guard

`scripts/v2/patch_kernel_usb_guard.py` applies the exact allowed `msm_otg.c` transport policy:

- parse `androidboot.diskless=1`;
- expose read-only `/sys/module/msm_otg/parameters/diskless_mode`;
- ignore B-peripheral bus-suspend LPM requests in diskless mode;
- return `-EBUSY` from `msm_otg_suspend()` before PHY retention/clock shutdown/regulator collapse while an active B-peripheral root transport is present.

`CONFIG_USB_G_ANDROID=n` separately guarantees Android's composite gadget cannot replace g_ether.

The first deterministic kernel with this layer passed verification:

```text
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
```

### P4-001 — combined power test changed NBD session

First combined real-device test observed:

```text
DISKLESS_V2_PHASE4_ACTIONS=FAIL
nbd_pid_before=327
system_suspend_write_rc=1
nbd_pid_after=569
FAIL_REASON=NBD session changed across power actions
```

USB/IP remained alive and all NBD partitions stayed mounted, but `/tmp/nbd.log` showed a second attach attempt. This was a real NBD session replacement, not the earlier PID false-negative.

The combined test mixed four classes of action, so no kernel change was made until isolation.

### P4-002 — isolated normal power actions PASS

`scripts/v2/phase4_isolate_power.sh` removed the forced system-suspend request and tested each normal runtime action independently.

Accepted real-device result:

```text
DISKLESS_V2_PHASE4_ISOLATION=PASS
diskless_guard=Y
baseline_nbd_pid=259
low_power_missing_count=0
low_power_nbd_pid=259
framebuffer_blank_nbd_pid=259
framebuffer_unblank_nbd_pid=259
otg_runtime_status_initial=active
otg_runtime_status_after_wait=active
otg_runtime_auto_nbd_pid=259
DISKLESS_V2_PHASE4_ISOLATION_VERIFIED=1
```

Conclusion:

- stock flo/Lineage RPM + CPU low-power enables are safe for the diskless transport;
- framebuffer blank/unblank is safe;
- `msm_otg` runtime-PM `auto` is safe;
- the NBD session replacement from P4-001 is isolated to the forced system-suspend sequence.

### Why the original OTG `-EBUSY` guard is not enough for system suspend

In this Linux 3.4 tree, `suspend_prepare()` calls `PM_SUSPEND_PREPARE` before freezing processes or suspending devices. The original P4-001 failure occurred because the system-suspend sequence could begin and suspend other devices before `msm_otg` itself rejected OTG suspend; rollback was enough to kill the TCP/NBD session.

A diskless root filesystem has no safe suspend-to-RAM contract unless a future design adds explicit USB/TCP/NBD reconnect and block-device recovery. Therefore diskless mode now blocks system suspend before device PM begins.

### Layer 2 — early system-suspend guard

Added:

```text
scripts/v2/patch_kernel_system_suspend_guard.py
```

Policy:

- register a PM notifier from `msm_otg`;
- when `androidboot.diskless=1`, return `NOTIFY_BAD` for `PM_SUSPEND_PREPARE`;
- reject all system suspend in diskless mode before process freezing/device PM;
- do not disable CPU idle, CPU power collapse, global RPM low power, framebuffer blank, charger detection, or OTG runtime PM.

The exact source result is independently reconstructed by:

```text
scripts/v2/verify_kernel_sources.py
```

Expected verifier contract after rebuild:

```text
usb_diskless_guard=enabled
usb_system_suspend_guard=pm_notifier
usb_system_suspend_stage=PM_SUSPEND_PREPARE
system_suspend_policy=blocked-in-diskless-mode
```

`build_transport_image.sh` refuses to package a kernel lacking the two diskless protection layers.

### Final Phase 4 gate

Added focused final test:

```text
scripts/v2/phase4_suspend_gate.sh
```

On a clean boot with the rebuilt kernel it must prove:

1. transport is already in STRESS;
2. `diskless_mode` is active;
3. `echo mem > /sys/power/state` is rejected synchronously;
4. the kernel NBD pid is unchanged across the rejected request;
5. immediate system read + userdata write/readback still work;
6. the original ten-minute transport stress reaches PASS;
7. Mac NBD log contains exactly one successful connection and no transport/server exception.

Formal success marker:

```text
DISKLESS_V2_PHASE4_VERIFIED=1
```

Do not begin Phase 5 Android fstab/image work until this marker is observed.
