#!/usr/bin/env python3
"""Differential protocol test: accepted Phase3/4 NBD server vs V2 traced server."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
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
NBD_CMD_WRITE = 1
NBD_CMD_DISC = 2
NBD_CMD_FLUSH = 3
NBD_CMD_TRIM = 4
NBD_CMD_FLAG_FUA = 1 << 16
HEADER_LEN = 8 + 8 + 8 + 4 + 124
EXPECTED_ACCEPTED_SERVER_GIT_BLOB = "6e7ce821c98f3c4f7a4ff4c337a20a4297c2bfd8"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def recv_exact(sock: socket.socket, n: int) -> bytes:
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            die(f"socket closed after {len(out)}/{n} bytes")
        out += chunk
    return bytes(out)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_connect(proc: subprocess.Popen, port: int) -> socket.socket:
    for _ in range(150):
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            die(f"server exited before connect: {err}")
        try:
            return socket.create_connection(("127.0.0.1", port), timeout=0.5)
        except OSError:
            time.sleep(0.02)
    die("could not connect to localhost NBD server")


def send_request(sock: socket.socket, req_type: int, handle_no: int, offset: int, length: int,
                 payload: bytes | None = None, expect_payload: bool = False) -> bytes:
    handle = struct.pack(">Q", handle_no)
    sock.sendall(struct.pack(">II8sQI", NBD_REQUEST_MAGIC, req_type, handle, offset, length))
    if payload is not None:
        if len(payload) != length:
            die("test bug: write payload length mismatch")
        sock.sendall(payload)
    reply = recv_exact(sock, 16)
    magic, error, got_handle = struct.unpack(">II8s", reply)
    if magic != NBD_REPLY_MAGIC or got_handle != handle:
        die(f"bad reply framing for request {handle_no}")
    if expect_payload and error == 0:
        reply += recv_exact(sock, length)
    return reply


def disconnect(sock: socket.socket, handle_no: int) -> None:
    handle = struct.pack(">Q", handle_no)
    sock.sendall(struct.pack(">II8sQI", NBD_REQUEST_MAGIC, NBD_CMD_DISC, handle, 0, 0))


def synthetic_trace_map(path: Path, disk_size: int) -> None:
    # The differential test exercises tracing code; these ranges are synthetic
    # and intentionally independent of Android/ext4 semantics.
    parts = []
    specs = [
        ("cache", 3, 0x00000, 0x10000, "second-stage-fs-early", False),
        ("persist", 6, 0x10000, 0x20000, "second-stage-fs-early", False),
        ("userdata", 5, 0x20000, 0x30000, "second-stage-late-fs", True),
    ]
    for name, number, start, end, stage, late in specs:
        parts.append({
            "name": name,
            "number": number,
            "stage": stage,
            "late_mount": late,
            "disk_start": start,
            "disk_end": end,
            "evidence": {
                "superblock": {"start": start + 0x1000, "end": start + 0x1100},
                "primary_gdt": {"start": start + 0x2000, "end": start + 0x2100},
            },
        })
    path.write_text(json.dumps({"schema": 2, "disk_size": disk_size, "partitions": parts}) + "\n")


def exercise(sock: socket.socket, size: int, readonly: bool) -> tuple[bytes, list[bytes]]:
    header = recv_exact(sock, HEADER_LEN)
    if header[:8] != NBD_INIT_MAGIC:
        die("bad NBD init magic")
    if struct.unpack_from(">Q", header, 8)[0] != NBD_OLDSTYLE_MAGIC:
        die("bad oldstyle magic")
    if struct.unpack_from(">Q", header, 16)[0] != size:
        die("export size mismatch")

    replies: list[bytes] = []
    req = 0

    req += 1
    replies.append(send_request(sock, NBD_CMD_READ, req, 0x1000, 64, expect_payload=True))

    req += 1
    payload_a = bytes(range(32))
    replies.append(send_request(sock, NBD_CMD_WRITE, req, 0x4000, len(payload_a), payload_a))
    if readonly:
        if struct.unpack_from(">I", replies[-1], 4)[0] != errno.EROFS:
            die("readonly WRITE did not return EROFS")
    else:
        if struct.unpack_from(">I", replies[-1], 4)[0] != 0:
            die("read-write WRITE failed")

    req += 1
    replies.append(send_request(sock, NBD_CMD_READ, req, 0x4000, 32, expect_payload=True))

    if not readonly:
        req += 1
        payload_b = b"FUA-DIFFERENTIAL"
        replies.append(send_request(
            sock, NBD_CMD_WRITE | NBD_CMD_FLAG_FUA, req, 0x5000, len(payload_b), payload_b
        ))

    req += 1
    replies.append(send_request(sock, NBD_CMD_FLUSH, req, 0, 0))

    req += 1
    replies.append(send_request(sock, NBD_CMD_TRIM, req, 0x6000, 4096))
    trim_error = struct.unpack_from(">I", replies[-1], 4)[0]
    if trim_error != (errno.EROFS if readonly else 0):
        die(f"unexpected TRIM status: {trim_error}")

    req += 1
    replies.append(send_request(sock, NBD_CMD_READ, req, size - 8, 16))
    if struct.unpack_from(">I", replies[-1], 4)[0] != errno.EINVAL:
        die("invalid READ did not return EINVAL")

    req += 1
    invalid_payload = b"0123456789abcdef"
    replies.append(send_request(sock, NBD_CMD_WRITE, req, size - 8, 16, invalid_payload))
    if struct.unpack_from(">I", replies[-1], 4)[0] != errno.EINVAL:
        die("invalid WRITE did not return EINVAL")

    req += 1
    replies.append(send_request(sock, 99, req, 0, 0))
    if struct.unpack_from(">I", replies[-1], 4)[0] != errno.EINVAL:
        die("unsupported command did not return EINVAL")

    req += 1
    disconnect(sock, req)
    return header, replies


def run_server(server: Path, image: Path, readonly: bool,
               trace_map: Path | None = None, trace_log: Path | None = None):
    port = free_port()
    cmd = [sys.executable, str(server), "--bind", "127.0.0.1", "--port", str(port),
           "--name", "phase6-v2-diff"]
    if readonly:
        cmd.append("--readonly")
    if trace_map is not None:
        cmd += ["--trace-map", str(trace_map), "--trace-log", str(trace_log)]
    cmd.append(str(image))

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        with wait_connect(proc, port) as sock:
            result = exercise(sock, image.stat().st_size, readonly)
        if trace_log is not None:
            for _ in range(100):
                if trace_log.exists() and "connection_close" in trace_log.read_text():
                    break
                time.sleep(0.01)
        return result
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def compare_case(accepted_server: Path, traced_server: Path, seed: Path, td: Path,
                 readonly: bool) -> None:
    tag = "ro" if readonly else "rw"
    accepted_img = td / f"accepted-{tag}.img"
    traced_img = td / f"traced-{tag}.img"
    shutil.copyfile(seed, accepted_img)
    shutil.copyfile(seed, traced_img)

    trace_map = td / f"trace-{tag}.json"
    trace_log = td / f"trace-{tag}.jsonl"
    synthetic_trace_map(trace_map, seed.stat().st_size)

    accepted_result = run_server(accepted_server, accepted_img, readonly)
    traced_result = run_server(traced_server, traced_img, readonly, trace_map, trace_log)

    if accepted_result != traced_result:
        die(f"{tag}: accepted and traced protocol bytes differ")
    if accepted_img.read_bytes() != traced_img.read_bytes():
        die(f"{tag}: final backing-image bytes differ")

    events = [json.loads(line) for line in trace_log.read_text().splitlines() if line.strip()]
    if len([e for e in events if e.get("event") == "connection_open"]) != 1:
        die(f"{tag}: trace did not record exactly one connection_open")
    if len([e for e in events if e.get("event") == "connection_close"]) != 1:
        die(f"{tag}: trace did not record exactly one connection_close")
    if not any(e.get("event") == "filesystem_evidence_hit" for e in events):
        die(f"{tag}: tracing instrumentation path was not exercised")


def main() -> None:
    ap = argparse.ArgumentParser(description="Differential NBD server protocol self-test")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    accepted_server = root / "scripts/nbd_test_server.py"
    traced_server = root / "scripts/v2/nbd_partition_trace_server.py"
    for path in (accepted_server, traced_server):
        if not path.is_file():
            die(f"server missing: {path}")

    accepted_blob = git_blob_sha1(accepted_server.read_bytes())
    if accepted_blob != EXPECTED_ACCEPTED_SERVER_GIT_BLOB:
        die(
            f"accepted NBD server git-blob={accepted_blob} "
            f"expected={EXPECTED_ACCEPTED_SERVER_GIT_BLOB}"
        )

    with tempfile.TemporaryDirectory(prefix="phase6-v2-nbd-diff-") as td_raw:
        td = Path(td_raw)
        seed = td / "seed.img"
        size = 1024 * 1024
        # Deterministic nonzero bytes make READ and mutation comparisons useful.
        block = bytes(range(256))
        with seed.open("wb") as fp:
            for _ in range(size // len(block)):
                fp.write(block)

        compare_case(accepted_server, traced_server, seed, td, readonly=False)
        compare_case(accepted_server, traced_server, seed, td, readonly=True)

    print("DISKLESS_V2_PHASE6_V2_NBD_DIFFERENTIAL=PASS")
    print(f"accepted_server_git_blob={accepted_blob}")
    print("rw_handshake_and_replies=byte-identical")
    print("rw_final_backing_image=byte-identical")
    print("readonly_handshake_and_replies=byte-identical")
    print("readonly_final_backing_image=byte-identical")
    print("covered=READ,WRITE,FUA,FLUSH,TRIM,invalid-READ,invalid-WRITE,unsupported,DISC")
    print("trace_instrumentation_exercised=yes")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
