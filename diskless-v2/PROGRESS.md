# Diskless v2 — Current checkpoint

Authority: complete AGENTS, total design, this checkpoint, latest WORKLOG, active phase documents and failure records. Conversation memory is not project state.

```text
branch=diskless-v2
Phase1-5=ACCEPTED/FROZEN (Phase5 device proof: first-stage p1/p2)
Phase6-E/F=PASS by R1/Q1 filesystem + attributable console evidence
Phase6-G=current blocker: Q1 GSS subsystem-powerup panic
full diskless Android boot=NOT_PROVEN
Phase7=NOT_REACHED
hardware=Q2 CONDITIONAL SINGLE-USE EXCEPTION / no other boot, flash or recovery authorization
current device=stock fastboot,07a117ae,productflo,physical location336789504
all Q1-owned export/sampler/observers=stopped after verified fastboot
```

## Exact inputs / demonstrated baseline

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
original_continuation_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
P2_panic_hold_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
Q1_route_image_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
Q1_wrapper_sha256=adf5ad9b4dafcdba8c3796208000c051c89e8a7c1272601a69f4a42d472a855e
root_peer_block_sha256=08f50f97201f622389a5f276929c68722b9125d0c3713e1c2ac8c36415669e65
golden_system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
root_fstab_system_sha256=d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795
R1_and_Q1_prerun_disk_sha256=060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a
Q1_artifacts=out/phase6-v2-root-route-O/artifacts/
Q1_run=out/phase6-root-route-Q1/
```

Preserve BusyBox path/shebang, layout path, single ECM/NBD session, Phase5 attach/retry/liveness/partition checks, original init.android handoff and mapping. Future isolated work retains the Phase6 root-fstab correction and Q1-demonstrated peer rule unless directly invalidated. Golden sources intact; runtime-written R1/Q1 disks are evidence, not pristine retry inputs.

## Proven progress and remaining blocker

H/I/R1: original system had a separate stock root fstab, distinct from patched boot/vendor. One-file derivative directly proves cache/persist/data NBD mounts and late-fs/post-fs-data. R1 later stalled; late ext4 panic captured, independence from manual action UNKNOWN. Long startup stall already failed validation; precise user keypress recall is not required and does not justify passive waiting.

M/N: old managed guards cover USB power/suspend/gadget, not L3 policy. HOST_FACT exact netd code/embedded symbols show nonzero-priority rule flush and32000 unreachable fallback; runtime RPDB not captured. O independently host-built one added pref0,to172.16.42.2/32,lookup main rule with fail-closed readback before NBD; all other image bytes/mechanisms unchanged, fresh disk byte-identical to R1 pre-run.

P/Q1 REAL_DEVICE_FACT: target rule marker6.153594s;one connection18345 replies(17156 reads719774720B,1189 writes29736960B),successful span97.950304s versus R1 approximately11s. Binary YES and system_server reached. This validates the controlled route-protected input, not exclusive causality or a post-netd RPDB snapshot.

User-controlled successor capture saved130302 bytes at root/constant boot389cb03f-aa51-4516-a245-4a8f08f29a3d uptime15.92->16.78:

```text
console_sha256=43d12aa2ed4bff986198335fa213e81c1c6101303c9d9f7faa6a1d2c35867cae
archive=audits/2026-10-30-root-route-Q1/
```

Full diskless head/unique peer-rule marker/sole Q1 boot and USB-user sequence establish Q1 attribution; first-visible ADB alone is not first-successor proof. Console: GSS firmware load105s,reset release106s,repeated fatal/SMSM_RESET/restart_level3,then primary subsystem_restart_wq_func powerup panic107.166s. GSS internal reason UNKNOWN(smem_get_entry failed). Other CPUs' interrupted qtaguid/TCP/NBD stacks are stopping contexts, not panic origin. Later host TCP timeout is not initiating-cause proof. Full Android boot remains NOT_PROVEN.

Next binary source question: does exact pinned GSS/SSR code explain this powerup panic independently of NBD? Audit call path and exact firmware inputs before selecting one minimal diagnostic. No blanket peripheral disable, runtime patch, kernel rebuild or new boot authorized. Notify user if a selected diagnostic needs Debian compilation; none selected yet. Use bounded decisions and prepared successor capture, not spontaneous-reboot waiting.

## Execution / active documents

Q SOURCE_PROVEN: pinned gss_open->pil_get and SMSM_RESET->SSR powerup-overlap guard match captured primary panic. HOST_FACT: exact firmware/HAL activation audited; gps.disable does not guard C HAL entry. Next host-only diagnostic changes exactly4 GPS HAL bytes to return NULL(GPS temporarily unavailable),preserving Q1 boot/kernel/route/root-fstab/other disk data. Runtime unproven/hardware paused; no kernel compile/Android rc edit selected. PHASE6_GSS_AUDIT.md is additionally active.

R HOST_PASS: four-byte GPS-null vendor/disk derivative independently audited, boot unchanged50377dc8...f99c799. New disk3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811, vendor7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996. Exactly4 changed bytes versus pristine Q1; all other metadata/partitions unchanged. Runtime unproven/no boot authorization from R. Next is separately committed Q2 single-run plan/current gates. PHASE6_GPS_NULL_PREPARATION.md is active; no kernel compile needed.

S/Q2 conditional activation: one verified stock->lk2nd RAM boot and one exact Q1 image boot with R's four-byte GPS-only disk after current gates/armed offline capture. Initial180s,max300 only while I/O progresses;60s no progress leads to controlled console capture. No flash/retry/other boot. PHASE6_GPS_NULL_RUN_Q2.md governs this single-use exception; no runtime result at activation.

Coordinator edits; Mac builds/gates/Git/device operations via ssh zhangjw@192.168.1.63,repo /Users/zhangjw/nexus7_test. /Volumes/zhangjw is its SMB view; Git only remotely. SCP independent snapshots/compare before execution. Export only172.16.42.2,no wildcard/management bind.

Active: DISKLESS_V2_EXECUTION.md;WORKLOG;PHASE6_ROOT_ROUTE_RUN_Q1.md;PHASE6_ROOT_ROUTE_PREPARATION.md;PHASE6_NETD_ROUTE_AUDIT.md;PHASE6_TRANSPORT_COVERAGE_AUDIT.md;PHASE6_ROOT_FSTAB_RUN_R1.md;PHASE6_SECOND_STAGE_FSTAB.md;PHASE6_V2_AUTOMATIC_CONSOLE_CAPTURE.md;PHASE6_AUDIT_V2.md;PHASE6_V2_REAL_DEVICE.md;PHASE6_V2_RUN1_POSTMORTEM.md;PHASE6_FAILURE_LOG.md and split F6_013/F6_014_TO_F6_016/F6_017;REMOTE_WORKFLOW.md. Historical P1/P2/reset/previous-console documents remain linked through R1;permissions consumed and finite-hold causal support REVOKED.
