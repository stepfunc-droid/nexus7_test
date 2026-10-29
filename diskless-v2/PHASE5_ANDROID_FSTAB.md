# Diskless v2 Phase 5 — deterministic Android fstab policy

## Scope

Phase 5 prepares the Android mount contract without importing the broad v1 rc bypasses.

Pinned Lineage device baseline:

```text
repository: LineageOS/android_device_asus_flox
branch:     lineage-18.1
commit:     936d74531565ca36e663e71dbcd43212fa93071b
fstab:      rootdir/etc/fstab.flox
sha256:     ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
```

The exact stock fstab is stored at:

```text
diskless-v2/fstab.flox.stock
```

The partition source of truth remains:

```text
diskless-v2/layout.json
```

## Mapping

```text
system    /dev/nbd0p1
vendor    /dev/nbd0p2
cache     /dev/nbd0p3
userdata  /dev/nbd0p5
persist   /dev/nbd0p6
metadata  /dev/nbd0p7
```

The extended partition p4 is only an MBR container and never appears in Android fstab.

## Policy

The generator preserves the stock Lineage mount options unless diskless architecture makes a stock policy invalid.

System remains ext4 and read-only with `wait,first_stage_mount`.

Vendor remains ext4 and read-only with `wait,first_stage_mount`, but stock `check,formattable` is intentionally removed. In diskless v2 vendor is an immutable remote partition. A transient transport/mount failure must not cause fs_mgr to repair or format it.

Cache remains ext4 with the stock `wait,check,formattable` policy.

Userdata remains ext4 with the stock `latemount,wait,check,formattable` policy. The stock external-metadata encryption reference is preserved but rewritten to `encryptable=/dev/nbd0p7`.

Persist remains ext4 with its stock mount flags and `wait` policy.

The stock f2fs fallback rows for cache and userdata are removed because the v2 layout explicitly creates ext4 filesystems. Falling through to f2fs after an ext4 failure would hide the real mount/transport error and is not a valid v2 configuration.

All `/dev/block/platform/msm_sdcc.1/by-name/*` rows are removed. Linux does not register SDCC1/eMMC in diskless mode, so boot/recovery/misc/bootloader rows are invalid and must never cause fs_mgr lookups.

The stock USB-host vold row and zram row are preserved because they are independent runtime features and do not own the diskless USB gadget transport.

## Deterministic tooling

Generation:

```text
scripts/v2/generate_android_fstab.py
```

Independent validation:

```text
scripts/v2/validate_android_fstab.py
```

Build gate:

```text
scripts/v2/build_android_fstab.sh
```

The generator verifies the pinned stock fstab hash before transforming it. The validator independently verifies the exact v2 block mapping, mount flags, metadata path, absence of eMMC references, absence of f2fs fallback rows, and preservation of USB-host vold/zram rows.

## Expected generated active rows

```text
/dev/nbd0p1  /system   ext4  ro,barrier=1                                                               wait,first_stage_mount
/dev/nbd0p2  /vendor   ext4  ro,barrier=1                                                               wait,first_stage_mount
/dev/nbd0p3  /cache    ext4  noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic   wait,check,formattable
/dev/nbd0p5  /data     ext4  noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic   latemount,wait,check,formattable,encryptable=/dev/nbd0p7
/dev/nbd0p6  /persist  ext4  noatime,nosuid,nodev,barrier=1,data=ordered,nodelalloc                     wait
/devices/platform/msm_hsusb_host/usb* auto auto defaults                                                 voldmanaged=usb:auto
/dev/block/zram0 none swap defaults                                                                      zramsize=1610612736,notrim
```

## Gate

Phase 5 fstab generation passes only when:

```text
DISKLESS_V2_ANDROID_FSTAB_GENERATED=1
DISKLESS_V2_ANDROID_FSTAB_VERIFIED=1
DISKLESS_V2_ANDROID_FSTAB_BUILT=1
```

This is only the fstab sub-gate. After it passes, the next Phase 5 task is deterministic insertion of this exact fstab into the Android ramdisk/vendor image preparation path, followed by validation that no eMMC fstab copy remains in the boot path.

No Android rc bypass is authorized by this phase.
