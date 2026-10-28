#!/usr/bin/env python3
"""Unpack a legacy Android boot.img (v0-style / Qualcomm layout)."""

import argparse
import json
import os
import struct
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
HEADER_FIXED = 8 + 10 * 4 + 16 + 512 + 32 + 1024


def align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def cstr(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("utf-8", "replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("outdir")
    args = ap.parse_args()

    data = Path(args.image).read_bytes()
    if len(data) < HEADER_FIXED or data[:8] != BOOT_MAGIC:
        raise SystemExit("not a legacy Android boot image")

    off = 8
    fields = struct.unpack_from("<10I", data, off)
    off += 40
    (
        kernel_size, kernel_addr,
        ramdisk_size, ramdisk_addr,
        second_size, second_addr,
        tags_addr, page_size,
        dt_size, unused,
    ) = fields

    if page_size <= 0 or page_size & (page_size - 1):
        raise SystemExit(f"invalid page size: {page_size}")

    board = cstr(data[off:off+16]); off += 16
    cmdline = cstr(data[off:off+512]); off += 512
    image_id = data[off:off+32].hex(); off += 32
    extra = cstr(data[off:off+1024]); off += 1024
    full_cmdline = (cmdline + extra).strip()

    cursor = page_size
    k0 = cursor; k1 = k0 + kernel_size
    cursor = align_up(k1, page_size)
    r0 = cursor; r1 = r0 + ramdisk_size
    cursor = align_up(r1, page_size)
    s0 = cursor; s1 = s0 + second_size
    cursor = align_up(s1, page_size)
    d0 = cursor; d1 = d0 + dt_size

    if max(k1, r1, s1, d1) > len(data):
        raise SystemExit("boot image is truncated")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "kernel").write_bytes(data[k0:k1])
    if ramdisk_size:
        (out / "ramdisk").write_bytes(data[r0:r1])
    if second_size:
        (out / "second").write_bytes(data[s0:s1])
    if dt_size:
        (out / "dt.img").write_bytes(data[d0:d1])

    meta = {
        "kernel_size": kernel_size,
        "kernel_addr": f"0x{kernel_addr:08x}",
        "ramdisk_size": ramdisk_size,
        "ramdisk_addr": f"0x{ramdisk_addr:08x}",
        "second_size": second_size,
        "second_addr": f"0x{second_addr:08x}",
        "tags_addr": f"0x{tags_addr:08x}",
        "page_size": page_size,
        "dt_size": dt_size,
        "board": board,
        "cmdline": full_cmdline,
        "image_id": image_id,
        "input_size": len(data),
    }
    (out / "boot.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(json.dumps(meta, indent=2))
    print(f"unpacked to: {out}")


if __name__ == "__main__":
    main()
