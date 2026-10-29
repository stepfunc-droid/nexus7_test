#!/usr/bin/env python3
"""Host-only self-test for Phase6 R2 trace coverage and ordering."""

import argparse
import json
import tempfile
from pathlib import Path

from nbd_trace_server import TraceLogger


def die(msg: str):
    raise SystemExit(f"ERROR: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-map", required=True, type=Path)
    args = ap.parse_args()

    trace = json.loads(args.trace_map.read_text())
    markers = sorted(trace["markers"], key=lambda m: int(m["order"]))
    if [int(m["order"]) for m in markers] != [1, 2, 3]:
        die("trace map must contain marker order 1,2,3")

    with tempfile.TemporaryDirectory(prefix="phase6-r2-selftest-") as td:
        log = Path(td) / "trace.jsonl"
        tracer = TraceLogger(args.trace_map, log)
        try:
            state = tracer.new_connection(1, ("127.0.0.1", 12345))
            request = 0
            for marker in markers:
                for r in marker["ranges"]:
                    request += 1
                    tracer.on_read_complete(
                        1,
                        request,
                        int(r["disk_offset"]),
                        int(r["length"]),
                        state,
                    )
            tracer.close_connection(1, "selftest-complete")
        finally:
            tracer.close()

        events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        complete = [e for e in events if e.get("event") == "marker_complete"]
        names = [e["marker"] for e in complete]
        expected = [m["name"] for m in markers]
        if names != expected:
            die(f"marker completion order mismatch: {names} != {expected}")
        if any(int(e["connection"]) != 1 for e in complete):
            die("marker self-test escaped connection 1")

    print("DISKLESS_V2_PHASE6_R2_TRACE_SELFTEST=PASS")
    print("marker_order=" + ",".join(expected))
    print("same_connection=PASS")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
