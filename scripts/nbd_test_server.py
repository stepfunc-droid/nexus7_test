#!/usr/bin/env python3
"""Minimal single-export oldstyle NBD server for the Nexus 7 diskless test.

This intentionally implements only the small protocol subset needed by the
BusyBox nbd-client probe: READ, WRITE, DISC, FLUSH and TRIM.

Run it on the Mac attached to the Nexus USB Ethernet link, for example:

    python3 scripts/nbd_test_server.py \
        --bind 172.16.42.2 --port 10809 \
        --create-size 64M ~/nexus7-nbd-test.img
"""

import argparse
import os
import socket
import struct
import sys

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


def serve_client(conn: socket.socket, image_fd: int, size: int, peer):
    # Oldstyle handshake: magic, oldstyle magic, export size, flags, 124 reserved bytes.
    header = (
        NBD_INIT_MAGIC
        + struct.pack(">Q", NBD_OLDSTYLE_MAGIC)
        + struct.pack(">Q", size)
        + struct.pack(">I", 0)
        + bytes(124)
    )
    conn.sendall(header)
    print(f"client {peer[0]}:{peer[1]} connected; export size={size} bytes", flush=True)

    while True:
        raw = recv_exact(conn, 28)
        if raw is None:
            print("client closed connection", flush=True)
            return

        magic, req_type, handle, offset, length = struct.unpack(">II8sQI", raw)
        if magic != NBD_REQUEST_MAGIC:
            raise RuntimeError(f"bad request magic 0x{magic:08x}")

        cmd = req_type & NBD_CMD_MASK
        fua = bool(req_type & NBD_CMD_FLAG_FUA)

        if cmd == NBD_CMD_DISC:
            print("client requested disconnect", flush=True)
            return

        if offset > size or length > size - offset:
            if cmd == NBD_CMD_WRITE:
                if recv_exact(conn, length) is None:
                    return
            send_reply(conn, 22, handle)  # EINVAL
            continue

        if cmd == NBD_CMD_READ:
            data = os.pread(image_fd, length, offset)
            if len(data) != length:
                data += bytes(length - len(data))
            send_reply(conn, 0, handle, data)

        elif cmd == NBD_CMD_WRITE:
            data = recv_exact(conn, length)
            if data is None:
                return
            written = os.pwrite(image_fd, data, offset)
            if written != length:
                send_reply(conn, 5, handle)  # EIO
                continue
            if fua:
                os.fsync(image_fd)
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_FLUSH:
            os.fsync(image_fd)
            send_reply(conn, 0, handle)

        elif cmd == NBD_CMD_TRIM:
            # A no-op trim is sufficient for this transport probe.
            send_reply(conn, 0, handle)

        else:
            print(f"unsupported NBD command {cmd} (raw type=0x{req_type:08x})", flush=True)
            send_reply(conn, 22, handle)  # EINVAL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="backing image file")
    ap.add_argument("--bind", default="172.16.42.2", help="address to listen on")
    ap.add_argument("--port", type=int, default=10809)
    ap.add_argument("--create-size", metavar="SIZE",
                    help="create/truncate IMAGE to SIZE first, e.g. 64M")
    args = ap.parse_args()

    image = os.path.expanduser(args.image)
    flags = os.O_RDWR | os.O_CREAT
    fd = os.open(image, flags, 0o644)
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
            print(f"NBD oldstyle server listening on {args.bind}:{args.port}", flush=True)
            print(f"backing file: {image} ({size} bytes)", flush=True)

            while True:
                conn, peer = srv.accept()
                with conn:
                    try:
                        serve_client(conn, fd, size, peer)
                    except (BrokenPipeError, ConnectionResetError) as exc:
                        print(f"client disconnected: {exc}", flush=True)
                    except Exception as exc:
                        print(f"client error: {exc}", file=sys.stderr, flush=True)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
