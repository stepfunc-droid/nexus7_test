# Phase6 automatic ADB console capture preparation

Status: **HOST_FACT / CURRENT BASELINE CAPTURED / HARDWARE PAUSED**.

Batch J starts at `e814fc55122ba8712ba4390e705eb2350e4d28d4` on diskless-v2, after the one-file derivative implementation batch closed. Question: can a host collector save a newly visible rooted ADB kernel's previous console before slower diagnostics, detect identity changes during capture, and preserve provenance limits without requiring manual screen observation?

## Collector contract

`scripts/v2/phase6_v2_watch_adb_console.py` requires a fresh output directory and correct serial `07a117ae`, valid boot ID, uptime and already-root ADB baseline. It captures that baseline before emitting `armed`. `--snapshot-current` captures only the baseline and never arms a watcher. No reboot, fastboot, flash, device-file write or Android configuration change exists in this collector.

For each newly visible boot ID, save raw `/proc/last_kmsg` first, then recheck boot identity, save mount/cmdline/build/boot-completed/NBD identity and current dmesg, and recheck identity again. Preserve stdout/stderr, exit status, byte count and SHA256 even on failure. Accept capture stability only when boot ID and root identity stay consistent. A successful capture is deduplicated by boot ID, not by ADB disconnect count. Failed captures have at most three attempts per boot with a five-second retry interval. Probe errors mean unavailable evidence, not a reboot fact.

The optional `--root-on-return` may issue `adb -s 07a117ae root` at most three times per newly visible nonroot boot, using the rooted-debugging option explicitly enabled by the user. This restarts adbd only; it does not change settings or reboot the device. Wrong serial/invalid identity is rejected. Current baseline mode issued no root restart because ADB was already root.

Timeline JSONL includes state changes and five-second heartbeats. Default maximum observation is 2100s; a cap or idle interval never becomes boot/reset success evidence. Pair this watcher with the existing independent USB observer and NBD completed-reply/partition traces for the entire controlled session, including any terminal transition. The collector does not stop a live storage export.

**Provenance limit:** first-visible ADB is not independently proven to be the first successor kernel. Earlier fallback starts might fail before ADB. Every capture explicitly records `first_visible_adb_is_first_successor=UNKNOWN` and `previous_boot_attribution=UNASSESSED`. Named-run attribution still requires review of the complete USB/NBD/boot sequence and actual console identity; missing ring head/run identity or extra possible boots may leave it INCONCLUSIVE. Never repair attribution by assuming an ADB return is diskless success.

## Validation

HOST_FACT: actual Mac self-tests pass (3 tests). They verify raw binary preservation and console-first ordering; reject invalid UUID/serial/probes; flag a boot change during capture; exercise the real CLI using a simulated ADB process through baseline -> unavailable -> new nonroot boot -> adbd root -> one deduplicated stable capture. Final reset cause remains UNKNOWN in the test output.

REAL_DEVICE_FACT: `--snapshot-current` on the existing eMMC OS captured the baseline without a device reboot or root restart:

```text
boot_id=b124ede8-c0bb-490a-8697-211f41b4bb73
uid=0
before_uptime=13303.68
after_console_uptime=13304.04
after_diagnostics_uptime=13304.62
same_boot_through_capture=true
last_kmsg_bytes=225756
last_kmsg_sha256=c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497
```

The console is byte-identical to the previously archived NBD console; no new named-run provenance is established. Current mounts still identify eMMC, not diskless Android. Raw capture is in `out/phase6-v2-console-J-current/`; the committed evidence directory contains capture metadata, identity, timeline, source hashes, self-test result and a reference to the existing identical console archive. Current eMMC dmesg remains in out with its hash; it is not used as a previous diskless cause.

## Handoff

J proves host behavior plus current baseline access, not capture during a real reboot. Next batch must compose current original frozen-input/P2 boot checks with the explicit root-fstab derivative audit and derivative-specific partition trace map; then write/commit the single runtime question, exact identities, observation/interpretation/stops and authorization state. No hardware boot is authorized by J. The root-fstab derivative remains IMPLEMENTED_UNPROVEN and the later NBD-timeout cause UNKNOWN.
