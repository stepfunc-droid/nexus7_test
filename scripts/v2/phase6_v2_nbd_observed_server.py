#!/usr/bin/env python3
"""Run the exact V2 server with host-only completed-reply snapshots.

SIGUSR1 appends a snapshot without closing the client. Protocol functions call
the pinned implementation with unchanged arguments. No socket timeout is added.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

import nbd_partition_trace_server as base


EXPECTED_SERVER_BLOB = "8046084119a1c12a72465b87d5afb450a2071311"


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--stats-log", required=True, type=Path)
    parser.add_argument("--system-range", required=True, nargs=2, type=int)
    args, server_args = parser.parse_known_args()
    system_start, system_end = args.system_range
    if not 0 <= system_start < system_end:
        parser.error("invalid system byte range")
    source = Path(base.__file__).read_bytes()
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    if blob != EXPECTED_SERVER_BLOB:
        raise SystemExit("ERROR: pinned V2 server identity changed")
    args.stats_log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    state = {"active": False, "connection": 0, "stats": None,
             "completed_replies": 0, "completed_read_bytes": 0,
             "completed_system_read_bytes": 0,
             "last_completed_reply": None}
    original_client = base.serve_client
    original_reply = base.send_reply

    with args.stats_log.open("x") as fp:
        def emit(event: str) -> None:
            stats = state["stats"]
            item = {"event": event,
                    "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "elapsed": round(time.monotonic() - started, 6),
                    "active": state["active"], "connection": state["connection"],
                    "completed_replies": state["completed_replies"],
                    "completed_read_bytes": state["completed_read_bytes"],
                    "completed_system_read_bytes": state["completed_system_read_bytes"],
                    "last_completed_reply": state["last_completed_reply"],
                    "stats": dict(stats) if stats is not None else None}
            fp.write(json.dumps(item, sort_keys=True) + "\n")
            fp.flush()

        def observed_reply(conn, error, handle, payload=b""):
            result = original_reply(conn, error, handle, payload)
            stats = state["stats"]
            if stats is not None:
                last = dict(stats["last"]) if stats["last"] else None
                state["last_completed_reply"] = {
                    "request": stats["requests"], "error": error, "last": last,
                    "elapsed": round(time.monotonic() - started, 6),
                }
                state["completed_replies"] += 1
                if error == 0 and last and last["cmd"] == "READ":
                    state["completed_read_bytes"] += len(payload)
                    start = last["offset"]
                    end = start + len(payload)
                    state["completed_system_read_bytes"] += max(
                        0, min(end, system_end) - max(start, system_start))
            return result

        def observed_client(conn, image_fd, size, peer, readonly, label, port,
                            stats, connection, tracer):
            state.update(active=True, connection=connection, stats=stats,
                         completed_replies=0, completed_read_bytes=0,
                         completed_system_read_bytes=0,
                         last_completed_reply=None)
            emit("client_start")
            try:
                return original_client(conn, image_fd, size, peer, readonly,
                                       label, port, stats, connection, tracer)
            finally:
                state["active"] = False
                emit("client_end")

        def snapshot(signum, frame):
            emit("snapshot")

        base.send_reply = observed_reply
        base.serve_client = observed_client
        signal.signal(signal.SIGUSR1, snapshot)
        sys.argv = [base.__file__, *server_args]
        emit("observer_start")
        try:
            base.main()
        finally:
            emit("observer_end")


if __name__ == "__main__":
    main()
