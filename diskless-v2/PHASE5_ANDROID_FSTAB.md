# Diskless v2 Phase 5 — deterministic Android fstab policy

## Scope

Phase 5 prepares the Android mount contract without importing the broad v1 rc bypasses.

The partition source of truth remains:

```text
diskless-v2/layout.json
```

The Android mount mapping is:

```text
system    /dev/nbd0p1
vendor    /dev/nbd0p2
cache     /dev/nbd0p3
userdata  /dev/nbd0p5
persist   /dev/nbd0p6
metadata  /dev/nbd0p7
```

The extended partition p4 is only an MBR container and never appears in Android fstab.

## Source baseline policy

The repository keeps a reference Lineage flox fstab from:

```text
repository: LineageOS/android_device_asus_flox
branch:     lineage-18.1
commit:     936d74531565ca36e663e71dbcd43212fa93071b
fstab:      rootdir/etc/fstab.flox
sha256:     ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
```

However Phase 5B does not blindly assume the repository snapshot is the runtime artifact baseline. Before patching, `scripts/v2/audit_android_fstab_sources.py` extracts the actual boot-ramdisk and vendor-image fstab copies and requires:

```text
boot_fstab_state=stock-emmc-style
vendor_fstab_state=stock-emmc-style
boot_vendor_fstab_identical=yes
```

That verified artifact copy becomes `out/diskless-v2-android/fstab.artifact.stock` and is the actual input to generation and artifact validation.

Accepted artifact audit on the current ROM:

```text
boot_fstab_sha256=ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
vendor_fstab_sha256=ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
boot_fstab_state=stock-emmc-style
vendor_fstab_state=stock-emmc-style
boot_matches_repo_stock=yes
vendor_matches_repo_stock=yes
boot_vendor_fstab_identical=yes
DISKLESS_V2_ANDROID_FSTAB_ARTIFACT_BASELINE_VERIFIED=1
```

This also established that `vendor.raw.img`, not the historical `vendor.nbd.raw.img`, is the clean vendor source.

## Generated fstab policy

System remains ext4 and read-only with `wait,first_stage_mount`.

Vendor remains ext4 and read-only with `wait,first_stage_mount`, but stock `check,formattable` is intentionally removed. A transient remote mount/transport failure must not cause fs_mgr to repair or format immutable vendor storage.

Cache remains ext4 with stock `wait,check,formattable` policy.

Userdata remains ext4 with stock `latemount,wait,check,formattable`; metadata is rewritten to `encryptable=/dev/nbd0p7`.

Persist remains ext4 with stock mount flags and `wait`.

The stock f2fs fallback rows are removed because the v2 layout explicitly creates ext4 cache/data filesystems. All `/dev/block/platform/msm_sdcc.1/by-name/*` rows are removed because SDCC1/eMMC is not registered in diskless mode.

The USB-host vold row and zram row are preserved.

## Phase 5A — deterministic generation — PASSED

Tooling:

```text
scripts/v2/generate_android_fstab.py
scripts/v2/validate_android_fstab.py
scripts/v2/build_android_fstab.sh
```

The original repository-baseline generator was independently reproduced on macOS and Debian. After Phase 5B was hardened to generate from the verified actual-ROM baseline, the accepted generated artifact is:

```text
DISKLESS_V2_ANDROID_FSTAB_GENERATED=1
DISKLESS_V2_ANDROID_FSTAB_VERIFIED=1
generated_fstab_sha256=d3d7a183b7b0373a93f5cd3af6d980ff8ba71cc0e3bede6e8be86417b5c876f7
emmc_references=absent
f2fs_fallbacks=absent
vendor_formattable=disabled
usb_vold=preserved
zram=preserved
```

## Phase 5B — exact boot/vendor fstab-only replacement — PASSED

Tooling:

```text
scripts/v2/audit_android_fstab_sources.py
scripts/v2/patch_boot_fstab.py
scripts/v2/patch_vendor_fstab.py
scripts/v2/validate_android_fstab_artifacts.py
scripts/v2/prepare_android_fstab_artifacts.sh
```

Accepted boot result:

```text
DISKLESS_V2_BOOT_FSTAB_PATCHED=1
stock_boot_sha256=4a325b563e59f393cfa40823f312f6bf53ebf3c955098d3133c5f441230c9223
patched_boot_sha256=a6791ea9d0b2fbc93b62419a13be3f3b94af0d4969feab7d009a9c0bc66c9a86
ramdisk_init=unchanged
non_fstab_ramdisk_payloads=unchanged
```

Accepted vendor result:

```text
DISKLESS_V2_VENDOR_FSTAB_PATCHED=1
stock_vendor_sha256=91b249dfcde1ad4a29b898a4371beb26b24e7cec2e63e2b05f942a2aa0264554
patched_vendor_sha256=b658abfd55fbd48a6aaf458d16bb8d60c177bb6bf2a2c65d0e37a504e5fcfbdb
fstab_offset=13807616
outside_fstab_region=unchanged
```

Independent artifact validation:

```text
DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_VERIFIED=1
boot_source_fstab=verified-actual-rom-baseline
boot_init=unchanged
boot_non_fstab_entries=unchanged
vendor_outside_fstab_region=unchanged
v1_rc_bypasses=absent-by-construction
DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_BUILT=1
```

No devwait, devstart, installd, Android USB rc, SELinux or panic-policy bypass is applied by Phase 5B.

## Phase 5C — isolated Android-test single-NBD disk — NEXT

Do not overwrite the Phase 3/4 accepted transport disk. Phase 5C creates a separate:

```text
~/nexus7-diskless-v2/diskless-v2-android.raw.img
```

The disk must use:

- a clean stock `system.raw.img` with all six historical v1 replacement markers absent;
- the Phase 5B `vendor-fstab.raw.img`;
- the existing Linux-3.4-compatible cache/userdata/persist component images;
- the same `diskless-v2/layout.json` partition geometry.

Tooling:

```text
scripts/v2/audit_android_system_source.py
scripts/v2/prepare_android_disk.sh
scripts/v2/validate_android_disk_sources.py
```

The system audit fails closed if any v1 USB/devwait/devstart/installd replacement is present. The final disk validator hashes the exact p1/p2 source-byte regions in the assembled disk and requires them to match the clean system and fstab-only vendor inputs.

Expected gate:

```text
DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1
DISKLESS_V2_DISK_ASSEMBLED=1
DISKLESS_V2_DISK_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1
DISKLESS_V2_ANDROID_DISK_PREPARED=1
```

After this gate passes, Phase 5 proceeds to the Android first-stage mount probe. The probe must establish the already-proven one-NBD transport before executing the untouched Lineage `/init`; it must not reintroduce any v1 rc bypass.
