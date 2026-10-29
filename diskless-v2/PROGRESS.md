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

Status: **PASSED**.

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

### Final real-device Phase 4 gate — PASSED

Accepted on the rebuilt two-layer kernel, in the same boot where the normal-power isolation gate had already passed:

```text
DISKLESS_V2_PHASE4_SUSPEND=PASS
diskless_guard=Y
nbd_pid_before=276
system_suspend_write_rc=1
nbd_pid_after=276
```

The rejected system-suspend request therefore did not replace the live NBD session. The same boot then completed the original ten-minute transport acceptance:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=171 checksum=0e9fbf0a07142896c8cf8d3e3bded48c
uptime=612.43 1711.70
```

Final Phase 4 marker:

```text
DISKLESS_V2_PHASE4_VERIFIED=1
isolation_gate=PASS
system_suspend_guard=PASS
transport_stress=PASS
single_nbd_connection=PASS
usb_root_transport=protected
```

This closes the USB/power root-transport gate. Phase 5 Android fstab/image work may now begin.

---

## Phase 5 — deterministic Android fstab/image

Status: **fstab generation gate PASSED; artifact replacement implementation in progress**.

Goals:

- derive Android block-device mapping from `diskless-v2/layout.json` rather than hand-maintained NBD numbers;
- map system/vendor/cache/userdata/persist/metadata to `/dev/nbd0p1`, `p2`, `p3`, `p5`, `p6`, `p7` respectively;
- preserve the stock flo mount flags and Android fs_mgr semantics wherever they remain valid;
- remove eMMC-only and alternate f2fs rows that cannot be valid in diskless mode;
- keep system/vendor read-only policy explicit;
- do not import the broad v1 USB/devwait/installd rc bypasses;
- validate generated fstab deterministically before it is packaged into an Android boot artifact.

### Phase 5A — deterministic fstab generation — PASSED

Pinned Android device-tree baseline:

```text
LineageOS/android_device_asus_flox
commit=936d74531565ca36e663e71dbcd43212fa93071b
stock_fstab_sha256=ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
```

The generated fstab is derived only from that pinned stock fstab plus `diskless-v2/layout.json`.

Accepted mapping:

```text
system=/dev/nbd0p1
vendor=/dev/nbd0p2
cache=/dev/nbd0p3
userdata=/dev/nbd0p5
persist=/dev/nbd0p6
metadata=/dev/nbd0p7
```

Policy validation:

```text
emmc_references=absent
f2fs_fallbacks=absent
vendor_formattable=disabled
usb_vold=preserved
zram=preserved
```

The exact generated result was independently produced on both macOS and Debian with the same digest:

```text
DISKLESS_V2_ANDROID_FSTAB_GENERATED=1
DISKLESS_V2_ANDROID_FSTAB_VERIFIED=1
DISKLESS_V2_ANDROID_FSTAB_BUILT=1
fstab_sha256=09b77ef5fb5a1dfe844f3c48485dabef04ee9371a920440a68c120059629bff7
```

This cross-host hash match closes the Phase 5A fstab-generation gate.

### Phase 5B — exact artifact replacement — IN PROGRESS

Next contract:

1. replace only `/fstab.flox` in the stock Lineage boot ramdisk;
2. replace only `/etc/fstab.flox` in a copy of the raw vendor image;
3. prove the boot ramdisk `/init` and all non-fstab entries are byte-identical to stock;
4. prove the vendor image differs only inside the original fstab file-data region;
5. do not apply any v1 devwait, USB, installd, SELinux, or panic-policy patch in this phase.

Only after this replacement gate passes will the prepared vendor filesystem be assembled back into the single partitioned NBD disk and used for first-stage Android mount testing.
