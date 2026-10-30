# Phase6 V2 panic-hold Run P2 — direct diagnostic from verified lk2nd

Status: **COMPLETED / PRESPECIFIED HOLD OUTCOME MET / CAUSE UNKNOWN / AUTHORIZATION CONSUMED**.

Preparation starts from `a8da61a3bc3b764c410ba3cdecb9cee178b5f455`, after P1 was closed/committed with zero diagnostic boots. The tablet remains in the exact lk2nd loaded by P1's one successful bootstrap command. Do not repeat that bootstrap.

## Binary question / frozen delta

Did a Run1-comparable reboot depend on Linux panic-timeout auto-restart? Single causal variable: `kernel.panic` target 5 -> 0, with fail-closed same-run read-back before NBD and `panic_on_oops=1`. All frozen Phase1–5 kernel/transport/handoff/fstab/Android/SELinux inputs and NBD protocol remain unchanged.

Inherit all artifact hashes, observer identities, system range, >=16MiB successful-p1-read comparability threshold, >=90s hold criterion, interpretation/INCONCLUSIVE limits and preservation requirements from `PHASE6_V2_PANIC_HOLD_RUN_P1.md`. That document is historical; only the total design plus this P2 procedure authorizes the new attempt. No reset-cause result exists from P1.

```text
diagnostic_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
full_disk_sha256=c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9
required_serial=07a117ae
required_USB_locationID=336789504
required_USB_VID_PID=0x18d1:0xd00d
required_current_product=lk2nd-msm8960
version-bootloader=record it; empty is observed and allowed
output_directory=/Users/zhangjw/nexus7_test/out/phase6-v2-panic-hold-P2/
export_bind=172.16.42.2:10810 only
```

The existing live lk2nd identity is a REAL_DEVICE_FACT from P1's controlled load and subsequent read-back. Reverify product, serial/port and USB identity immediately before the diagnostic command. A missing/mismatched identity stops P2; do not repeat bootstrap to make a guard pass.

## Concrete procedure

1. Require committed P2 authorization, clean tracked state, newly passed repaired preflight using separate P2 outputs and the batch-C baseline/tracer reports, exact diagnostic hash and full-disk hash. Preserve both output streams/statuses. Confirm the saved dedicated USB service and available physical screen observer.
2. Start/persist the read-only USB observer for the target serial/port (600s cap), without a server PID. Require valid initial lk2nd samples.
3. Arm the same USB-only deferred launcher that was reviewed for P1, with only output paths changed to P2. Preserve exact source/argv/hash/journal/PID. It waits for `172.16.42.2` on a non-management USB interface and an Ethernet/Gadget device at the target physical port. Then start the pinned observed server bound only to `172.16.42.2:10810`; preserve both output channels and enable SIGUSR1 snapshots after listening readiness. No wildcard bind, privileged capture or test connection to the real export is permitted.
4. Reverify exact current lk2nd identity and observer/launcher health, notify the user, then run `fastboot -s 07a117ae boot <P2>/diagnostic.img` **once** with a persisted transcript/status/time. Record attempted command count before launch. No other state-changing fastboot command is authorized.
5. After Linux enumeration, verify actual USB service/address. If macOS created a new dedicated gadget service, identify it from the same physical USB port and configure only that service to `172.16.42.2/24`, router `0.0.0.0`, recording the exact change. Preserve the accepted client retries and one successful NBD session.
6. Require first NBD request within 120s of diagnostic command completion; otherwise stop as INCONCLUSIVE without another boot. Collect partition trace, completed-reply snapshots, USB registry timeline and physical screen notes. Use the inherited outcome table: comparable boundary + observed >=90s hold supports dependency; comparable boundary + observed reboot makes panic auto-restart insufficient; divergence/incomplete evidence is INCONCLUSIVE. USB loss/TCP timeout alone cannot classify cause.
7. Run the existing trace classifier and preserve a result with all claim limits. Stop only this run's observation processes after result recording; preserve a live root-storage server if Android has progressed. No automatic reboot/retry/recovery boot. Consume the P2 exception after one attempt, restore hardware pause, synchronize and commit results before another experiment.

The P1 host-version predicate error is fixed by checking the actual product/physical identity; no Nexus artifact was changed to accommodate it. P2 is the first attempted diagnostic Linux boot in this sequence.

## Actual result

Exactly one diagnostic RAM boot returned success at `2026-10-30T03:54:43.602615Z`; no additional bootstrap, flash, erase or retry occurred. Linux USB appeared at the same physical port, registry ID `4295014365`, VID/PID `0x0525:0xa4a2`. Saved `en7` configuration supplied the accepted endpoint. The observed server bound only `172.16.42.2:10810` and accepted exactly one connection from `172.16.42.1`.

```text
completed_READ_replies=1688
completed_READ_bytes=71657472
completed_p1_READ_bytes=53687296
writes=0
last_completed_request=1688
last_READ_offset=164990976
last_READ_length=49152
last_reply_estimated_UTC=2026-10-30T03:56:46.559796Z
last_snapshot_UTC=2026-10-30T04:05:02.023962Z
reply_inactivity_seconds=495.464
continuous_same_USB_entry_overlap_seconds=455.260188
cache_or_persist_filesystem_evidence=NOT_OBSERVED
userdata_filesystem_evidence=NOT_OBSERVED
```

These are `REAL_DEVICE_FACT` transport/USB observations with `HOST_FACT` classifier arithmetic. Earlier shorter idle intervals ended in additional requests, so they were not used as terminal boundaries. The final completed-request identity remained unchanged and the same Linux USB entry persisted for more than 90s with no observation errors or reenumeration.

The user reported reaching Lineage boot animation (`REAL_DEVICE_FACT`, user-observed screen), and confirmed that an earlier run had genuinely self-rebooted. The exact old runtime sysctl values remain unknown; no old console is attributed retrospectively. USB ADB has not been accepted/restored; a host TCP connect to port 5555 timed out and three ICMP probes got no reply (`HOST_FACT` probe results), neither of which identifies a cause. The user need not continuously watch the screen.

Prespecified outcome: `panic_timeout_dependency=SUPPORTED`. This is single-run behavior supporting a path affected by panic timeout, not proof of a kernel panic, exclusive reset mechanism, call site or root cause. The nonliteral late-sysctl-writer limitation remains. Kernel panic/hang/reset cause remains UNKNOWN; full Android boot remains NOT_PROVEN. The NBD p3/p6 evidence gate is NOT_REACHED, which must not be phrased as proof that Android never reached second stage; the separate screen observation is preserved.

Evidence: `audits/2026-10-30-P2/`, including all raw USB/statistics timelines, exact launcher source and commands, preflight, identities, classifier, screen notes, reachability probes, result and SHA256 manifest. The active root-storage server PID `92856` was left running; dedicated USB observer/snapshot sampler ended or were stopped. No manual or automatic reset/recovery transition was issued after the diagnostic. P2 authorization is consumed and hardware pause restored.

Next question: can the first controlled successor kernel expose a persistent console attributable to P2? Prepare exact accepted recovery artifacts/host capture before any transition, enforce no intervening Linux boot, and treat a missing/unattributable console as UNKNOWN. No recovery boot is authorized by this P2 result.
