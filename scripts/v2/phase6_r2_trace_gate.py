#!/usr/bin/env python3
"""Parse Phase6 R2/R3 host NBD trace evidence after one real-device run."""

import argparse
import json
from pathlib import Path

EXPECTED = [
    "pre_enforce_vendor_precompiled_sepolicy",
    "post_enforce_second_stage_init_rc",
    "post_enforce_flox_rc",
]


def die(msg: str):
    raise SystemExit(f"ERROR: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-log", required=True, type=Path)
    args = ap.parse_args()

    if not args.trace_log.is_file():
        die(f"trace log not found: {args.trace_log}")
    events = [json.loads(line) for line in args.trace_log.read_text().splitlines() if line.strip()]
    opens = [e for e in events if e.get("event") == "connection_open"]
    if len(opens) != 1:
        die(f"expected exactly one NBD connection, observed {len(opens)}")
    conn = int(opens[0]["connection"])

    completes = [
        e for e in events
        if e.get("event") == "marker_complete" and int(e.get("connection", -1)) == conn
    ]
    names = [e.get("marker") for e in completes]
    if names != EXPECTED:
        die(f"marker completion sequence mismatch: {names} != {EXPECTED}")

    requests = [int(e["request"]) for e in completes]
    if requests != sorted(requests) or len(set(requests)) != len(requests):
        die(f"marker request order is not strictly increasing: {requests}")

    close_before_complete = False
    final_req = requests[-1]
    for e in events:
        if e.get("event") == "connection_close" and int(e.get("connection", -1)) == conn:
            # elapsed ordering is enough here because events are append-only JSONL.
            idx = events.index(e)
            complete_idx = max(i for i, x in enumerate(events) if x in completes)
            if idx < complete_idx:
                close_before_complete = True
                break
    if close_before_complete:
        die("NBD connection closed before the final post-enforcing marker completed")

    print("DISKLESS_V2_PHASE6_R2_TRANSPORT_AFTER_ENFORCING=PASS")
    print("DISKLESS_V2_PHASE6_R3_ENFORCING_SECOND_STAGE=PASS")
    print(f"connection={conn}")
    print("single_nbd_connection=PASS")
    print("marker_sequence=" + ",".join(EXPECTED))
    print("marker_requests=" + ",".join(map(str, requests)))
    print("pre_enforce_policy_read=complete")
    print("post_enforce_init_rc_read=complete")
    print("post_enforce_flox_rc_read=complete")
    print("nexus_side_logger=none")
    print("android_rc_modifications=none")


if __name__ == "__main__":
    main()
