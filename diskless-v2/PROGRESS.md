# Diskless v2 — Current checkpoint

Authority: complete AGENTS, total design, this checkpoint, latest WORKLOG, active phase documents and failure records. Conversation memory is not project state.

```text
branch=diskless-v2
Phase1-5=ACCEPTED/FROZEN (Phase5 device proof: first-stage p1/p2)
Phase6-E/F=PASS by R1/Q1 filesystem + attributable console evidence
Phase6-G=Q1 GSS panic localized; Q2 GPS-unavailable profile reaches desktop
core diskless Android UI boot=PASS / REAL_DEVICE_FACT, Q2
Phase7=GApps derivative HOST_PASS / first device run reserved for user M1
hardware=M1 user-operated conditional startup only; no agent boot/reset/flash
current device=live Q2 desktop; same gadget registry4295016541/location336789504
preserve=server12963 + caffeinate14159 + USB/Mac + current writable disk
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

## Proven progress and historical blocker

H/I/R1: original system had a separate stock root fstab, distinct from patched boot/vendor. One-file derivative directly proves cache/persist/data NBD mounts and late-fs/post-fs-data. R1 later stalled; late ext4 panic captured, independence from manual action UNKNOWN. Long startup stall already failed validation; precise user keypress recall is not required and does not justify passive waiting.

M/N: old managed guards cover USB power/suspend/gadget, not L3 policy. HOST_FACT exact netd code/embedded symbols show nonzero-priority rule flush and32000 unreachable fallback; runtime RPDB not captured. O independently host-built one added pref0,to172.16.42.2/32,lookup main rule with fail-closed readback before NBD; all other image bytes/mechanisms unchanged, fresh disk byte-identical to R1 pre-run.

P/Q1 REAL_DEVICE_FACT: target rule marker6.153594s;one connection18345 replies(17156 reads719774720B,1189 writes29736960B),successful span97.950304s versus R1 approximately11s. Binary YES and system_server reached. This validates the controlled route-protected input, not exclusive causality or a post-netd RPDB snapshot.

User-controlled successor capture saved130302 bytes at root/constant boot389cb03f-aa51-4516-a245-4a8f08f29a3d uptime15.92->16.78:

```text
console_sha256=43d12aa2ed4bff986198335fa213e81c1c6101303c9d9f7faa6a1d2c35867cae
archive=audits/2026-10-30-root-route-Q1/
```

Full diskless head/unique peer-rule marker/sole Q1 boot and USB-user sequence establish Q1 attribution; first-visible ADB alone is not first-successor proof. Console: GSS firmware load105s,reset release106s,repeated fatal/SMSM_RESET/restart_level3,then primary subsystem_restart_wq_func powerup panic107.166s. GSS internal reason UNKNOWN(smem_get_entry failed). Other CPUs' interrupted qtaguid/TCP/NBD stacks are stopping contexts, not panic origin. Later host TCP timeout is not initiating-cause proof. Q1 did not establish full boot; Q2 below subsequently reaches desktop.

Q source audit and R isolated GPS-null artifact gates are complete. No kernel rebuild/blanket peripheral disable selected. Notify user if future work needs Debian compilation. Use bounded decisions and prepared capture for failed starts; preserve successful live operation.

## Execution / active documents

Q SOURCE_PROVEN: pinned gss_open->pil_get and SMSM_RESET->SSR powerup-overlap guard match captured primary panic. HOST_FACT: exact firmware/HAL activation audited; gps.disable does not guard C HAL entry. R changes exactly4 GPS HAL bytes to return NULL, preserving all other Q1 inputs. PHASE6_GSS_AUDIT.md and PHASE6_GPS_NULL_PREPARATION.md retain source/preparation history.

R HOST_FACT: four-byte GPS-null vendor/disk derivative independently audited, boot unchanged50377dc8...f99c799. PRE-RUN disk3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811, vendor7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996. Exactly4 changed bytes versus pristine Q1; all other metadata/partitions unchanged. Current disk has runtime/user-setup writes; never use that pre-run hash as its present identity.

S/Q2 CLOSED: execution9818dd26774fff4aee3da308a2011b583ec257e6; one lk2nd/one Q1-image RAM boot, completed09:59:15UTC. REAL_DEVICE_FACT: user completed initialization and reached desktop without observed crash. Same gadget/single active NBD session at10:12:18UTC:25742 replies,818136064 read bytes,89602048 write bytes; request progress beyond742s. Core diskless UI boot PASS. No Q2 console/sys.boot_completed readback; console-specific GSS criterion NOT_EVALUATED, internal cause/other functions/long-term stability UNKNOWN. User accepts GPS unavailable. No successor reboot performed: preserve successful operation per user steering. Evidence: audits/2026-10-30-gps-null-Q2/; detailed result PHASE6_GPS_NULL_RUN_Q2.md.

Live disk out/phase6-v2-gps-null-R/disk.raw.img now contains user setup; preserve privately, never overwrite or commit it. Root server12963 on172.16.42.2:10810 and caffeinate14159 remain running. USB/ADB/sampler12844/12845/12849 stop at1200s; independent server persists. No new boot/experiment authorized. Next question: normal feature verification and reproducible packaging of this working GPS-unavailable profile. User asks how to add GApps Pico; installation approach is advisory only until a separate image-derivative plan exists. Do not modify live disk.

T formal preservation: /Users/zhangjw/nexus7/releases/20261030-Q2-gps-off/ (coordinator /Volumes/zhangjw/nexus7). Clean master exactly matches pre-run Q2 hash3cf28c...e811; private online snapshot3032f399...eb400 has filesystem consistency UNVERIFIED, not clean-shutdown/boot-tested backup. Exact boot/bootstrap/server tools, hashes, launcher and runbook preserved; writable daily disk prepared. New launcher hardware execution IMPLEMENTED_UNPROVEN; current running path/server untouched. See PHASE7_RELEASE.md and total design§17.

User now explicitly requests GApps on a separate image; supplied ZIP retained under nexus7/inputs/, SHA4df52af6b0dcc0f21d6e1dd943ef3088121354179782b9d0d48593ff127b4cc0, CRC/internal arm11.0sdk30pico metadata valid. Debian host supplied: debian@192.168.1.200. Next U is exact installer/environment audit and host-only derivative preparation, not another boot/live-root edit. Earlier advisory-only wording above is superseded by this explicit request; no GApps hardware run plan yet.

U CLOSED host preparation: formal GApps release /Users/zhangjw/nexus7/releases/20261030-gapps-pico/ (same SMB root). Original ARM11 Pico installer runs unchanged in isolated Debian KVM/ARM guest, skipswypelibs omits broken optional gesture aliases. H restores one generated keyboard symlink label; no policy/kernel/rc/transport change. Independent34-file/20-directory/1-symlink ownership/mode/context/resolution checks and e2fsck PASS. Protected init/netd/root-fstab/policy unchanged. System SHA98e58fa4070666b4f1ff5ab7d8c15617bf1237fa4e0c0f3cee617031a4d62401. Whole master SHA70e4caad543835d0f9f61de64de1f22265bedbc9365ccfdfc7f89b72340832f9; outside p1 byte-identical to clean Q2. Fresh writable disks/daily.raw.img prepared. GApps runtime IMPLEMENTED_UNPROVEN. Original Q2 release/online snapshot/current service untouched. F6-030/031/032 record rejected host candidates and repaired metadata/logging gates. Safe reports: audits/2026-10-30-gapps-{system-audit,package}.json; full private evidence nexus7/gapps-work and Debian nexus7-gapps-U.

Exact next handoff: user requests to perform first GApps boot themselves. PHASE7_GAPPS_MANUAL_RUN_M1.md binds hashes/question/gates/stops; user-only conditional sequence after U commit. User enters verified stock fastboot, uses guarded stop-nbd for old recognized service, arms new serve, then one lk2nd/one accepted boot.img RAM boot. No agent transition/automatic retry/flash. New launcher records USB900s/NBD5s/boot journal; observation cap never stops root export. Agent issued0 physical device commands in U. New user data requires initialization; current original12963/14159 stay until user transition. Runtime Play/long-term stability still UNKNOWN.

Coordinator edits; Mac builds/gates/Git/device operations via ssh zhangjw@192.168.1.63,repo /Users/zhangjw/nexus7_test. /Volumes/zhangjw is its SMB view; Git only remotely. SCP independent snapshots/compare before execution. Export only172.16.42.2,no wildcard/management bind. PHASE7_RELEASE.md and PHASE7_GAPPS_MANUAL_RUN_M1.md are additionally active.

Active: DISKLESS_V2_EXECUTION.md;WORKLOG;PHASE6_ROOT_ROUTE_RUN_Q1.md;PHASE6_ROOT_ROUTE_PREPARATION.md;PHASE6_NETD_ROUTE_AUDIT.md;PHASE6_TRANSPORT_COVERAGE_AUDIT.md;PHASE6_ROOT_FSTAB_RUN_R1.md;PHASE6_SECOND_STAGE_FSTAB.md;PHASE6_V2_AUTOMATIC_CONSOLE_CAPTURE.md;PHASE6_AUDIT_V2.md;PHASE6_V2_REAL_DEVICE.md;PHASE6_V2_RUN1_POSTMORTEM.md;PHASE6_FAILURE_LOG.md and split F6_013/F6_014_TO_F6_016/F6_017;REMOTE_WORKFLOW.md. Historical P1/P2/reset/previous-console documents remain linked through R1;permissions consumed and finite-hold causal support REVOKED.
