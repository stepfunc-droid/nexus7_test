#!/usr/bin/env python3
"""Protocol differential and idle-snapshot checks for the host-only observer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import phase6_v2_observe_usb as usb
import selftest_phase6_v2_nbd_differential as common


def check(condition, message):
    if not condition:
        raise SystemExit("ERROR: " + message)


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def start_server(root, run, readonly=False):
    image = run / "disk.img"
    image.write_bytes(bytes(range(256)) * 4096)
    trace_map = run / "map.json"
    common.synthetic_trace_map(trace_map, image.stat().st_size)
    stats = run / "stats.jsonl"
    port = common.free_port()
    cmd = [sys.executable, str(root / "scripts/v2/phase6_v2_nbd_observed_server.py"),
           "--stats-log", str(stats), "--system-range", "0", str(image.stat().st_size),
           "--bind", "127.0.0.1", "--port", str(port),
           "--trace-map", str(trace_map), "--trace-log", str(run / "trace.jsonl")]
    if readonly:
        cmd.append("--readonly")
    cmd.append(str(image))
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return proc, common.wait_connect(proc, port), image, stats


def stop(proc):
    proc.terminate()
    proc.wait(timeout=3)


def main():
    root = Path(__file__).resolve().parents[2]
    accepted = root / "scripts/nbd_test_server.py"
    check(common.git_blob_sha1(accepted.read_bytes()) == common.EXPECTED_ACCEPTED_SERVER_GIT_BLOB,
          "accepted server identity changed")
    with tempfile.TemporaryDirectory(prefix="phase6-observation-test-") as raw:
        temp = Path(raw)
        for readonly in (False, True):
            run = temp / ("ro" if readonly else "rw")
            run.mkdir()
            proc, sock, image, stats = start_server(root, run, readonly)
            reference = run / "reference.img"
            shutil.copyfile(image, reference)
            try:
                with sock:
                    actual = common.exercise(sock, image.stat().st_size, readonly)
                expected = common.run_server(accepted, reference, readonly)
                check(actual == expected, "observer changed NBD protocol bytes")
                check(image.read_bytes() == reference.read_bytes(), "observer changed disk results")
                for _ in range(100):
                    if any(e["event"] == "client_end" for e in events(stats)):
                        break
                    time.sleep(0.01)
                end = next(e for e in events(stats) if e["event"] == "client_end")
                check(end["completed_read_bytes"] == 96, "completed READ byte count incorrect")
                check(end["completed_system_read_bytes"] == 96, "system-range byte count incorrect")
                check(end["completed_replies"] == (8 if readonly else 9), "reply count incorrect")
            finally:
                stop(proc)
            print(f"differential={'ro' if readonly else 'rw'} protocol_and_disk=PASS")
        run = temp / "idle"
        run.mkdir()
        proc, sock, image, stats = start_server(root, run)
        try:
            with sock:
                common.recv_exact(sock, common.HEADER_LEN)
                reply = common.send_request(sock, common.NBD_CMD_READ, 1, 0, 512, expect_payload=True)
                check(reply[16:] == image.read_bytes()[:512], "idle test READ payload differs")
                for _ in range(3):
                    os.kill(proc.pid, signal.SIGUSR1)
                    time.sleep(0.05)
                snapshots = [e for e in events(stats) if e["event"] == "snapshot"]
                check(len(snapshots) == 3, "SIGUSR1 snapshots missing")
                check(all(e["active"] and e["completed_read_bytes"] == 512 and
                          e["last_completed_reply"]["last"]["cmd"] == "READ" for e in snapshots),
                      "idle snapshots lost completed request evidence")
                common.send_request(sock, common.NBD_CMD_READ, 2, 512, 16, expect_payload=True)
                common.disconnect(sock, 3)
        finally:
            stop(proc)
        print("idle_snapshot_without_disconnect=PASS")
    node = {"idVendor": 6353, "USB Serial Number": "07a117ae"}
    tree = {"IORegistryEntryChildren": [node]}
    check(list(usb.usb_devices(tree)) == list(usb.usb_devices([tree])),
          "USB plist dict/list roots disagree")
    check(len(list(usb.usb_devices(tree))) == 1, "USB tree traversal lost device")
    print("usb_plist_dict_and_list_roots=PASS")
    print("DISKLESS_V2_PHASE6_V2_OBSERVATION_SELFTEST=PASS")
    print("evidence_class=HOST_FACT")


if __name__ == "__main__":
    main()
