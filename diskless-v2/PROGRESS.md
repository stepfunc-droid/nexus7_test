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

Status: **isolation PASSED; rebuilt two-layer kernel gate PASSED; final real-device suspend gate pending**.

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

### Layer 2 — early system-suspend guard

In this Linux 3.4 tree, `suspend_prepare()` calls `PM_SUSPEND_PREPARE` before freezing processes or suspending devices. Diskless mode therefore blocks suspend-to-RAM at that notifier stage instead of letting device PM begin and later roll back.

Added:

```text
scripts/v2/patch_kernel_system_suspend_guard.py
```

Policy:

- register a PM notifier from `msm_otg`;
- when `androidboot.diskless=1`, return `NOTIFY_BAD` for `PM_SUSPEND_PREPARE`;
- reject all system suspend in diskless mode before process freezing/device PM;
- do not disable CPU idle, CPU power collapse, global RPM low power, framebuffer blank, charger detection, or OTG runtime PM.

The exact source result is independently reconstructed by `scripts/v2/verify_kernel_sources.py`.

### Phase 4 rebuilt deterministic kernel gate — PASSED

Accepted Debian build result after both protection layers were installed:

```text
DISKLESS_V2_KERNEL_SOURCE_TRANSFORMS_VERIFIED=1
DISKLESS_V2_KERNEL_VERIFIED=1
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
kernel_source_state=baseline-plus-exact-sdcc1-usb-and-system-suspend-guards
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
usb_gadget=g_ether
usb_android_gadget=disabled
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
usb_system_suspend_guard=pm_notifier
usb_system_suspend_stage=PM_SUSPEND_PREPARE
system_suspend_policy=blocked-in-diskless-mode
persistent_ram_console=enabled
sdcc1_emmc=disabled
```

This closes the rebuilt-kernel sub-gate. The next artifact must be packaged from this exact verified zImage.

### Final Phase 4 gate

Focused final test:

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
