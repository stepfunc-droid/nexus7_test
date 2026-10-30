# Phase6 root-peer route diagnostic preparation

Batch O starts atb56c2c3e4d42cf20c8279be6041b6dbf71c1ff50. Question: can a separate deterministic P2 derivative add only the reviewed root-peer rule/precondition while preserving other image/disk bytes? YES/HOST_FACT; runtime IMPLEMENTED_UNPROVEN, hardware not authorized by this host batch.

Reviewed fragment `initramfs/phase6-root-route-rule.inc` adds `ip rule add priority 0 to 172.16.42.2/32 table main`, requires ip/iprule applets and exact priority/destination/table readback before NBD. It emits a kernel marker after success. Wrong priority/address/table, failed add or missing applet blocks attach. Three actual Mac tests pass, including eight readback fixtures. This explicitly adds a diagnostic policy to the copied P2 wrapper; accepted wrapper/kernel/USB/NBD/handoff/Android rc/SELinux files are unchanged.

Accepted builder produces two identical images. Accepted image auditor and independent exact P2 delta auditor pass: only /init data/length differs by the pinned fragment; other header geometry/payloads, original Android init and every other CPIO entry/metadata remain exact. Shell syntax passes. Frozen BusyBox hash is unchanged and its applet-name table contains ip/iprule; actual target execution remains protected by runtime fail-closed checks.

Native APFS clonefile creates a separate golden-disk copy without allocating another full6.2GB on the nearly full Mac volume; no full-copy fallback exists. The original4295-byte root-fstab data is copied from the audited system derivative. Independent full-byte disk/system audit proves all other bytes unchanged, original sources unchanged, and new disk byte-identical to R1 pre-run. Runtime-written R1 disk is retained untouched. New trace map is bound to the new disk path.

```text
artifact_dir=out/phase6-v2-root-route-O/artifacts/
image_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
wrapper_sha256=adf5ad9b4dafcdba8c3796208000c051c89e8a7c1272601a69f4a42d472a855e
block_sha256=08f50f97201f622389a5f276929c68722b9125d0c3713e1c2ac8c36415669e65
disk_sha256=060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a
manifest_sha256=059644adca6f27990c8a4644143c3229f33bab21d288175d8fe66fe99524fa70
trace_map_sha256=abe8b46bdb319c32911ed3d5ac8bc5a53799803da8b6bd83678d1deda1203763
```

ADB collector gains explicit --start-offline mode for a separately verified fastboot start: refuses a live ADB baseline in that mode, records baseline unavailable/provenance UNKNOWN, and saves each first-visible rooted successor as before. Default online-baseline behavior is unchanged. Four CLI/binary/identity tests pass; an actual two-second offline Mac dry run arms/finishes without any device transition. This does not prove first-successor provenance or authorize a boot.

Evidence: audits/2026-10-30-root-route-preparation. No device boot/flash/reset occurred in O. Next: separately committed Q1 single-use plan with fresh original fact gate, input/device identities, automatic offline capture and a180s maximum active observation/60s no-progress decision. No prolonged reboot waiting. Kernel compilation is unnecessary for this diagnostic.
