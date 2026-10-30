# Phase6 V2 panic-hold Run P1 — controlled execution plan

Status: **CLOSED BEFORE DIAGNOSTIC BOOT / RESET QUESTION INCONCLUSIVE / AUTHORIZATION CONSUMED**.

This is the first named panic-hold run, distinct from the earlier Audit-V2 continuation Run1. The user instructed continuation after host-validation batch C and confirmed availability to observe the physical screen. Preparation batch D starts at `f585b41dc01eb8624cf4311476d21bd31a8c36c0`. No device boot occurred in D.

## Question and single causal variable

Did a Run1-comparable reboot depend on Linux panic-timeout auto-restart? Change only `kernel.panic` from the baseline target 5 to 0; retain `panic_on_oops=1`, frozen kernel/transport/handoff/Android inputs and stock enforcing policy. The diagnostic's fail-closed read-back precedes NBD attach. This does not classify all kernel/userspace reset paths.

## Frozen input and host identities

Execution is through SSH on `zhangjw@192.168.1.63`, repository `/Users/zhangjw/nexus7_test`.

```text
physical_device=07a117ae / flo
USB_locationID=336789504
existing_bootstrap=out/lk2nd-flo-fastboot.img
bootstrap_sha256=a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a
diagnostic_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
baseline_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
original_traced_server_git_blob=8046084119a1c12a72465b87d5afb450a2071311
observed_server_sha256=07109f683e954075aead0d0f253a30d77b81cad6e06bc95c176a2278df91729c
USB_observer_sha256=1aca1eb7c160c3cc3e7ce3ec13af35f52fa13a5e2a53e19bab0becfc48bf1bf3
observer_selftest_sha256=9e5dab0a6f865bd8806208fb637d2c347ed9f05b01de02ab923454ee85594d17
disk=/Users/zhangjw/nexus7-diskless-v2/diskless-v2-android.raw.img
system_byte_range=[1048576,1573912576)
```

Full disk identity is recorded in `audits/2026-10-30-observation-host/disk-before.sha256`; all accepted source/fstab/partition identities remain those in the batch-C frozen report. Recheck full disk SHA before export and refuse a mismatch. The current bootstrap identity is a `HOST_FACT` binding of the existing artifact; do not describe a newly verified bootstrap source build. Reuse the repository's existing two-stage RAM-only flow (`build-lk2nd.sh`), with no bootstrap rebuild or flash.

The dedicated saved `RNDIS/Ethernet Gadget` host network service is now manual `172.16.42.2/24`, router `0.0.0.0`. The configuration command succeeded without sudo and was read back. No effective USB gateway or management-network change is intended. If the Linux gadget gets a different newly created service, identify it from the same physical USB port and configure only that service to the same accepted endpoint; preserve the actual command and result. Do not guess a management interface.

## Prepared observation / HOST_FACT limits

`phase6_v2_nbd_observed_server.py` imports and pins the original traced-server bytes. It delegates original protocol and reply calls unchanged, recording completed replies only after the original reply function returns. SIGUSR1 writes host statistics without closing the connection or adding a socket timeout. Completed p1 byte counts use the frozen geometry above. A sampled generic `stats.phase` is not itself a completion record; `last_completed_reply` is the explicit completed-reply observation.

The new entrypoint passed READ/WRITE/FUA/FLUSH/TRIM/invalid/unsupported/DISC protocol and final-disk differential checks against the accepted Phase3/4 server in read-write and read-only cases. An idle-connection self-test proves three SIGUSR1 snapshots preserve the completed READ and permit another request on the same connection. Original server files are unchanged. This is host logging, not a new Nexus-side observer or accepted runtime architecture.

`phase6_v2_observe_usb.py` samples the target physical port/serial every 0.5s, preserving UTC, monotonic elapsed time, registry ID, VID/PID and errors. A 2s read-only dry run succeeded. It supports actual macOS plist dictionary/list roots. Distinct registry IDs identify reenumeration; USB disappearance alone is not a reboot classification. The user will additionally report screen changes.

No packet capture is required. The SSH user lacks noninteractive sudo/BPF access, and no privileged capture, kernel change or Android logger will be introduced for this run.

## Gates and exact procedure

1. Preparation D must be committed, with observer source/test evidence and authoritative authorization synchronized. Confirm clean tracked state remotely, exact source hashes, one expected fastboot device, no other NBD listener/client, enough host disk space, and the saved endpoint configuration.
2. Create `out/phase6-v2-panic-hold-P1/` without overwriting an earlier run. Persist a run journal and exact command exit statuses. Re-run the repaired panic-hold real preflight using batch-C baseline/tracer reports and separate P1 fact/diagnostic report/image paths. Require its final PASS, exact expected image SHA and `hardware_authorized=no`. Copy reports and raw combined output into P1. Verify full disk SHA against preparation D after the preflight and before export.
3. Start the USB observer with `<P1>/usb.jsonl`, serial/location above and a maximum 600s duration, without a server PID initially. Store its stdout/stderr/PID and require actual target-port observations before boot. Arm a host launcher that waits for the dedicated USB interface to obtain `172.16.42.2`; no NBD export exists while that address is absent.
4. Once the Linux USB endpoint exists, the launcher starts the observed server with `--stats-log <P1>/nbd-stats.jsonl --system-range 1048576 1573912576 --bind 172.16.42.2 --port 10810 --name phase6-v2-P1 --trace-map <batch-C-map> --trace-log <P1>/nbd-trace.jsonl <accepted-disk>`. Persist stdout **and stderr** to `<P1>/server.txt`, record PID and actual interface/address, and send SIGUSR1 every 0.5s only after its listening log proves readiness. Do not make a test TCP connection to the real export. Preserve the launcher's exact code/argv/status in the run journal. This ordering uses the unchanged Phase5 NBD retry behavior if a connect attempt precedes listener readiness. The user observes the screen; notify them immediately before the boot transition.
5. On the original stock fastboot, run `fastboot -s 07a117ae boot out/lk2nd-flo-fastboot.img`, saving the entire output and status. Wait at most 30s for the same physical target's lk2nd fastboot; record product/version. If its serial differs, require exactly one fastboot target at the same physical port and inspect its identity before selecting it. Do not select an unrelated device.
6. Once lk2nd is identified, run `fastboot -s <verified-lk2nd-serial> boot <P1-diagnostic.img>` exactly once. Save output/status/time. No `flash`, `erase`, alternate image or automatic retry is authorized.
7. Verify the host endpoint after Linux USB enumeration; record the actual interface/address. Observe NBD, USB and screen concurrently. Classify using the table below and run the existing real-trace classifier on the preserved JSONL/map. Preserve unknowns explicitly.

## Observable boundary and interpretation

Comparable boundary requires exactly one NBD connection and first valid request, at least 16 MiB of successful p1 READ replies, no accepted cache/persist filesystem evidence, and subsequent request/reply inactivity. The threshold operationalizes “substantial” for P1; it does not identify a caller or Android stage. Exact final file/count need not match Run1.

| Observation | Interpretation |
| --- | --- |
| Comparable boundary; replies stop; >=90s without reboot/reenumeration, supported by continuous same Linux USB registry entry or contemporaneous physical screen observation | `panic_timeout_dependency=SUPPORTED`; no panic stack/call-site claim |
| Comparable boundary; stock bootloader or a new boot is observed after the Linux run, while same-run pre-NBD read-back was implied by attach | `panic_timeout_auto_restart=INSUFFICIENT_TO_EXPLAIN_RESET`; not proof of userspace reboot |
| No attach/precondition proof, insufficient p1 traffic, extra NBD session, early transport fault, p3/p6 progression or incomplete reboot/hold observation | `INCONCLUSIVE` for this reset question; separately preserve any valid stage evidence |

USB disappearance or host TCP timeout alone does not distinguish reset, hang, panic or userspace action. No reenumeration while the USB device is absent is not positive hold proof. A physical observation must include its interval and whether anyone touched the device. Nonliteral late sysctl writers remain unproven absent.

## Stop and preservation rules

- Bootstrap failure or missing verified lk2nd within 30s: stop, no diagnostic boot.
- Missing endpoint/first NBD request within 120s of diagnostic boot completion: stop this attempt as INCONCLUSIVE; no automatic second boot.
- Never bind this read-write export to `0.0.0.0`, the management address or another interface. The initial wildcard-listener action was rejected by automatic approval review before any SSH/boot/export action; this plan replaces it with the USB-only address and deferred startup (F6-021).
- More than one NBD session, changed identities, unexpected writes/setup changes, observer failure or evidence loss: do not infer reset cause. Preserve all evidence and stop further boot actions.
- If no new request arrives for >=90s after a comparable boundary, collect physical/USB observation and classify. Keep observing long enough to distinguish a later reset when necessary, within the 600s cap. A timeout alone yields INCONCLUSIVE.
- If p3/p6 evidence or Android progression appears, preserve it; do not terminate an active root-storage server merely because the old boundary was not reproduced.
- Do not auto-reboot the tablet or boot a recovery kernel. Optional persistent-RAM capture is a subsequent controlled step only after the result is recorded with explicit previous-boot provenance.
- Stop only this run's observer/server processes when their connections are known inactive or the outcome/cleanup is explicitly recorded. Never kill an unrelated listener. Record whether a live root-storage session remains.

Preserve under P1: preflight, host reports, source/image/disk identities, command journal, both boot outputs/statuses, NBD trace, server transcript, completed-reply snapshots, USB timeline, endpoint observations, physical observation notes, classifier output and result. Commit the detailed result and synchronize design/checkpoint/worklog before any new experiment.

## P1 actual outcome

Fresh preflight and full disk identity passed. The wildcard-export action was rejected before execution; the revised USB-only launcher never started an export because no Linux USB endpoint appeared. Exactly one bootstrap RAM boot returned success and produced the same physical device/serial at USB PID `0xd00d`. Read-back is `product: lk2nd-msm8960`; `version-bootloader` is empty (`REAL_DEVICE_FACT`).

The command helper incorrectly required “lk2nd” in the version field and therefore timed out its identity guard. No diagnostic image was booted, no NBD connection/export occurred, and no reset-cause conclusion is possible. P1 is closed as `NOT_EXECUTED / INCONCLUSIVE`; its authorization is consumed. The device remains in verified lk2nd fastboot. Only this run's host observer/waiter was stopped. Evidence: `audits/2026-10-30-P1-preboot/`.

F6-022 records the mistaken version-field assumption. A subsequent separately documented attempt may start from the already-loaded, reverified lk2nd without repeating the bootstrap. This historical P1 plan does not authorize that attempt.
