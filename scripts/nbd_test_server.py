#!/usr/bin/env python3
"""Minimal oldstyle NBD server with diagnostics for the Nexus 7 diskless test."""

import argparse
import errno
import os
import socket
import struct
import sys
import time

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
                 label: str, port: int, stats: dict):
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

    while True:
        stats["phase"] = "request-header-recv"
        raw = recv_exact(conn, 28)
        if raw is None:
            print(summary(f"{prefix} client closed connection;", stats), flush=True)
            return

        magic, req_type, handle, offset, length = struct.unpack(">II8sQI", raw)
        if magic != NBD_REQUEST_MAGIC:
            raise RuntimeError(f"bad request magic 0x{magic:08x}")

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

        if cmd == NBD_CMD_DISC:
            stats["phase"] = "disconnect"
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

        elif cmd == NBD_CMD_WRITE:
            stats["writes"] += 1
            stats["write_bytes"] += length
            stats["phase"] = "write-payload-recv"
            data = recv_exact(conn, length)
            if data is None:
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
    args = ap.parse_args()

    if args.readonly and args.create_size:
        ap.error("--readonly cannot be combined with --create-size")

    image = os.path.expanduser(args.image)
    flags = os.O_RDONLY if args.readonly else (os.O_RDWR | os.O_CREAT)
    fd = os.open(image, flags, 0o644)
    prefix = f"[{args.name}:{args.port}]"

    try:
        if args.create_size:
            size = parse_size(args.create_size)
            os.ftruncate(fd, size)
        else:
            size = os.fstat(fd).st_size
        if size <= 0:
            ap.error("image is empty; use --create-size or provide a non-empty image")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((args.bind, args.port))
            srv.listen(1)
            mode = "read-only" if args.readonly else "read-write"
            print(f"{prefix} NBD oldstyle server listening on {args.bind}:{args.port}", flush=True)
            print(f"{prefix} backing file: {image} ({size} bytes, {mode})", flush=True)

            while True:
                conn, peer = srv.accept()
                stats = new_stats()
                with conn:
                    try:
                        serve_client(conn, fd, size, peer, args.readonly,
                                     args.name, args.port, stats)
                    except (BrokenPipeError, ConnectionResetError, TimeoutError, socket.timeout) as exc:
                        print(summary(f"{prefix} client transport error={exc!r};", stats),
                              file=sys.stderr, flush=True)
                    except Exception as exc:
                        print(summary(f"{prefix} client error={exc!r};", stats),
                              file=sys.stderr, flush=True)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
