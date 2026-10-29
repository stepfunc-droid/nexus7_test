#!/usr/bin/env python3
"""Oldstyle NBD server with optional file-range tracing for Phase6 R2/R3.

This is intentionally separate from the accepted Phase3/4 nbd_test_server.py.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import socket
import struct
import sys
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
NBD_CMD_MASK = 0xFFFF
NBD_CMD_FLAG_FUA = 1 << 16
NBD_FLAG_HAS_FLAGS = 1 << 0
NBD_FLAG_READ_ONLY = 1 << 1


def recv_exact(sock: socket.socket, n: int):
    chunks = []
    left = n
    while left:
        data = sock.recv(left)
        if not data:
            return None
        chunks.append(data)
        left -= len(data)
    return b"".join(chunks)


def send_reply(sock: socket.socket, error: int, handle: bytes, payload: bytes = b""):
    sock.sendall(struct.pack(">II8s", NBD_REPLY_MAGIC, error, handle))
    if payload:
        sock.sendall(payload)


def merge_interval(intervals: list[tuple[int, int]], start: int, end: int) -> list[tuple[int, int]]:
    if end <= start:
        return intervals
    merged = []
    placed = False
    for a, b in sorted(intervals + [(start, end)]):
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    return [(a, b) for a, b in merged]


class TraceLogger:
    def __init__(self, trace_map: Path, trace_log: Path):
        data = json.loads(trace_map.read_text())
        if data.get("schema") != 1:
            raise RuntimeError("unsupported trace-map schema")
        self.markers = data.get("markers", [])
        if not self.markers:
            raise RuntimeError("trace map contains no markers")
        self.trace_log = trace_log
        self.trace_log.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.trace_log.open("w", encoding="utf-8")
        self.started = time.monotonic()

    def close(self):
        self.fp.close()

    def emit(self, event: dict):
        event = dict(event)
        event["elapsed"] = round(time.monotonic() - self.started, 6)
        self.fp.write(json.dumps(event, sort_keys=True) + "\n")
        self.fp.flush()
        print("TRACE " + " ".join(f"{k}={v}" for k, v in event.items()), flush=True)

    def new_connection(self, connection: int, peer) -> dict:
        state = {}
        for marker in self.markers:
            state[marker["name"]] = {
                "covered": [],
                "complete": False,
                "first_hit": False,
            }
        self.emit({"event": "connection_open", "connection": connection, "peer": f"{peer[0]}:{peer[1]}"})
        return state

    def close_connection(self, connection: int, reason: str):
        self.emit({"event": "connection_close", "connection": connection, "reason": reason})

    def on_read_complete(self, connection: int, request: int, offset: int, length: int, state: dict):
        read_start, read_end = offset, offset + length
        for marker in self.markers:
            name = marker["name"]
            mstate = state[name]
            changed = False
            for r in marker["ranges"]:
                ds = int(r["disk_offset"])
                de = ds + int(r["length"])
                start = max(read_start, ds)
                end = min(read_end, de)
                if end <= start:
                    continue
                file_start = int(r["file_offset"]) + (start - ds)
                file_end = file_start + (end - start)
                before = sum(b - a for a, b in mstate["covered"])
                mstate["covered"] = merge_interval(mstate["covered"], file_start, file_end)
                after = sum(b - a for a, b in mstate["covered"])
                changed |= after > before

            if changed and not mstate["first_hit"]:
                mstate["first_hit"] = True
                self.emit({
                    "event": "marker_first_hit",
                    "connection": connection,
                    "request": request,
                    "marker": name,
                    "order": marker["order"],
                })

            covered = sum(b - a for a, b in mstate["covered"])
            required = int(marker["required_coverage"])
            if not mstate["complete"] and covered >= required:
                mstate["complete"] = True
                self.emit({
                    "event": "marker_complete",
                    "connection": connection,
                    "request": request,
                    "marker": name,
                    "order": marker["order"],
                    "covered": covered,
                    "required": required,
                    "stage": marker["stage"],
                    "path": marker["resolved_path"],
                })


def serve_client(conn: socket.socket, image_fd: int, size: int, peer, readonly: bool,
                 connection: int, tracer: TraceLogger | None):
    tx_flags = NBD_FLAG_HAS_FLAGS | (NBD_FLAG_READ_ONLY if readonly else 0)
    header = (
        NBD_INIT_MAGIC
        + struct.pack(">Q", NBD_OLDSTYLE_MAGIC)
        + struct.pack(">Q", size)
        + struct.pack(">I", tx_flags)
        + bytes(124)
    )
    conn.sendall(header)
    state = tracer.new_connection(connection, peer) if tracer else None
    request = 0
    print(f"[phase6-r2:{connection}] client {peer[0]}:{peer[1]} connected size={size}", flush=True)

    while True:
        raw = recv_exact(conn, 28)
        if raw is None:
            if tracer:
                tracer.close_connection(connection, "eof")
            return
        magic, req_type, handle, offset, length = struct.unpack(">II8sQI", raw)
        if magic != NBD_REQUEST_MAGIC:
            raise RuntimeError(f"bad request magic 0x{magic:08x}")
        request += 1
        cmd = req_type & NBD_CMD_MASK
        fua = bool(req_type & NBD_CMD_FLAG_FUA)

        if cmd == NBD_CMD_DISC:
            if tracer:
                tracer.close_connection(connection, "client-disc")
            return
        if offset > size or length > size - offset:
            if cmd == NBD_CMD_WRITE and recv_exact(conn, length) is None:
                return
            send_reply(conn, errno.EINVAL, handle)
            continue

        if cmd == NBD_CMD_READ:
            data = os.pread(image_fd, length, offset)
            if len(data) != length:
                data += bytes(length - len(data))
            send_reply(conn, 0, handle, data)
            if tracer:
                tracer.on_read_complete(connection, request, offset, length, state)

        elif cmd == NBD_CMD_WRITE:
            data = recv_exact(conn, length)
            if data is None:
                if tracer:
                    tracer.close_connection(connection, "closed-during-write")
                return
            if readonly:
                send_reply(conn, errno.EROFS, handle)
                continue
            written = os.pwrite(image_fd, data, offset)
            if written != length:
                send_reply(conn, errno.EIO, handle)
                continue
            if fua:
                os.fsync(image_fd)
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_FLUSH:
            if not readonly:
                os.fsync(image_fd)
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_TRIM:
            send_reply(conn, errno.EROFS if readonly else 0, handle)

        else:
            send_reply(conn, errno.EINVAL, handle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=10810)
    ap.add_argument("--readonly", action="store_true")
    ap.add_argument("--trace-map", type=Path)
    ap.add_argument("--trace-log", type=Path)
    args = ap.parse_args()

    if bool(args.trace_map) != bool(args.trace_log):
        ap.error("--trace-map and --trace-log must be supplied together")
    if not args.image.is_file():
        ap.error(f"image not found: {args.image}")

    tracer = TraceLogger(args.trace_map, args.trace_log) if args.trace_map else None
    flags = os.O_RDONLY if args.readonly else os.O_RDWR
    fd = os.open(args.image, flags)
    size = os.fstat(fd).st_size
    connection = 0

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((args.bind, args.port))
            srv.listen(1)
            print(f"[phase6-r2] listening on {args.bind}:{args.port} disk={args.image}", flush=True)
            while True:
                conn, peer = srv.accept()
                connection += 1
                with conn:
                    try:
                        serve_client(conn, fd, size, peer, args.readonly, connection, tracer)
                    except (BrokenPipeError, ConnectionResetError, TimeoutError, socket.timeout) as exc:
                        if tracer:
                            tracer.close_connection(connection, f"transport-error:{exc!r}")
                        print(f"[phase6-r2:{connection}] transport error: {exc!r}", file=sys.stderr, flush=True)
                    except Exception as exc:
                        if tracer:
                            tracer.close_connection(connection, f"error:{exc!r}")
                        print(f"[phase6-r2:{connection}] error: {exc!r}", file=sys.stderr, flush=True)
    finally:
        os.close(fd)
        if tracer:
            tracer.close()


if __name__ == "__main__":
    main()
