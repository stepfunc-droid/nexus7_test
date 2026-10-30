# Phase6 root-route Q1 — single-use controlled test

Status: CLOSED / BINARY YES / GSS POWERUP PANIC CAPTURED / AUTHORIZATION CONSUMED. Batch P starts atb807d1f771883ae0352d08a214119991d18c9b38 after O closed. The conditional procedure below is consumed history; final results govern current state.

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

## Final result

Execution HEAD6c7945bc272396f90ea7c9ee5e46b901275090eb. Fresh original fact producer/current route audit/full image+disk hashes/device identities passed. One lk2nd/one diagnostic RAM boot, diagnostic completed09:19:38.317733UTC; no flash/retry/extra ADB reboot. One NBD session18345 replies:17156 READs719774720B,1189 WRITEs29736960B,p1 reads683570176B. First request1.242402s,last successful reply99.192706s,span97.950304s. Cache/persist/userdata gates reached. Q1 binary YES/REAL_DEVICE_FACT: I/O extends beyond R1's approximately11s span; no exclusive cause or post-netd RPDB snapshot claimed.

User reported boot animation then stopped animation. At the bounded180s decision, prompted controlled successor capture; user confirmed manual reboot. Watcher saved130302-byte console SHA43d12aa2ed4bff986198335fa213e81c1c6101303c9d9f7faa6a1d2c35867cae at09:23:16.986462UTC, successor389cb03f-aa51-4516-a245-4a8f08f29a3d UID0/boot stable,uptime15.92->16.78. Full diskless head/unique root-peer marker6.153594s/sole Q1 boot and USB/user sequence establish named attribution; first-visible ADB alone does not prove first successor.

Console REAL_DEVICE_FACT: rule precondition passed; NBD mounts/late-fs continue and system_server is identified at76/88s. GSS firmware gss.mdt/b02..b11 loads from105s,reset release106.083s,then GSS SMSM_RESET/fatal/restart_level3 at106.222s and repeated recovery. Primary panic107.166107s: subsystem_restart_wq_func, Subsystem died during powerup, with direct panic stack. GSS internal reason UNKNOWN(smem_get_entry failed). Other CPUs' stopping stacks include qtaguid/TCP/NBD and are not panic origin. Host request-header TCP timeout at152.907s is later and not cause proof. Full Android boot NOT_PROVEN.

After capture ADB became unavailable and a cleanup guard stopped nothing. Read-only checks then verified stock fastboot/same serial/port/product; all Q1-owned export/sampler/USB/ADB processes stopped safely. No operator inferred for later fastboot transition. Current device fastboot, hardware PAUSED, permission consumed. Written disk retained; full evidence/result/provenance/SHA in audits/2026-10-30-root-route-Q1. Next: pinned GSS/SSR call-path and exact firmware-input audit, preserving demonstrated root-fstab/peer-route progress; no new boot or kernel rebuild authorized.
