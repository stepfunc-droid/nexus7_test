# Diskless v2 Phase 4 — USB root-transport power audit

## Scope

Pinned kernel:

```text
LineageOS/android_kernel_google_msm
commit 0da5107137f93b8d8f697e949ab0784f5ace450c
```

Question:

> Which normal flo/Lineage power-management paths are safe for a USB-Ethernet/NBD root transport, and which transitions must be prohibited in diskless mode?

Phase 3 already proved a stable ten-minute single-NBD baseline. Phase 4 therefore changes only behavior demonstrated to threaten that transport.

## 1. flo USB architecture

flo uses:

```text
mode        = USB_OTG
otg_control = OTG_PMIC_CONTROL
phy_type    = SNPS_28NM_INTEGRATED_PHY
```

Its `msm_otg_pdata` does not enable `enable_lpm_on_dev_suspend`, so stock flo does not set `ALLOW_LPM_ON_DEV_SUSPEND`.

The CI13xxx gadget layer does not independently shut down the PHY on gadget suspend. It delegates through `usb_phy_set_suspend()` to `msm_otg`, where the actual low-power policy lives.

## 2. Layer 1: explicit OTG/root-transport guard

`scripts/v2/patch_kernel_usb_guard.py` adds a narrow diskless policy to `drivers/usb/otg/msm_otg.c`:

1. parse `androidboot.diskless=1`;
2. expose read-only `/sys/module/msm_otg/parameters/diskless_mode`;
3. ignore B-peripheral bus-suspend LPM requests while diskless mode is active;
4. reject `msm_otg_suspend()` before PHY retention, clock shutdown or regulator collapse while the active B-peripheral root transport exists.

Diskless v2 separately enforces:

```text
CONFIG_USB_ETH=y
CONFIG_USB_G_ANDROID=n
```

so Android's composite gadget cannot replace g_ether.

## 3. First combined power test: real NBD session replacement

The initial Phase 4 combined test applied:

- stock flo `enable-low-power` CPU/RPM writes;
- framebuffer blank/unblank;
- `msm_otg` runtime-PM `auto`;
- `echo mem > /sys/power/state`.

Observed:

```text
nbd_pid_before=327
system_suspend_write_rc=1
nbd_pid_after=569
FAIL_REASON=NBD session changed across power actions
```

USB networking remained alive and NBD partitions stayed mounted, but `/tmp/nbd.log` showed a second attach attempt. The session replacement was therefore real.

A rejected system-suspend request can still be harmful if rejection occurs late: Linux may already have suspended other devices and then roll them back after one driver returns `-EBUSY`.

## 4. Isolation result: normal runtime power actions are safe

`scripts/v2/phase4_isolate_power.sh` removed the system-suspend request and tested each runtime action separately.

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

Therefore the following are accepted and remain enabled:

- global RPM low-power enables;
- CPU retention;
- CPU power collapse and standalone power collapse;
- framebuffer blank/unblank;
- `msm_otg` runtime-PM `auto` policy.

The P4-001 failure is isolated to the system-suspend sequence.

## 5. Why system suspend is blocked in diskless mode

This kernel's `suspend_prepare()` calls:

```text
pm_notifier_call_chain(PM_SUSPEND_PREPARE)
```

before process freezing and before device suspend callbacks.

The diskless root filesystem is carried by USB Ethernet + TCP + NBD. Suspend-to-RAM has no valid recovery contract unless the design later adds explicit USB/TCP/NBD reconnect plus block-device recovery semantics.

Therefore diskless mode treats system suspend as unsupported rather than attempting a fragile partial suspend.

## 6. Layer 2: early system-suspend guard

`scripts/v2/patch_kernel_system_suspend_guard.py` adds a PM notifier to `msm_otg.c`.

When:

```text
androidboot.diskless=1
```

and the PM core announces:

```text
PM_SUSPEND_PREPARE
```

the notifier returns `NOTIFY_BAD` immediately.

This rejects suspend before:

- process freezing;
- `dpm_suspend_start()`;
- individual device suspend callbacks;
- PHY/controller/device rollback sequences.

The policy is deliberately global within diskless mode: system suspend is unsupported for a live remote-root architecture until a future reconnect/resume protocol exists.

This does **not** disable normal CPU idle, RPM low power, framebuffer blanking, charger detection or OTG runtime PM.

## 7. Deterministic verification

Source transformations are independently reconstructed from the pinned upstream files by:

```text
scripts/v2/verify_kernel_sources.py
```

Expected kernel verifier contract:

```text
usb_diskless_guard=enabled
usb_diskless_cmdline=androidboot.diskless=1
usb_system_suspend_guard=pm_notifier
usb_system_suspend_stage=PM_SUSPEND_PREPARE
system_suspend_policy=blocked-in-diskless-mode
```

`build_transport_image.sh` refuses to package a kernel missing the required protection layers.

## 8. Final Phase 4 gate

Use:

```text
scripts/v2/phase4_suspend_gate.sh
```

on a clean boot of the rebuilt kernel while the normal ten-minute transport stress test is active.

It must prove:

1. diskless mode is active;
2. `echo mem > /sys/power/state` is rejected;
3. `/sys/block/nbd0/pid` is unchanged;
4. block reads and userdata write/readback succeed immediately afterwards;
5. the original ten-minute transport stress reaches PASS;
6. the Mac NBD log contains exactly one successful connection and no transport/server exception.

Formal marker:

```text
DISKLESS_V2_PHASE4_VERIFIED=1
```

Only after that marker may Phase 5 Android fstab/image preparation begin.
