# Diskless v2 — Current checkpoint

Authority: read `AGENTS.md`, complete `DISKLESS_V2_EXECUTION.md`, this checkpoint, latest WORKLOG, active phase evidence and all failure records. Conversation memory is not project state.

## Accepted boundary

```text
branch=diskless-v2
Phase1-5=ACCEPTED/FROZEN
Phase5 real-device scope=p1/system + p2/vendor first-stage mounts only
Phase6=ACTIVE / full diskless Android boot NOT PROVEN
Phase7=NOT REACHED
hardware=R1 CONDITIONAL SINGLE-RUN EXCEPTION / no other boot or recovery authorization
```

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
accepted_continuation_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
panic_hold_diagnostic_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
accepted_clean_system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
```

Keep `/bin/busybox`, `/etc/diskless-v2-layout`, single ECM/NBD transport, original `/init.android`, Phase5 attach/retry/liveness/partition validation and first-stage fstab unchanged unless new evidence directly invalidates an accepted gate.

## Latest device sequence and correction

P1 loaded lk2nd but launched no diagnostic because a host identity predicate wrongly expected a version string. Actual identity: serial 07a117ae, same physical port, product `lk2nd-msm8960`, empty version, VID/PID 18d1:d00d. P1 closed before diagnostic.

P2 booted the exact panic-hold diagnostic once from that lk2nd. One NBD session completed 1688 READ replies / 71,657,472 bytes, including 53,687,296 p1 bytes, zero writes. Last READ offset 164990976 length 49152. No accepted p3/p6 filesystem evidence appeared.

The finite 495s reply inactivity / >=455s unchanged USB observation remains a fact. The initial `panic_timeout_dependency=SUPPORTED` interpretation is **REVOKED** (F6-023): the device later automatically returned to eMMC, confirmed by the user and ADB mount/kernel identity. Panic auto-restart alone is insufficient to explain the observed sequence, subject to unknown late sysctl changes; the specific cause remains UNKNOWN. A boot animation or restored ADB does not establish same-kernel continuity or diskless success.

```text
6V2-A/B/C=HOST PASS, refreshed in batch C
6V2-D=REAL_DEVICE_FACT / attach PASS
6V2-E=p3/p6 evidence NOT_REACHED (not proof second stage never ran)
6V2-F=late-fs NOT PROVEN from block evidence alone
current runtime=eMMC-backed; sys.boot_completed=1 at root capture
current boot_id=b124ede8-c0bb-490a-8697-211f41b4bb73
ADB=root, after user enabled rooted debugging
P2 NBD server 92856=inactive and stopped
additional recovery/reset commands=NONE
```

## Captured previous NBD console

ADB root retrieved 225,756 bytes from current `/proc/last_kmsg`:

```text
sha256=c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497
archive=audits/2026-10-30-previous-NBD-console/
```

REAL_DEVICE_FACT about the captured prior NBD boot:

- second-stage `mount_all ./fstab.flox` skips eMMC cache/persist/userdata paths after waits;
- `/cache`, `/persist` and `/data` operations fail read-only;
- much later, NBD receive fails with -110 and socket closes;
- init explicitly requests `boringssl-self-check-failed` reboot after I/O failures.

Exact P2 attribution is qualified: ring head/cmdline/run marker missing, later starts uncontrolled. NBD/timing/user history and stable current boot ID corroborate association; do not silently label it controlled P2 evidence. Old cached recovery files are not P2 evidence. Current eMMC logcat failures must not be mixed into the diskless cause.

## Current question / next batch

**H HOST_FACT:** the exact accepted system has an independent regular root `/fstab.flox`, inode 26, 4295 bytes, stock eMMC SHA ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764. Its init.flox.rc calls that relative path for early/late mounts. Vendor's patched file is separate; root is not a symlink. Namespace mismatch proven; Phase5 first-stage acceptance remains frozen.

**I HOST_FACT:** separate system/disk derivative built and independently audited on the Mac; two system builds match. Only 2566 bytes differ within the original 4295-byte root-fstab data span. All other filesystem/disk bytes, inode/xattrs, geometry and partitions compare unchanged; both source/derived p1 hashes match their system images. Original golden sources remain intact.

```text
derivative_dir=out/phase6-v2-root-fstab-I/
system_sha256=d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795
disk_sha256=060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a
manifest_sha256=e307d3285e61fc0a4419bdb6a89d672a45792ab65da39bfdddfaa61bed33b3a3
runtime_effect=IMPLEMENTED_UNPROVEN / PROPOSED_DIAGNOSTIC
```

**J HOST_FACT:** automatic console-first ADB collector passes simulated offline/new boot/root-return, raw binary and identity-change tests. REAL_DEVICE_FACT: baseline-only capture from current unchanged root eMMC boot succeeds; previous console hash remains c494dc5e...760497. No reboot/root restart occurred. A future first-visible ADB still does not automatically prove first-successor provenance. Details: `PHASE6_V2_AUTOMATIC_CONSOLE_CAPTURE.md`.

**K HOST_FACT:** composed preflight freshly passes unchanged original frozen/P2 gates, exact regenerated P2 boot, independent full-byte derivative audit, disk structure and two matching derivative-specific maps. Trace-map SHA 4a70e1c1ceb1933ba840c73b77b67bfcbd1429a2fa2aa360f3381be2856fd90b. No device command/export ran.

**L/R1 conditional activation:** fresh current-device/port/full-disk/input readiness passed at starting HEAD a23e2ad. The committed R1 plan/total design permits one ADB-to-stock-bootloader transition, one pinned lk2nd RAM boot and one exact P2 diagnostic boot with the derivative disk, after healthy USB/console observers are armed. No flash/erase/retry/recovery boot. Binary question is both cache/p3 and persist/p6 filesystem READ evidence on one NBD connection; old Phase6-E p3-OR-p6 classifier remains separate. Exact P2 boot/kernel/transport/handoff/rc stay unchanged. This is a documented single-use exception, not authority conferred by HOST_PASS; restore pause after an attempt. No new runtime result exists at activation. Details: `PHASE6_ROOT_FSTAB_RUN_R1.md`.

F6-018 preflight refresh is repaired and host-verified. F6-019 requires remote Git operations. F6-020/021/022 record observer schema, wildcard export and lk2nd predicate lessons. F6-023/024 record the latest causal/namespace corrections.

## Execution hosts

Coordinator edits locally; Mac builds, full gates, Git and device work execute through `ssh zhangjw@192.168.1.63`, repo `/Users/zhangjw/nexus7_test`. `/Volumes/zhangjw` is its SMB view. Use SCP for independent snapshots and verify destination hashes. USB NBD exports bind only `172.16.42.2`, never wildcard/management addresses. Notify user if Debian compilation is required; none was needed for current host work.

## Active evidence

```text
DISKLESS_V2_EXECUTION.md
diskless-v2/WORKLOG.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
diskless-v2/PHASE6_V2_RUN1_POSTMORTEM.md
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P1.md
diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P2.md
diskless-v2/PHASE6_V2_PREVIOUS_CONSOLE_CAPTURE.md
diskless-v2/PHASE6_SECOND_STAGE_FSTAB.md
diskless-v2/PHASE6_V2_AUTOMATIC_CONSOLE_CAPTURE.md
diskless-v2/PHASE6_ROOT_FSTAB_RUN_R1.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/PHASE6_FAILURE_F6_013.md
diskless-v2/PHASE6_FAILURE_F6_014_TO_F6_016.md
diskless-v2/PHASE6_FAILURE_F6_017.md
diskless-v2/REMOTE_WORKFLOW.md
diskless-v2/audits/2026-10-30-f6018-host/SUMMARY.txt
diskless-v2/audits/2026-10-30-P2-late-transition/
diskless-v2/audits/2026-10-30-previous-NBD-console/PROVENANCE.json
```
