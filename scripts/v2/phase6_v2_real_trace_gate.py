#!/usr/bin/env python3
"""Classify one Audit-V2 real-device NBD trace without Nexus-side observers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Classify Phase6 V2 real-device partition trace")
    ap.add_argument("--trace", type=Path, default=Path.home() / "phase6-v2-nbd-trace.jsonl")
    ap.add_argument("--trace-map", required=True, type=Path)
    args = ap.parse_args()

    if not args.trace.is_file():
        die(f"trace log missing: {args.trace}")
    if not args.trace_map.is_file():
        die(f"trace map missing: {args.trace_map}")

    trace_map = json.loads(args.trace_map.read_text())
    if trace_map.get("schema") != 2:
        die("trace map schema is not 2")
    mapped = {p["name"]: p for p in trace_map.get("partitions", [])}
    if set(mapped) != {"cache", "persist", "userdata"}:
        die(f"unexpected trace-map partitions: {sorted(mapped)}")

    events = []
    for lineno, raw in enumerate(args.trace.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            die(f"invalid JSONL line {lineno}: {exc}")
        events.append(event)

    opens = [e for e in events if e.get("event") == "connection_open"]
    if len(opens) != 1:
        die(f"single-session gate requires exactly one connection_open; got {len(opens)}")
    connection = opens[0].get("connection")

    first_requests = [
        e for e in events
        if e.get("event") == "nbd_first_request" and e.get("connection") == connection
    ]
    if len(first_requests) != 1:
        die(f"transport attach requires exactly one nbd_first_request; got {len(first_requests)}")

    foreign = [
        e for e in events
        if e.get("connection") is not None and e.get("connection") != connection and
        e.get("event") in {
            "nbd_first_request", "partition_first_read", "filesystem_evidence_hit",
            "filesystem_evidence_complete", "connection_close"
        }
    ]
    if foreign:
        die("trace contains events from a second NBD connection")

    complete = [
        e for e in events
        if e.get("event") == "filesystem_evidence_complete" and e.get("connection") == connection
    ]
    seen_partitions = set()
    for event in complete:
        name = event.get("partition")
        if name not in mapped:
            die(f"completion event references unknown partition: {name}")
        if name in seen_partitions:
            die(f"duplicate filesystem evidence completion for {name}")
        seen_partitions.add(name)
        # stage is an fstab/mount-class annotation in the trace map.  It is
        # checked for internal consistency, but only cache/persist are used as
        # causal second-stage-or-later acceptance evidence below.
        expected_stage = mapped[name]["stage"]
        if event.get("stage") != expected_stage:
            die(f"{name}: event stage={event.get('stage')} expected={expected_stage}")

    early_candidates = [e for e in complete if e.get("partition") in {"cache", "persist"}]
    userdata = [e for e in complete if e.get("partition") == "userdata"]
    first_post_first_stage = (
        min(early_candidates, key=lambda e: int(e["request"])) if early_candidates else None
    )
    userdata_event = userdata[0] if userdata else None

    closes = [
        e for e in events
        if e.get("event") == "connection_close" and e.get("connection") == connection
    ]
    if len(closes) > 1:
        die("trace contains multiple close events for the same connection")
    close_reason = closes[0].get("reason") if closes else "still-open-or-not-captured"

    print("DISKLESS_V2_PHASE6_V2_D_TRANSPORT_ATTACH=PASS")
    print(f"connection={connection}")
    print("single_nbd_connection=PASS")
    print(f"first_request={first_requests[0].get('request')}")
    print(f"first_request_cmd={first_requests[0].get('cmd')}")
    print(f"connection_close_reason={close_reason}")

    if first_post_first_stage:
        print("DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=PASS")
        print(f"evidence_partition={first_post_first_stage['partition']}")
        print(f"evidence_request={first_post_first_stage['request']}")
        print("meaning=first-stage-excluded-filesystem-read-after-stock-enforcing-handoff")
    else:
        print("DISKLESS_V2_PHASE6_V2_E_ENFORCING_SECOND_STAGE_OR_LATER=NOT_REACHED")

    if userdata_event:
        print("userdata_filesystem_evidence=OBSERVED")
        print(f"userdata_evidence_request={userdata_event['request']}")
        print("late_fs_claim=NOT_PROVEN")
        print("note=vold-starts-in-early-fs-so-userdata-I/O-is-not-a-hard-late-fs-marker")
    else:
        print("userdata_filesystem_evidence=NOT_OBSERVED")
        print("late_fs_claim=NOT_PROVEN")

    if closes and str(close_reason).startswith(("transport-error:", "error:")):
        print("transport_close_classification=ERROR")
    elif closes:
        print("transport_close_classification=normal-or-peer-close")
    else:
        print("transport_close_classification=no-close-event")

    print("android_rc_marker=not-used")
    print("kernel_log_observer=not-used")
    print("selinux_policy=stock-enforcing-baseline")


if __name__ == "__main__":
    main()
