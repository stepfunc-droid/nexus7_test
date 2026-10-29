# Diskless v2 Phase 6 Audit V2 — real-device run 1 postmortem

Status: **6V2-D PASS / 6V2-E NOT REACHED / RUN ENDED BY DEVICE AUTO-REBOOT**.

This file records the first real-device run of the Audit-V2 continuation image after host gates 6V2-A/B/C passed.

## Accepted run identity

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
accepted_nbd_server_git_blob=6e7ce821c98f3c4f7a4ff4c337a20a4297c2bfd8
traced_nbd_server_git_blob=8046084119a1c12a72465b87d5afb450a2071311
partition_trace_map=deterministic-match
```

Preflight result:

```text
DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS
```

## Host-observed NBD evidence

The traced server accepted exactly one connection:

```text
TRACE event=connection_open connection=1 peer=172.16.42.1:46433 elapsed=25.593854
```

The Nexus then completed the oldstyle NBD handshake and sent a valid first request:

```text
TRACE event=nbd_first_request connection=1 request=1 cmd=READ offset=0 length=4096 elapsed=25.70591
```

Therefore:

```text
DISKLESS_V2_PHASE6_V2_D_TRANSPORT_ATTACH=PASS
single_nbd_connection=PASS
```

No cache/persist filesystem-evidence completion was observed before the run ended, so:

```text
DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=NOT_REACHED
```

No userdata filesystem evidence was observed. No late-fs claim is made.

## Run termination

The device auto-rebooted. The host later recorded:

```text
TRACE event=connection_close connection=1 reason=transport-error:TimeoutError(60, 'Operation timed out') elapsed=190.380111
```

Important interpretation:

- `60` in `TimeoutError(60, ...)` is the macOS errno value (`ETIMEDOUT`), not a configured 60-second application timeout.
- Neither the accepted Phase3/4 NBD server nor the traced server configures a socket timeout.
- The interval between the first NBD request and the host-side transport exception was about 164.7 seconds.
- Because the Nexus had already auto-rebooted, disappearance of USB ECM/TCP can itself cause a later host socket timeout. This event does **not** prove that the NBD transport caused the reboot.

Current causal classification:

```text
transport_attach=PROVEN
transport_caused_reboot=NOT_PROVEN
selinux_caused_reboot=NOT_PROVEN
second_stage_or_later=NOT_PROVEN
run_end=device-auto-reboot
```

## Observation gap discovered

The traced JSONL intentionally recorded only connection lifecycle, first request, and target-partition evidence. It did not record the rolling NBD request summary for ordinary p1/p2 traffic.

The server already maintains:

```text
phase
requests
reads
writes
read_bytes
write_bytes
last request offset/length/type
```

and prints that summary when an exception occurs, but the exception summary is written to stderr. The run command used a stdout-only `tee`, so `phase6-v2-server.txt` did not preserve the most useful failure summary.

Consequently this run cannot, from persisted files alone, establish the final successful request, request count, or exact server syscall phase at the time the peer disappeared.

## Next rule

Do not modify Android or the continuation image based on this run.

Before another real-device run, the host observer must preserve the exception/request summary without changing NBD protocol semantics. The preferred minimal change is host-only logging/capture, followed by the existing differential protocol gate. If the original server terminal scrollback still contains the `client transport error=... phase=... requests=... last=[...]` line, preserve that line before any repeat run.
