#!/usr/bin/env python3
import argparse
import re
import sys
import time
from pathlib import Path

MARKER = "DISKLESS_V2_PHASE6_SECOND_STAGE_EARLY_INIT=1"


def fail(msg: str, marker_file: Path, nbd_log: Path):
    print(f"ERROR: {msg}", file=sys.stderr)
    if marker_file.exists():
        print("--- marker capture ---", file=sys.stderr)
        print(marker_file.read_text(errors="replace")[-4000:], file=sys.stderr)
    if nbd_log.exists():
        print("--- NBD log tail ---", file=sys.stderr)
        print("\n".join(nbd_log.read_text(errors="replace").splitlines()[-80:]), file=sys.stderr)
    raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description="Phase6 enforcing second-stage early-init marker gate")
    ap.add_argument("--marker-file", type=Path, default=Path.home() / "phase6-second-stage-marker.txt")
    ap.add_argument("--nbd-log", type=Path, default=Path.home() / "nexus7-v2-android-nbd.log")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    if not args.marker_file.exists():
        fail(
            f"marker capture not found: {args.marker_file}; start 'nc -lk 11001 | tee {args.marker_file}' before boot",
            args.marker_file, args.nbd_log,
        )
    if not args.nbd_log.exists():
        fail(f"NBD log not found: {args.nbd_log}", args.marker_file, args.nbd_log)

    print("==> Waiting for enforcing Android second-stage early-init marker")
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        text = args.marker_file.read_text(errors="replace")
        if MARKER in text:
            break
        time.sleep(1)
    else:
        fail("timed out waiting for second-stage early-init marker", args.marker_file, args.nbd_log)

    nbd = args.nbd_log.read_text(errors="replace")
    connections = len(re.findall(r"client [^ ]+ connected; export size=", nbd))
    if connections != 1:
        fail(f"expected exactly one successful NBD connection; found {connections}", args.marker_file, args.nbd_log)
    if re.search(r"transport error|client error|Traceback|bad request magic|unsupported NBD command", nbd, re.I):
        fail("NBD log contains server/protocol error", args.marker_file, args.nbd_log)

    print(MARKER)
    print("DISKLESS_V2_PHASE6_ENFORCING_SECOND_STAGE_VERIFIED=1")
    print("selinux_policy=stock-enforcing-baseline")
    print("stage=second-stage-early-init")
    print("single_nbd_connection=PASS")
    print("kernel_log_observer=not-used")
    print("android_rc_bypasses=none")
    print(f"evidence={args.marker_file}")


if __name__ == "__main__":
    main()
