# Phase6 Q2 — GPS-only interface deferral

Status: CLOSED / REAL_DEVICE_FACT: setup completed and desktop reached without user-observed crash. Q2 boot authorization consumed; preserve the live NBD root. Batch S starts atc09c5260c00d7b296cc4d43a5a05816821a01168 after R closed. The original predeclared single-run plan follows; actual results and user-directed preservation below govern current operation.

Binary question: does deferring the audited GPS HAL activation prevent Q1's GSS powerup panic and allow progress beyond that107s boundary? Sole runtime delta from Q1 is4 GPS HAL bytes returning NULL. Q1 boot/kernel/route/root-fstab/firmware/rc/SELinux/initial writable partitions remain unchanged. GPS temporarily unavailable; no permanent feature-fix claim.

```text
boot=out/phase6-v2-root-route-O/artifacts/diagnostic.img
boot_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
disk=out/phase6-v2-gps-null-R/disk.raw.img
disk_sha256=3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811
vendor_sha256=7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996
manifest_sha256=9a040b59379961ce3039575fd459d86052b9760576c7d2523352d1f3d23f20e8
trace_map_sha256=23ba156c7c9859bc83ee03342f07d305e82fd96403613323d72041a954c1c5d9
bootstrap_sha256=a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a
serial=07a117ae;location336789504;export172.16.42.2:10810 only
run=out/phase6-gps-null-Q2/
```

Require R independent ELF/vendor/full-disk/metadata/source/p2/hash/structure/map gates, fresh original fact producer in Q2, current exact boot/disk/manifest/map/stock-fastboot identities and clean tracked source. Arm1200s USB/offline console-first ADB(--root-on-return,--start-offline) and deferred USB-only unchanged server before transition. Fresh armed/USB records and healthy PIDs required; no listener/test connection before proper dedicated gadget endpoint.

From stock productflo/PID4ee0, RAM-boot pinned lk2nd once; verify actuallk2nd-msm8960/PIDd00d,same serial/port(empty version allowed),then RAM-boot exact Q1 image once. Record counts before attempts. No flash/erase/ADB reboot/retry/recovery boot. First NBD request within120s or stop INCONCLUSIVE.

Active observation initially180s; only continuing newly completed I/O permits one120s extension(max300s). At60s reply inactivity,obtain console instead of waiting for automatic reboot; normal idle after unverified boot is not itself panic proof. On boundary/requested capture,prompt one user hard reboot into eMMC and save first-visible root last_kmsg before diagnostics. No remembered keypress/screen-watching requirement. Keep live root export until verified successor/no NBD or fastboot.

YES: attributable same-run console progresses beyond130s without GSS startup/powerup panic,with continued NBD/userspace progress; direct boot_completed/home evidence is stronger and must be separately stated. NO: same GSS activation/panic recurs on verified inputs. Earlier unrelated failure,missing identity/attach/trace,partial/unattributable console or insufficient post-boundary evidence is INCONCLUSIVE. Full Android boot requires direct same-run evidence; absence in a truncated log is insufficient.

Preserve exact plan/commit/hashes/preflight,full USB/NBD/stats/ADB/commands/PIDs/user-transition notes/result/SHA and written disk. Attempt consumes exception,restore pause;safe process-state/documented close before another experiment. No source/firmware fix selected by this run.

## Actual result / live-runtime handoff

Execution HEAD9818dd26774fff4aee3da308a2011b583ec257e6. Fresh original fact producer/current input and stock/lk2nd identity checks passed. Exactly one bootstrap and one diagnostic RAM boot; diagnostic command completed2026-10-30T09:59:15.036924UTC. No flash/erase/retry. Since09:59:23.797503UTC, same gadget registry4295016541 at location336789504; one NBD connection, no observed fallback USB transition.

REAL_DEVICE_FACT: user first reported setup UI, then explicitly accepted GPS omission and continued normal initialization, then reported: “ok. 我已经完成了设置进入了桌面，没有崩溃出现”. At10:12:18.221916UTC snapshot: active connection1,25742 completed replies,818136064 read bytes,89602048 write bytes; successful requests span beyond742s of server time, well beyond Q1's107s panic boundary. This establishes core diskless Android startup through setup and desktop for the explicit GPS-unavailable profile. It does not establish long-term stability or every peripheral.

The plan explicitly allowed direct home evidence as stronger separate evidence. Behavioral startup question is positive. Console-specific GSS criterion is NOT_EVALUATED: no Q2 kernel console was captured and absence of GSS activation cannot be independently claimed. After success the user's normal-setup instruction superseded destructive successor capture and the failed-start observation cap; preserve the working system instead of rebooting it for last_kmsg. sys.boot_completed readback, GSS internal failure reason and other feature behavior remain UNKNOWN. GPS NULL profile is now an explicitly user-accepted feature limitation; restoration is optional future work, not a prerequisite to this desktop milestone.

Immutable evidence prefix: audits/2026-10-30-gps-null-Q2/, cut10:12:18UTC, SHA256SUMS. Original logs continue under out/phase6-gps-null-Q2/. Root export PID12963 remains bound only172.16.42.2:10810, backed by out/phase6-v2-gps-null-R/disk.raw.img. Idle-sleep guard14159 is caffeinate -i -w12963. Keep USB/Mac/export running. USB observer12844, ADB watcher12845 and sampler12849 have1200s caps; the root server independently persists afterward. No monitoring cap authorizes stopping root storage.

The disk now contains completed user setup, is no longer pristine, and its recorded3cf28c...e811 hash is PRE-RUN ONLY. Do not overwrite/export it as a fresh diagnostic or commit private userdata. Preserve original golden inputs and R's pristine Q1 clone separately. No new boot/experiment authorized. Next question is normal-function verification and packaging this reproducible GPS-unavailable baseline; no runtime redesign or GPS repair selected.
