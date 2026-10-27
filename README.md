# Nexus 7 2013 (flo) diskless test

Experimental **RAM-only Linux boot** for a Nexus 7 (2013 Wi-Fi, `flo`) whose eMMC is failing.

The first milestone is deliberately small: prove that the tablet can run for a long time without the Linux kernel touching eMMC at all.

## Safety model

This project does **not** flash `boot`, `recovery`, `system`, or any other partition.

The test image is launched with:

```sh
fastboot boot out/diskless-test.img
```

That downloads the image to RAM and boots it once. Power-cycling returns to the existing bootloader/recovery setup.

The test kernel uses two independent protections against eMMC access:

1. `CONFIG_MMC` is disabled in the kernel configuration.
2. The `flo` device tree overrides `&sdcc1` (the onboard eMMC controller) to `status = "disabled"`.

So after the stock bootloader hands control to Linux, the test kernel has no MMC block driver and should never create `/dev/mmcblk*`.

> The stock Qualcomm/ASUS boot chain still lives on eMMC. This project only eliminates eMMC access **after** the Linux kernel starts.

## First test image

`out/diskless-test.img` contains:

- mainline Linux kernel for APQ8064 / Nexus 7 2013
- appended `qcom-apq8064-asus-nexus7-flo.dtb`
- tiny BusyBox initramfs
- eMMC disabled at both kernel-config and device-tree levels
- USB gadget Ethernet (CDC-ECM)
- telnet shell on `172.16.42.1:2323`

No root filesystem is mounted from eMMC.

## Build locally on macOS / Linux

The recommended build path is local Docker. Nothing is built by GitHub Actions.

Requirements:

- Git
- Docker Desktop (macOS) or Docker Engine (Linux)

Clone and build:

```sh
git clone https://github.com/stepfunc-droid/nexus7_test.git
cd nexus7_test
bash build-local.sh
```

The Docker image contains the ARM cross compiler, kernel build dependencies, `mkbootimg`, and the tools needed to build the initramfs. Build output is written back to your local checkout:

```text
out/
├── diskless-test.img
├── flo-no-emmc.dtb
├── initramfs.cpio.gz
├── kernel.config
└── SHA256SUMS
```

To rebuild from scratch, simply run:

```sh
bash build-local.sh
```

You can also run `build.sh` directly on a Debian/Ubuntu host if you already have the required ARM cross-toolchain installed, but Docker is the supported path for macOS.

## Test on the tablet

1. Boot the Nexus 7 into the bootloader (`Power + Volume Down`).
2. Connect a USB data path to the host running `fastboot`.
3. Verify fastboot sees it:

```sh
fastboot devices
```

4. Boot the image into RAM — **do not use `fastboot flash`**:

```sh
fastboot boot out/diskless-test.img
```

The first boot may leave the display unchanged; the initial validation path is USB networking.

### macOS USB shell

After Linux boots, macOS should see a new USB Ethernet/CDC-ECM interface. Give the Mac side `172.16.42.2/24` (replace `enX` with the new USB interface):

```sh
sudo ifconfig enX 172.16.42.2 netmask 255.255.255.0 up
ping 172.16.42.1
nc 172.16.42.1 2323
```

If `telnet` is installed:

```sh
telnet 172.16.42.1 2323
```

Inside the tablet shell, check:

```sh
cat /proc/cmdline
cat /proc/partitions
ls -l /dev/mmcblk* 2>/dev/null || echo "no mmc block devices"
dmesg | grep -i mmc
uptime
```

Expected result: no `mmcblk` devices and no eMMC probe/access messages after Linux takes control.

The important test is to leave it running. If Android freezes quickly but this RAM-only image stays alive for hours, that is strong evidence that a full diskless userspace is worth building.

## Next milestone

Once the RAM-only test is stable:

1. bring up `wcn36xx` Wi-Fi in the initramfs;
2. mount an Alpine/postmarketOS root filesystem over Wi-Fi (NFS/NBD);
3. run Wayland/X + Chromium in kiosk mode for TradingView.

## Boot image parameters

The current test uses flo's historical Android boot image layout:

- base: `0x80200000`
- kernel offset: `0x00008000`
- ramdisk offset: `0x02000000`
- second offset: `0x00f00000`
- tags offset: `0x00000100`
- page size: `2048`

The command line starts with 26 padding characters because the flo bootloader has historically consumed the first 26 characters when directly booting a mainline kernel.

These parameters are intentionally kept isolated in `build.sh` so they can be adjusted after the first real-device test if necessary.
