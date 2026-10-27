# Nexus 7 2013 (flo) diskless test

Experimental **RAM-only Linux boot** for a Nexus 7 (2013 Wi-Fi, `flo`) whose eMMC is failing.

The first milestone is deliberately small: prove that the tablet can run for a long time without the Linux kernel touching eMMC at all.

## Safety model

This project does **not** flash `boot`, `recovery`, `system`, or any other partition.

The test image is launched with:

```sh
fastboot boot diskless-test.img
```

That downloads the image to RAM and boots it once. Power-cycling returns to the existing bootloader/recovery setup.

The test kernel uses two independent protections against eMMC access:

1. `CONFIG_MMC` is disabled in the kernel configuration.
2. The `flo` device tree overrides `&sdcc1` (the onboard eMMC controller) to `status = "disabled"`.

So after the stock bootloader hands control to Linux, the test kernel has no MMC block driver and should never create `/dev/mmcblk*`.

> The stock bootloader itself still lives on eMMC. This project only eliminates eMMC access **after** the kernel starts.

## What the first image does

`diskless-test.img` contains:

- Linux kernel for APQ8064 / Nexus 7 2013
- appended `qcom-apq8064-asus-nexus7-flo.dtb`
- tiny BusyBox initramfs
- USB gadget Ethernet (CDC-ECM) setup
- telnet shell on `172.16.42.1:2323`

No root filesystem is mounted from eMMC.

## Build

GitHub Actions builds the image automatically. You can also build on Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y \
  git make gcc-arm-linux-gnueabihf bc bison flex libssl-dev libelf-dev \
  device-tree-compiler cpio gzip xz-utils wget python3 mkbootimg

./build.sh
```

Artifacts are written to `out/`.

## Test on the tablet

1. Boot the Nexus 7 into the bootloader (`Power + Volume Down`).
2. Connect it to the Mac/PC with USB.
3. Verify fastboot sees it:

```sh
fastboot devices
```

4. Boot the RAM image — **do not use `fastboot flash`**:

```sh
fastboot boot diskless-test.img
```

The first boot may leave the display unchanged; the initial validation path is USB networking.

### macOS USB shell

After Linux boots, macOS should see a new USB Ethernet/CDC-ECM interface. Give the Mac side `172.16.42.2/24` (replace `enX` with the new USB interface):

```sh
sudo ifconfig enX 172.16.42.2 netmask 255.255.255.0 up
ping 172.16.42.1
nc 172.16.42.1 2323
```

If `telnet` is installed you can use:

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

Expected result: no `mmcblk` devices and no eMMC probe/access messages.

The important test is simply to leave it running. If Android freezes quickly but this image stays alive for hours, that is strong evidence that a full diskless userspace is worth building.

## Next milestone

Once the RAM-only test is stable:

1. bring up `wcn36xx` Wi-Fi in the initramfs;
2. mount an Alpine/postmarketOS root filesystem over Wi-Fi (NFS/NBD);
3. run Wayland/X + Chromium in kiosk mode for TradingView.

That later stage will still use eMMC only for the original Qualcomm/ASUS boot chain; Linux userspace and application storage will live elsewhere.

## Boot image parameters

Flo's historical Android boot image layout is retained:

- base: `0x80200000`
- kernel offset: `0x00008000`
- ramdisk offset: `0x02000000`
- second offset: `0x00f00000`
- tags offset: `0x00000100`
- page size: `2048`

The command line starts with 26 padding characters because the flo bootloader historically consumes the first 26 characters when directly booting a mainline kernel.
