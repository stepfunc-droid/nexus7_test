# Diskless v2 Phase 4 — USB root-transport power audit

## Scope

This audit covers the pinned flo kernel at:

```text
LineageOS/android_kernel_google_msm
commit 0da5107137f93b8d8f697e949ab0784f5ace450c
```

The question is deliberately narrow:

> Can normal OTG / gadget / power-management behavior put the USB peripheral link carrying the diskless NBD root transport into a PHY/controller low-power transition or allow Android to replace the gadget owner?

The Phase 3 transport baseline has already passed more than ten minutes of single-NBD read/write stress. Phase 4 must therefore protect that working transport without broadly disabling unrelated power management.

## 1. flo platform data

`arch/arm/mach-msm/asustek/flo/board-flo.c` defines `msm_otg_pdata` with:

```text
mode        = USB_OTG
otg_control = OTG_PMIC_CONTROL
phy_type    = SNPS_28NM_INTEGRATED_PHY
```

and does **not** set:

```text
enable_lpm_on_dev_suspend = true
```

This matters because `msm_otg.c` only adds `ALLOW_LPM_ON_DEV_SUSPEND` when that platform-data flag is true.

For the flo combination of 28 nm PHY + PMIC OTG control, the driver does enable the generic PHY retention/power-collapse capabilities. Those capabilities are valid for idle/non-data states and are not themselves a reason to disable all OTG PM.

## 2. CI13xxx gadget suspend path

`drivers/usb/gadget/ci13xxx_msm.c` does not directly shut down the PHY, clocks, regulators, or USB controller on a gadget suspend event.

Its suspend notification mainly manages the wake IRQ. The generic CI13xxx UDC then calls:

```text
usb_phy_set_suspend(transceiver, 1)
```

The actual policy decision therefore belongs to `msm_otg_set_suspend()` / `msm_otg_suspend()`.

## 3. Existing msm_otg behavior already helps flo

In `OTG_STATE_B_PERIPHERAL`, `msm_otg_set_suspend()` only sets `A_BUS_SUSPEND` and schedules an LPM transition when `ALLOW_LPM_ON_DEV_SUSPEND` is present.

Because flo does not enable that capability, the stock flo path already avoids the normal device-bus-suspend LPM transition.

Separately, `msm_otg_suspend()` calculates whether the current state is a permitted `device_bus_suspend`. With an active B session (`B_SESS_VLD`) that is not a DCP-only charger and is not an allowed device-bus-suspend case, the driver returns `-EBUSY` instead of entering LPM.

This explains why the standalone g_ether/NBD transport can remain stable under ordinary runtime activity without globally disabling OTG PM.

## 4. Why add an explicit diskless guard anyway

The root filesystem is now carried by this USB peripheral link. Relying only on incidental platform-data and charger-classification behavior is too fragile for a root-storage transport.

Diskless v2 therefore adds one narrow source-level policy to `drivers/usb/otg/msm_otg.c`:

1. parse `androidboot.diskless=1` into a read-only `diskless_mode` state;
2. expose that state at `/sys/module/msm_otg/parameters/diskless_mode` for acceptance testing;
3. while `diskless_mode` is active, ignore a peripheral bus-suspend request in `OTG_STATE_B_PERIPHERAL` rather than letting it initiate OTG/PHY LPM;
4. while an active B-peripheral session also has `B_SESS_VLD`, return `-EBUSY` from `msm_otg_suspend()` before clocks, regulators, retention or PHY power-collapse logic is touched.

The transformation is applied by:

```text
scripts/v2/patch_kernel_usb_guard.py
```

and independently reconstructed byte-for-byte by:

```text
scripts/v2/verify_kernel.sh
```

The kernel verifier therefore rejects any additional untracked edit to `msm_otg.c`.

## 5. What the guard intentionally does NOT disable

The patch does **not**:

- disable CPU idle or CPU power-collapse modes;
- disable global RPM low-power modes;
- disable charger detection;
- force a charger type;
- disable the PHY/OTG low-power machinery for idle/non-diskless states;
- change host-mode OTG behavior;
- change CI13xxx endpoint behavior;
- patch Android power rc files;
- add a second gadget driver.

The goal is to protect exactly one condition: an active diskless B-peripheral root-storage session.

## 6. Android gadget ownership

Diskless v2 independently enforces:

```text
CONFIG_USB_ETH=y
CONFIG_USB_G_ANDROID=n
```

Therefore Android's `android_usb` platform device may still exist in board code, but there is no `g_android` driver in this kernel to bind it and replace/reconfigure the active g_ether gadget.

ADB/MTP/RNDIS-over-Android-gadget must not be reintroduced during the root-transport phases. If ADB is needed later, the initial design is ADB over TCP on the existing diskless network.

## 7. Phase 4 acceptance test

`scripts/v2/phase4_power_test.sh` runs while the existing Phase 3 ten-minute NBD stress loop is active. It verifies the kernel diskless guard and then reproduces the low-power writes from flo's stock `init.flox.power.rc` `enable-low-power` action:

- RPM low-power enables;
- CPU retention;
- CPU power-collapse suspend/idle enables;
- standalone power-collapse suspend/idle enables.

It additionally:

- blanks/unblanks fb0 when the kernel exposes that control;
- puts the actual msm_otg platform device under runtime-PM `auto` policy when available;
- performs a controlled `mem` system-suspend request when supported;
- requires the same `/sys/block/nbd0/pid` session before and after the actions;
- performs immediate block reads/writes after the power actions;
- then waits for the original ten-minute transport stress test to reach PASS;
- checks the Mac NBD server log for exactly one successful NBD connection and no transport/server error.

Formal success marker:

```text
DISKLESS_V2_PHASE4_VERIFIED=1
```

Only after that marker is observed may Phase 5 Android fstab/image preparation begin.
