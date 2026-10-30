# Phase6 Q2 — GPS-only interface deferral

Status: CONDITIONALLY AUTHORIZED ONCE / runtime unproven. Batch S starts atc09c5260c00d7b296cc4d43a5a05816821a01168 after R closed. Under the ongoing diskless task, this committed plan/design permits only the guarded single run below.

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
