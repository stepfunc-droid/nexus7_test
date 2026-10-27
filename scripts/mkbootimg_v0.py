#!/usr/bin/env python3
"""Minimal Android boot image v0 packer for Nexus 7 (2013) / flo.

This intentionally implements only the legacy header format needed by flo.
It avoids distro mkbootimg packaging differences and has no third-party Python
dependencies.
"""

import argparse
import hashlib
import os
import struct
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
BOOT_NAME_SIZE = 16
BOOT_ARGS_SIZE = 512
BOOT_EXTRA_ARGS_SIZE = 1024
BOOT_ID_SIZE = 32


def parse_int(value: str) -> int:
    return int(value, 0)


def pad_to_page(fp, page_size: int) -> None:
    padding = (-fp.tell()) % page_size
    if padding:
        fp.write(b"\x00" * padding)


def read_file(path: str | None) -> bytes:
    if not path:
        return b""
    return Path(path).read_bytes()


def fixed_bytes(text: str, size: int, field: str) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) > size:
        raise SystemExit(f"{field} is too long: {len(raw)} bytes > {size}")
    return raw.ljust(size, b"\x00")


def update_sha(sha: "hashlib._Hash", blob: bytes) -> None:
    sha.update(blob)
    sha.update(struct.pack("<I", len(blob)))


def main() -> None:
    p = argparse.ArgumentParser(description="Create a legacy Android boot.img (header v0)")
    p.add_argument("--kernel", required=True)
    p.add_argument("--ramdisk")
    p.add_argument("--second")
    p.add_argument("--cmdline", default="")
    p.add_argument("--board", default="")
    p.add_argument("--base", type=parse_int, default=0x10000000)
    p.add_argument("--kernel_offset", type=parse_int, default=0x00008000)
    p.add_argument("--ramdisk_offset", type=parse_int, default=0x01000000)
    p.add_argument("--second_offset", type=parse_int, default=0x00F00000)
    p.add_argument("--tags_offset", type=parse_int, default=0x00000100)
    p.add_argument("--pagesize", type=parse_int, default=2048)
    p.add_argument("--output", "-o", required=True)
    args = p.parse_args()

    if args.pagesize <= 0 or args.pagesize & (args.pagesize - 1):
        raise SystemExit("pagesize must be a positive power of two")

    kernel = read_file(args.kernel)
    ramdisk = read_file(args.ramdisk)
    second = read_file(args.second)
    if not kernel:
        raise SystemExit("kernel image is empty")

    # Android boot image header v0. In the historical structure, the first
    # two words after page_size were dt_size/unused; modern definitions call
    # them header_version/os_version. Zero is correct for this legacy image.
    fields = (
        len(kernel),
        args.base + args.kernel_offset,
        len(ramdisk),
        args.base + args.ramdisk_offset if ramdisk else 0,
        len(second),
        args.base + args.second_offset if second else 0,
        args.base + args.tags_offset,
        args.pagesize,
        0,  # header_version / legacy dt_size
        0,  # os_version / legacy unused
    )

    cmd = args.cmdline.encode("utf-8")
    if len(cmd) > BOOT_ARGS_SIZE + BOOT_EXTRA_ARGS_SIZE:
        raise SystemExit("cmdline is longer than 1536 bytes")

    sha = hashlib.sha1()
    update_sha(sha, kernel)
    update_sha(sha, ramdisk)
    update_sha(sha, second)
    image_id = sha.digest().ljust(BOOT_ID_SIZE, b"\x00")

    with open(args.output, "wb") as out:
        out.write(BOOT_MAGIC)
        out.write(struct.pack("<10I", *fields))
        out.write(fixed_bytes(args.board, BOOT_NAME_SIZE, "board"))
        out.write(cmd[:BOOT_ARGS_SIZE].ljust(BOOT_ARGS_SIZE, b"\x00"))
        out.write(image_id)
        out.write(cmd[BOOT_ARGS_SIZE:].ljust(BOOT_EXTRA_ARGS_SIZE, b"\x00"))
        pad_to_page(out, args.pagesize)

        out.write(kernel)
        pad_to_page(out, args.pagesize)
        if ramdisk:
            out.write(ramdisk)
            pad_to_page(out, args.pagesize)
        if second:
            out.write(second)
            pad_to_page(out, args.pagesize)

    print(f"created {args.output} ({os.path.getsize(args.output)} bytes)")
    print(f"kernel_addr=0x{fields[1]:08x} ramdisk_addr=0x{fields[3]:08x} tags_addr=0x{fields[6]:08x}")


if __name__ == "__main__":
    main()
