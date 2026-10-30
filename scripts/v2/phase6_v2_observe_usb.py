#!/usr/bin/env python3
"""Read-only USB timeline and optional SIGUSR1 host-server snapshots on macOS."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import time


def usb_devices(tree):
    if isinstance(tree, list):
        for child in tree:
            yield from usb_devices(child)
    elif isinstance(tree, dict):
        if "idVendor" in tree:
            yield {key: tree.get(key) for key in (
                "IORegistryEntryID", "IORegistryEntryName", "idVendor", "idProduct",
                "USB Product Name", "USB Serial Number", "locationID")}
        yield from usb_devices(tree.get("IORegistryEntryChildren", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--serial", default="07a117ae")
    parser.add_argument("--location", type=int, default=336789504)
    parser.add_argument("--server-pid", type=int)
    parser.add_argument("--duration", type=float, default=420)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error("duration and interval must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    previous = None
    tracked_location=args.location
    with args.output.open("x") as fp:
        while time.monotonic() - started < args.duration:
            tick = time.monotonic()
            item = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "elapsed": round(tick - started, 6)}
            try:
                result = subprocess.run(["ioreg", "-a", "-p", "IOUSB", "-l", "-w", "0"],
                                        capture_output=True, timeout=3, check=True)
                observed=list(usb_devices(plistlib.loads(result.stdout)))
                matching=[d for d in observed if d['USB Serial Number']==args.serial]
                if len(matching)==1:tracked_location=matching[0]['locationID']
                devices = [d for d in observed
                           if d["USB Serial Number"] == args.serial or
                           d["locationID"] == tracked_location]
                item['tracked_location']=tracked_location
                item["devices"] = devices
                if devices != previous:
                    print(json.dumps({"usb_change": item}, sort_keys=True), flush=True)
                    previous = devices
            except Exception as exc:
                item["observation_error"] = repr(exc)
            if args.server_pid is not None:
                try:
                    os.kill(args.server_pid, signal.SIGUSR1)
                except ProcessLookupError:
                    item["server_missing"] = True
            fp.write(json.dumps(item, sort_keys=True) + "\n")
            fp.flush()
            time.sleep(max(0, args.interval - (time.monotonic() - tick)))


if __name__ == "__main__":
    main()
