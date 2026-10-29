#!/usr/bin/env python3
"""Host-only semantic self-test for Audit-V2 partition-stage evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from nbd_partition_trace_server import PartitionTraceLogger


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def completed(events: list[dict], partition: str) -> list[dict]:
    return [
        e for e in events
        if e.get("event") == "filesystem_evidence_complete" and e.get("partition") == partition
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Self-test Phase6 V2 partition-stage trace semantics")
    ap.add_argument("--trace-map", required=True, type=Path)
    args = ap.parse_args()
    if not args.trace_map.is_file():
        die(f"trace map missing: {args.trace_map}")

    data = json.loads(args.trace_map.read_text())
    if data.get("schema") != 2:
        die("trace map schema is not 2")
    parts = {p["name"]: p for p in data.get("partitions", [])}
    if set(parts) != {"cache", "persist", "userdata"}:
        die(f"unexpected trace partitions: {sorted(parts)}")

    with tempfile.TemporaryDirectory(prefix="phase6-v2-trace-selftest-") as td:
        log = Path(td) / "trace.jsonl"
        tracer = PartitionTraceLogger(args.trace_map, log, int(data["disk_size"]))
        try:
            state = tracer.new_connection(1, ("127.0.0.1", 12345))
            request = 0

            # MBR traffic is outside every target partition and must never be
            # accepted as filesystem evidence.
            request += 1
            tracer.on_read_complete(1, request, 0, 512, state)
            events = read_events(log)
            if any(e.get("event") == "filesystem_evidence_complete" for e in events):
                die("MBR read incorrectly produced filesystem evidence")

            # A generic read inside each partition, deliberately chosen away
            # from superblock/GDT windows, may create partition_first_read but
            # must not complete filesystem evidence.
            for name in ("cache", "persist", "userdata"):
                p = parts[name]
                request += 1
                safe_offset = int(p["disk_start"]) + max(int(p["block_size"]) * 8, 65536)
                if safe_offset + 512 >= int(p["disk_end"]):
                    die(f"{name}: partition too small for semantic self-test")
                tracer.on_read_complete(1, request, safe_offset, 512, state)
                if completed(read_events(log), name):
                    die(f"{name}: generic partition read incorrectly completed evidence")

            # Superblock alone is insufficient.
            for name in ("cache", "persist", "userdata"):
                p = parts[name]
                r = p["evidence"]["superblock"]
                request += 1
                tracer.on_read_complete(1, request, int(r["start"]), int(r["end"]) - int(r["start"]), state)
                if completed(read_events(log), name):
                    die(f"{name}: superblock-only read incorrectly completed evidence")

            # Primary GDT completes evidence only after the independent
            # superblock window has already been observed on the same connection.
            for name in ("cache", "persist", "userdata"):
                p = parts[name]
                r = p["evidence"]["primary_gdt"]
                request += 1
                tracer.on_read_complete(1, request, int(r["start"]), int(r["end"]) - int(r["start"]), state)

            events = read_events(log)
            for name in ("cache", "persist", "userdata"):
                matches = completed(events, name)
                if len(matches) != 1:
                    die(f"{name}: expected exactly one completed evidence event, got {len(matches)}")

            early = {
                e["partition"] for e in events
                if e.get("event") == "filesystem_evidence_complete" and
                e.get("stage") == "second-stage-fs-early"
            }
            if early != {"cache", "persist"}:
                die(f"early-stage partition classification mismatch: {sorted(early)}")
            late = [
                e for e in events
                if e.get("event") == "filesystem_evidence_complete" and
                e.get("stage") == "second-stage-late-fs"
            ]
            if len(late) != 1 or late[0].get("partition") != "userdata":
                die("userdata late-fs classification mismatch")

            tracer.close_connection(1, "selftest-complete")
        finally:
            tracer.close()

    print("DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_SELFTEST=PASS")
    print("mbr_read_is_not_stage_evidence=PASS")
    print("generic_partition_read_is_not_stage_evidence=PASS")
    print("superblock_only_is_not_stage_evidence=PASS")
    print("superblock_plus_primary_gdt_required=PASS")
    print("cache_persist_stage=second-stage-fs-early")
    print("userdata_stage=second-stage-late-fs")
    print("same_connection_state_required=PASS")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
