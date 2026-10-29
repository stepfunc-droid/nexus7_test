#!/usr/bin/env python3
"""End-to-end localhost self-test of the Phase6 traced NBD server."""

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

NBD_INIT_MAGIC = b"NBDMAGIC"
NBD_OLDSTYLE_MAGIC = 0x0000420281861253
NBD_REQUEST_MAGIC = 0x25609513
NBD_REPLY_MAGIC = 0x67446698
NBD_CMD_READ = 0
NBD_CMD_DISC = 2
HEADER_LEN = 8 + 8 + 8 + 4 + 124
MAX_READ = 1024 * 1024


def die(msg):
    raise SystemExit(f"ERROR: {msg}")


def recv_exact(sock, size):
    out = bytearray()
    while len(out) < size:
        data = sock.recv(size - len(out))
        if not data:
            die(f"socket closed after {len(out)}/{size} bytes")
        out += data
    return bytes(out)


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk", required=True, type=Path)
    ap.add_argument("--trace-map", required=True, type=Path)
    args = ap.parse_args()
    if not args.disk.is_file() or not args.trace_map.is_file():
        die("disk or trace map missing")

    trace = json.loads(args.trace_map.read_text())
    markers = sorted(trace["markers"], key=lambda m: int(m["order"]))
    expected = [m["name"] for m in markers]
    server = Path(__file__).with_name("nbd_trace_server.py")
    port = free_port()

    with tempfile.TemporaryDirectory(prefix="phase6-r2-server-") as td:
        log = Path(td) / "trace.jsonl"
        proc = subprocess.Popen(
            [sys.executable, str(server), "--bind", "127.0.0.1", "--port", str(port),
             "--trace-map", str(args.trace_map), "--trace-log", str(log), str(args.disk)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            sock = None
            for _ in range(100):
                if proc.poll() is not None:
                    err = proc.stderr.read()
                    die(f"trace server exited early: {err}")
                try:
                    sock = socket.create_connection(("127.0.0.1", port), timeout=0.2)
                    break
                except OSError:
                    time.sleep(0.02)
            if sock is None:
                die("could not connect to localhost trace server")

            with sock, args.disk.open("rb") as disk_fp:
                header = recv_exact(sock, HEADER_LEN)
                if header[:8] != NBD_INIT_MAGIC:
                    die("bad NBD init magic")
                if struct.unpack_from(">Q", header, 8)[0] != NBD_OLDSTYLE_MAGIC:
                    die("bad NBD oldstyle magic")
                export_size = struct.unpack_from(">Q", header, 16)[0]
                if export_size != args.disk.stat().st_size:
                    die("NBD export size differs from disk size")

                req = 0
                for marker in markers:
                    for r in marker["ranges"]:
                        offset = int(r["disk_offset"])
                        left = int(r["length"])
                        while left:
                            length = min(left, MAX_READ)
                            req += 1
                            handle = struct.pack(">Q", req)
                            sock.sendall(struct.pack(">II8sQI", NBD_REQUEST_MAGIC, NBD_CMD_READ,
                                                     handle, offset, length))
                            reply = recv_exact(sock, 16)
                            magic, error, got_handle = struct.unpack(">II8s", reply)
                            if magic != NBD_REPLY_MAGIC or error != 0 or got_handle != handle:
                                die(f"bad NBD read reply request={req} error={error}")
                            payload = recv_exact(sock, length)
                            disk_fp.seek(offset)
                            expected_payload = disk_fp.read(length)
                            if payload != expected_payload:
                                die(f"NBD payload mismatch request={req} offset={offset}")
                            offset += length
                            left -= length

                req += 1
                handle = struct.pack(">Q", req)
                sock.sendall(struct.pack(">II8sQI", NBD_REQUEST_MAGIC, NBD_CMD_DISC,
                                         handle, 0, 0))

            for _ in range(50):
                if log.exists() and "marker_complete" in log.read_text():
                    time.sleep(0.05)
                    break
                time.sleep(0.02)

            events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
            opens = [e for e in events if e.get("event") == "connection_open"]
            if len(opens) != 1:
                die(f"self-test expected one connection, got {len(opens)}")
            complete = [e for e in events if e.get("event") == "marker_complete"]
            names = [e["marker"] for e in complete]
            if names != expected:
                die(f"server marker sequence mismatch: {names} != {expected}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

    print("DISKLESS_V2_PHASE6_R2_SERVER_SELFTEST=PASS")
    print("oldstyle_nbd_handshake=PASS")
    print("read_payload_byte_validation=PASS")
    print("marker_sequence=" + ",".join(expected))
    print("single_connection=PASS")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
