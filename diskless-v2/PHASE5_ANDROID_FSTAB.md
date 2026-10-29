# Diskless v2 Phase 5 — deterministic Android fstab policy

## Scope

Phase 5 prepares the Android mount contract without importing the broad v1 rc bypasses.

The partition source of truth remains:

```text
diskless-v2/layout.json
```

## Source baseline policy

The repository keeps a reference Lineage flox fstab from:

```text
repository: LineageOS/android_device_asus_flox
branch:     lineage-18.1
commit:     936d74531565ca36e663e71dbcd43212fa93071b
fstab:      rootdir/etc/fstab.flox
sha256:     ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
```

Phase 5B additionally audits the actual boot/vendor artifacts and requires byte-identical stock eMMC-style fstab copies before any patching. On the current ROM the boot, clean `vendor.raw.img`, and repository snapshot all matched that same SHA-256.

## P5-001 — Android block-device namespace correction

The original Phase 5 generator used `/dev/nbd0pN`. That path is valid only in the pre-Android transport supervisor, where BusyBox creates temporary block nodes manually.

LineageOS 18.1 first-stage init immediately mounts tmpfs on `/dev`. Its `DeviceHandler::HandleUevent()` creates every `SUBSYSTEM=block` node under:

```text
/dev/block/<basename>
```

`FirstStageMountVBootV1::GetDmVerityDevices()` also adds the basename of every non-logical first-stage fstab block path to the coldboot device set. Therefore `nbd0p1`, `nbd0p2`, etc. are recreated as `/dev/block/nbd0pN`, not `/dev/nbd0pN`.

This was found by source audit **before the first real Android first-stage mount test**. All Phase 5B/5C artifacts generated with the earlier namespace are invalidated and must be regenerated.

Correct Android mapping:

```text
system    /dev/block/nbd0p1
vendor    /dev/block/nbd0p2
cache     /dev/block/nbd0p3
userdata  /dev/block/nbd0p5
persist   /dev/block/nbd0p6
metadata  /dev/block/nbd0p7
```

The extended partition p4 is only an MBR container and never appears in Android fstab.

## Generated fstab policy

System remains ext4 and read-only with `wait,first_stage_mount`.

Vendor remains ext4 and read-only with `wait,first_stage_mount`, but stock `check,formattable` is removed. A transient remote mount/transport failure must not cause fs_mgr to repair or format immutable vendor storage.

Cache remains ext4 with stock `wait,check,formattable` policy.

Userdata remains ext4 with stock `latemount,wait,check,formattable`; metadata is rewritten to `encryptable=/dev/block/nbd0p7`.

Persist remains ext4 with stock mount flags and `wait`.

The stock f2fs fallback rows are removed because the v2 layout explicitly creates ext4 cache/data filesystems. All `/dev/block/platform/msm_sdcc.1/by-name/*` rows are removed because SDCC1/eMMC is not registered in diskless mode.

The USB-host vold row and zram row are preserved.

## Deterministic tooling

Generation and validation:

```text
scripts/v2/generate_android_fstab.py
scripts/v2/validate_android_fstab.py
scripts/v2/build_android_fstab.sh
```

The validator now explicitly rejects transport-wrapper paths beginning with `/dev/nbd0` and requires the canonical Android `/dev/block/nbd0pN` namespace.

## Phase 5B — exact boot/vendor fstab-only replacement

Tooling:

```text
scripts/v2/audit_android_fstab_sources.py
scripts/v2/patch_boot_fstab.py
scripts/v2/patch_vendor_fstab.py
scripts/v2/validate_android_fstab_artifacts.py
scripts/v2/prepare_android_fstab_artifacts.sh
```

Contract:

- actual boot/vendor stock fstab must be identical before patching;
- original Lineage `/init` remains byte-identical;
- all non-fstab boot ramdisk payloads remain unchanged;
- vendor image may change only inside the exact original fstab file-data region;
- no v1 devwait/devstart/installd/USB/SELinux bypass is applied.

Because P5-001 changes the generated fstab paths, the previously accepted Phase 5B hashes are superseded. Regenerate Phase 5B before any Android first-stage test.

## Phase 5C — isolated Android-test single-NBD disk

The previous run proved that a clean system source and fstab-only vendor source can be assembled exactly into a separate Android-test disk without touching the accepted Phase 3/4 transport disk:

```text
DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1
system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
v1_system_rc_bypasses=absent

DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1

DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1
system_source=exact-clean-copy
vendor_source=exact-fstab-only-copy

DISKLESS_V2_ANDROID_DISK_PREPARED=1
```

However the vendor fstab in that specific disk still used the now-invalid `/dev/nbd0pN` namespace, so the disk must be rebuilt after corrected Phase 5B generation.

The correct regenerated Android-test disk remains:

```text
~/nexus7-diskless-v2/diskless-v2-android.raw.img
```

## Phase 5D — Android first-stage mount probe

After corrected Phase 5B and 5C pass again, use `diskless-v2/PHASE5_FIRST_STAGE.md`.

The formal gate is:

```text
DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1
```

No full Android boot begins until that marker is observed.
