#!/usr/bin/env python3
"""Accepted-style oldstyle NBD server with passive partition-stage tracing.

Protocol behavior is intentionally kept aligned with scripts/nbd_test_server.py.
Audit V2 requires differential self-test against that accepted server before use
on hardware.
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

CMD_NAMES = {
    NBD_CMD_READ: "READ",
    NBD_CMD_WRITE: "WRITE",
    NBD_CMD_DISC: "DISC",
    NBD_CMD_FLUSH: "FLUSH",
    NBD_CMD_TRIM: "TRIM",
}


def parse_size(text: str) -> int:
    s = text.strip().upper()
    mult = 1
    for suffix, factor in (("KIB", 1024), ("MIB", 1024**2), ("GIB", 1024**3),
                           ("KB", 1000), ("MB", 1000**2), ("GB", 1000**3),
                           ("K", 1024), ("M", 1024**2), ("G", 1024**3)):
        if s.endswith(suffix):
            mult = factor
            s = s[:-len(suffix)]
            break
    return int(s, 0) * mult


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


def ranges_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)


class PartitionTraceLogger:
    def __init__(self, trace_map: Path, trace_log: Path, export_size: int):
        data = json.loads(trace_map.read_text())
        if data.get("schema") != 2:
            raise RuntimeError("partition trace map schema must be 2")
        if int(data.get("disk_size", -1)) != export_size:
            raise RuntimeError(
                f"trace-map disk_size={data.get('disk_size')} export_size={export_size}"
            )
        self.partitions = data.get("partitions", [])
        if {p.get("name") for p in self.partitions} != {"cache", "persist", "userdata"}:
            raise RuntimeError("trace map must contain exactly cache,persist,userdata")
        self.trace_log = trace_log
        self.trace_log.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.trace_log.open("w", encoding="utf-8")
        self.started = time.monotonic()

    def close(self):
        self.fp.close()

    def emit(self, event: dict):
        item = dict(event)
        item["elapsed"] = round(time.monotonic() - self.started, 6)
        self.fp.write(json.dumps(item, sort_keys=True) + "\n")
        self.fp.flush()
        print("TRACE " + " ".join(f"{k}={v}" for k, v in item.items()), flush=True)

    def new_connection(self, connection: int, peer) -> dict:
        state = {
            p["name"]: {
                "first_read": False,
                "superblock": False,
                "primary_gdt": False,
                "complete": False,
            }
            for p in self.partitions
        }
        state["_first_request"] = False
        self.emit({
            "event": "connection_open",
            "connection": connection,
            "peer": f"{peer[0]}:{peer[1]}",
        })
        return state

    def close_connection(self, connection: int, reason: str):
        self.emit({"event": "connection_close", "connection": connection, "reason": reason})

    def on_request(self, connection: int, request: int, cmd: str, offset: int, length: int,
                   state: dict) -> None:
        if state["_first_request"]:
            return
        state["_first_request"] = True
        self.emit({
            "event": "nbd_first_request",
            "connection": connection,
            "request": request,
            "cmd": cmd,
            "offset": offset,
            "length": length,
        })

    def on_read_complete(self, connection: int, request: int, offset: int, length: int,
                         state: dict) -> None:
        read_start = offset
        read_end = offset + length
        for p in self.partitions:
            name = p["name"]
            pstate = state[name]
            pstart = int(p["disk_start"])
            pend = int(p["disk_end"])
            if not ranges_overlap(read_start, read_end, pstart, pend):
                continue

            if not pstate["first_read"]:
                pstate["first_read"] = True
                self.emit({
                    "event": "partition_first_read",
                    "connection": connection,
                    "request": request,
                    "partition": name,
                    "stage": p["stage"],
                    "offset": offset,
                    "length": length,
                })

            for evidence_name in ("superblock", "primary_gdt"):
                erange = p["evidence"][evidence_name]
                if pstate[evidence_name]:
                    continue
                if ranges_overlap(read_start, read_end, int(erange["start"]), int(erange["end"])):
                    pstate[evidence_name] = True
                    self.emit({
                        "event": "filesystem_evidence_hit",
                        "connection": connection,
                        "request": request,
                        "partition": name,
                        "evidence": evidence_name,
                        "stage": p["stage"],
                        "offset": offset,
                        "length": length,
                    })

            if (not pstate["complete"] and pstate["superblock"] and
                    pstate["primary_gdt"]):
                pstate["complete"] = True
                self.emit({
                    "event": "filesystem_evidence_complete",
                    "connection": connection,
                    "request": request,
                    "partition": name,
                    "stage": p["stage"],
                    "late_mount": bool(p["late_mount"]),
                })


def summary(prefix: str, stats: dict) -> str:
    last = stats.get("last")
    if last:
        last_text = (
            f"{last['cmd']} offset=0x{last['offset']:x} ({last['offset']}) "
            f"length={last['length']} fua={int(last['fua'])}"
        )
    else:
        last_text = "none"
    elapsed = time.monotonic() - stats["started"]
    return (
        f"{prefix} phase={stats['phase']} elapsed={elapsed:.3f}s "
        f"requests={stats['requests']} reads={stats['reads']} writes={stats['writes']} "
        f"read_bytes={stats['read_bytes']} write_bytes={stats['write_bytes']} "
        f"last=[{last_text}]"
    )


def serve_client(conn: socket.socket, image_fd: int, size: int, peer, readonly: bool,
                 label: str, port: int, stats: dict, connection: int,
                 tracer: PartitionTraceLogger | None):
    prefix = f"[{label}:{port}]"
    tx_flags = NBD_FLAG_HAS_FLAGS
    if readonly:
        tx_flags |= NBD_FLAG_READ_ONLY

    header = (
        NBD_INIT_MAGIC
        + struct.pack(">Q", NBD_OLDSTYLE_MAGIC)
        + struct.pack(">Q", size)
        + struct.pack(">I", tx_flags)
        + bytes(124)
    )
    stats["phase"] = "handshake-send"
    conn.sendall(header)
    mode = "read-only" if readonly else "read-write"
    print(f"{prefix} client {peer[0]}:{peer[1]} connected; export size={size} bytes ({mode})", flush=True)
    trace_state = tracer.new_connection(connection, peer) if tracer else None
    request_index = 0

    while True:
        stats["phase"] = "request-header-recv"
        raw = recv_exact(conn, 28)
        if raw is None:
            if tracer:
                tracer.close_connection(connection, "eof")
            print(summary(f"{prefix} client closed connection;", stats), flush=True)
            return

        magic, req_type, handle, offset, length = struct.unpack(">II8sQI", raw)
        if magic != NBD_REQUEST_MAGIC:
            raise RuntimeError(f"bad request magic 0x{magic:08x}")

        request_index += 1
        cmd = req_type & NBD_CMD_MASK
        fua = bool(req_type & NBD_CMD_FLAG_FUA)
        cmd_name = CMD_NAMES.get(cmd, f"UNKNOWN({cmd})")
        stats["requests"] += 1
        stats["last"] = {
            "cmd": cmd_name,
            "offset": offset,
            "length": length,
            "fua": fua,
        }
        if tracer:
            tracer.on_request(connection, request_index, cmd_name, offset, length, trace_state)

        if cmd == NBD_CMD_DISC:
            stats["phase"] = "disconnect"
            if tracer:
                tracer.close_connection(connection, "client-disc")
            print(summary(f"{prefix} client requested disconnect;", stats), flush=True)
            return

        if offset > size or length > size - offset:
            stats["phase"] = "invalid-range"
            if cmd == NBD_CMD_WRITE:
                if recv_exact(conn, length) is None:
                    return
            send_reply(conn, errno.EINVAL, handle)
            continue

        if cmd == NBD_CMD_READ:
            stats["reads"] += 1
            stats["read_bytes"] += length
            stats["phase"] = "read-image"
            data = os.pread(image_fd, length, offset)
            if len(data) != length:
                data += bytes(length - len(data))
            stats["phase"] = "read-reply-send"
            send_reply(conn, 0, handle, data)
            if tracer:
                tracer.on_read_complete(connection, request_index, offset, length, trace_state)

        elif cmd == NBD_CMD_WRITE:
            stats["writes"] += 1
            stats["write_bytes"] += length
            stats["phase"] = "write-payload-recv"
            data = recv_exact(conn, length)
            if data is None:
                if tracer:
                    tracer.close_connection(connection, "closed-during-write")
                print(summary(f"{prefix} client closed during write payload;", stats), flush=True)
                return
            if readonly:
                stats["phase"] = "readonly-error-send"
                send_reply(conn, errno.EROFS, handle)
                continue
            stats["phase"] = "write-image"
            written = os.pwrite(image_fd, data, offset)
            if written != length:
                stats["phase"] = "write-error-send"
                send_reply(conn, errno.EIO, handle)
                continue
            if fua:
                stats["phase"] = "write-fsync"
                os.fsync(image_fd)
            stats["phase"] = "write-reply-send"
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_FLUSH:
            stats["phase"] = "flush"
            if not readonly:
                os.fsync(image_fd)
            stats["phase"] = "flush-reply-send"
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_TRIM:
            stats["phase"] = "trim-reply-send"
            if readonly:
                send_reply(conn, errno.EROFS, handle)
            else:
                send_reply(conn, 0, handle)

        else:
            stats["phase"] = "unsupported-command"
            print(f"{prefix} unsupported NBD command {cmd} (raw type=0x{req_type:08x})", flush=True)
            send_reply(conn, errno.EINVAL, handle)


def new_stats():
    return {
        "started": time.monotonic(),
        "phase": "accepted",
        "requests": 0,
        "reads": 0,
        "writes": 0,
        "read_bytes": 0,
        "write_bytes": 0,
        "last": None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="backing image file")
    ap.add_argument("--bind", default="172.16.42.2", help="address to listen on")
    ap.add_argument("--port", type=int, default=10809)
    ap.add_argument("--name", default="nbd", help="human-readable export name for diagnostics")
    ap.add_argument("--create-size", metavar="SIZE",
                    help="create/truncate IMAGE to SIZE first, e.g. 64M")
    ap.add_argument("--readonly", action="store_true",
                    help="export IMAGE read-only and reject write/trim requests")
    ap.add_argument("--trace-map", type=Path)
    ap.add_argument("--trace-log", type=Path)
    args = ap.parse_args()

    if args.readonly and args.create_size:
        ap.error("--readonly cannot be combined with --create-size")
    if bool(args.trace_map) != bool(args.trace_log):
        ap.error("--trace-map and --trace-log must be supplied together")

    image = os.path.expanduser(args.image)
    flags = os.O_RDONLY if args.readonly else (os.O_RDWR | os.O_CREAT)
    fd = os.open(image, flags, 0o644)
    prefix = f"[{args.name}:{args.port}]"
    tracer = None

    try:
        if args.create_size:
            size = parse_size(args.create_size)
            os.ftruncate(fd, size)
        else:
            size = os.fstat(fd).st_size
        if size <= 0:
            ap.error("image is empty; use --create-size or provide a non-empty image")

        if args.trace_map:
            tracer = PartitionTraceLogger(args.trace_map, args.trace_log, size)

        connection = 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((args.bind, args.port))
            srv.listen(1)
            mode = "read-only" if args.readonly else "read-write"
            print(f"{prefix} NBD oldstyle server listening on {args.bind}:{args.port}", flush=True)
            print(f"{prefix} backing file: {image} ({size} bytes, {mode})", flush=True)

            while True:
                conn, peer = srv.accept()
                connection += 1
                stats = new_stats()
                with conn:
                    try:
                        serve_client(conn, fd, size, peer, args.readonly,
                                     args.name, args.port, stats, connection, tracer)
                    except (BrokenPipeError, ConnectionResetError, TimeoutError, socket.timeout) as exc:
                        if tracer:
                            tracer.close_connection(connection, f"transport-error:{exc!r}")
                        print(summary(f"{prefix} client transport error={exc!r};", stats),
                              file=sys.stderr, flush=True)
                    except Exception as exc:
                        if tracer:
                            tracer.close_connection(connection, f"error:{exc!r}")
                        print(summary(f"{prefix} client error={exc!r};", stats),
                              file=sys.stderr, flush=True)
    finally:
        os.close(fd)
        if tracer:
            tracer.close()


if __name__ == "__main__":
    main()
