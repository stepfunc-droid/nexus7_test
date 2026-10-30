# Phase6 root-route Q1 — single-use controlled test

Status: CONDITIONALLY AUTHORIZED ONCE / runtime effect unproven. Batch P starts atb807d1f771883ae0352d08a214119991d18c9b38 after O closed. User explicitly requested starting the prepared test. This committed plan/total design authorizes only the sequence below after fresh gates and armed-observer checks.

Binary question: does the sole root-peer priority0/main rule let successful NBD I/O continue beyond R1's initial approximately20s cutoff? Sole runtime delta from R1: the pinned route-rule/precondition fragment in /init. Kernel/BusyBox/sysctls/USB/NBD attach-retry/handoff/Android rc/SELinux and initial disk bytes remain fixed. No netd bypass.

Exact identities inherit O's audited table in PHASE6_ROOT_ROUTE_PREPARATION.md:

```text
image=out/phase6-v2-root-route-O/artifacts/diagnostic.img
image_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
disk=out/phase6-v2-root-route-O/artifacts/disk.raw.img
disk_sha256=060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a
manifest_sha256=059644adca6f27990c8a4644143c3229f33bab21d288175d8fe66fe99524fa70
trace_map_sha256=abe8b46bdb319c32911ed3d5ac8bc5a53799803da8b6bd83678d1deda1203763
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
bootstrap_sha256=a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a
serial=07a117ae; USB_location=336789504; export=172.16.42.2:10810 only
run=out/phase6-root-route-Q1/
```

Preflight: O deterministic/independent image/full-byte pristine disk gates and tests passed; rerun original frozen-fact producer into fresh Q1 report, fresh route image audit and current hashes/device identities. Require clean tracked source and no current listener. Arm900s USB/console-first ADB watcher(--start-offline,--root-on-return) before any transition; require armed/fresh USB records and healthy PIDs. Defer unchanged protocol export until correct dedicated Ethernet gadget/address exists. Use new disk/map only, no test connection. Host PASS alone grants no hardware permission.

From verified stock fastboot(product flo,VID18d1:4ee0), RAM-boot pinned lk2nd once; verify actual productlk2nd-msm8960,serial/physical port/PIDd00d (empty version allowed); RAM-boot the route diagnostic once. No flash/erase/ADB reboot/retry/recovery boot. Count/persist attempts before commands. Missing identity or gate stops before next command; first NBD request required within120s.

Observe actively for at most180s after diagnostic command. After initial attach,60s with no newly completed reply means switch to console retrieval, not more passive waiting. YES: one comparable session with cache/persist gates and a successful later reply >=30s after first request (well past R1's11s reply span), or attributable console proves full Android boot after netd. This proves continued I/O with the diagnostic, not an actual RPDB snapshot or exclusive initiating cause. NO: comparable boundary still stalls and attributable console confirms failure to pass it. Missing attach/identity/trace/provenance or unresolved normal-idle-vs-stall is INCONCLUSIVE. Preserve narrower observations separately; full Android boot requires direct same-run evidence.

At the stall decision or180s, prompt one user-controlled hard reboot into eMMC for the already-armed first-visible ADB capture. Do not ask for screen watching or remembered timestamps. Save last_kmsg first, then root/boot/mount identity; new root-rule marker distinguishes Q1, first-visible is not automatically first successor. No automatic reboot wait. Keep export while a live NBD root may depend on it; stop only after verified successor eMMC/no NBD or fastboot. Preserve complete trace/stats/USB/ADB/commands/PIDs/artifact hashes/result/SHA and runtime-written disk. Attempt consumes exception; restore pause and close/commit P before another experiment. No spontaneous-panic/reset claim from manual transition.
