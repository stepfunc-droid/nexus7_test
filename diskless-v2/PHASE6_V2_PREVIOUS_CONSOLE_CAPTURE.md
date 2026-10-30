# Previous NBD console capture and P2 late-transition correction

Status: **CAPTURED / EXACT P2 PROVENANCE QUALIFIED / HOST NAMESPACE AUDIT NEXT / HARDWARE PAUSED**.

Batch G starts at `9369be99ef49df85eb5f7c8b783e5a62c94a1e5c`. Accepted recovery-image host preflight passed, but no manual reset or recovery RAM boot was performed. The device instead returned automatically to an eMMC-backed system, as confirmed by the user and ADB storage identity. P2's finite-hold causal support was revoked; its raw NBD/USB observations are retained.

## Runtime identity and retrieval

ADB initially showed shell UID 2000, eMMC mounts and `mmcblk0`; `/sys/block/nbd0/pid` was absent. Current boot ID was `b124ede8-c0bb-490a-8697-211f41b4bb73` and remained unchanged across the recorded ADB checks while uptime rose. The user reported repeated subsequent starts; kernel-versus-framework restart counts outside these checks are not independently established. Current logcat shows repeated system_server failures, but is not evidence of P2's failure.

Rooted debugging was initially disabled and direct last_kmsg access was denied. Supported bugreport export succeeded; its cached recovery last_kmsg files were dated October 27, lacked diskless/NBD tokens and have UNKNOWN attribution. No cause was inferred from them. The user then explicitly enabled rooted debugging. `adb root` restarted adbd only; boot ID stayed unchanged. Current `sys.boot_completed=1` and mounts confirm successful **eMMC** boot, not diskless success.

The current `/proc/last_kmsg` was copied byte-for-byte to the Mac:

```text
bytes=225756
sha256=c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497
archive=diskless-v2/audits/2026-10-30-previous-NBD-console/
current_kernel_boot_id=b124ede8-c0bb-490a-8697-211f41b4bb73
```

Its ring head starts around uptime 14s; the original cmdline and any unique run marker are absent. It directly describes a previous NBD-backed boot. Timing/NBD identity/user history corroborate P2 association, but later transitions were not controlled and exact named-run attribution is not independently unique. Treat contents as REAL_DEVICE_FACT about that previous NBD boot; do not silently call it controlled P2 evidence. Raw files and `PROVENANCE.json`/SHA manifest preserve these limits.

## Captured fault sequence

1. At 35/55/75s, second-stage `mount_all ./fstab.flox --early` skips `/dev/block/platform/msm_sdcc.1/by-name/cache` and `persist`; the action takes about 60s. Cache/persist remain unwritable.
2. At 96/116s, the late mount skips the eMMC userdata path and takes about 40s. Subsequent `/data` operations fail read-only. SurfaceFlinger/bootanim are started before that late mount completes, so an animation is not proof that data mounted.
3. Many service/data errors continue. At 1177.450s, `block nbd0: Receive control failed (result -110)` and socket shutdown are recorded, followed by widespread system/vendor I/O errors.
4. At 1180.114s init explicitly starts `reboot,boringssl-self-check-failed`; the kernel restarts with that command at 1180.442s.

The earlier eMMC path/mount failure is the priority concrete defect to audit. NBD's later receive failure is observed, but its cause is UNKNOWN. The last BoringSSL failure/reboot reason is not independently the first cause; do not bypass its self-test. Missing data may explain some downstream failures, but exact causal links require source/artifact verification.

## Current decision

Hardware paused; no recovery transition is needed to retrieve this already-saved file. Inactive P2 host export has been stopped; current ADB remains available on eMMC with user-enabled root. No runtime image/script was changed during capture.

Next binary host question: does the exact accepted system image expose an unpatched root `/fstab.flox` after SwitchRoot while only boot/vendor copies contain the accepted NBD mapping? Read actual filesystem entries and exact init source; bind results to source-image SHA. Preserve accepted Phase5 first-stage behavior. Only after the namespace audit may a minimal Phase6 correction be designed, gated and separately authorized for one hardware run.
