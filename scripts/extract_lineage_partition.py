#!/usr/bin/env python3
"""Extract a full-OTA Android *.new.dat.br partition from a LineageOS ZIP.

Usage:
    python3 scripts/extract_lineage_partition.py \
        lineage-18.1-...-flox-signed.zip system ~/system.raw.img

This handles full OTAs that use only new/erase/zero transfer commands.
Incremental-OTA commands such as move/stash/free are rejected explicitly.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

BLOCK_SIZE = 4096


def parse_ranges(text: str):
    nums = [int(x) for x in text.split(",")]
    if not nums or nums[0] != len(nums) - 1 or nums[0] % 2:
        raise ValueError(f"bad transfer range set: {text}")
    return [(nums[i], nums[i + 1]) for i in range(1, len(nums), 2)]


def parse_transfer_list(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("transfer list is too short")

    version = int(lines[0])
    if version < 1 or version > 4:
        raise ValueError(f"unsupported transfer-list version {version}")

    command_start = 4 if version >= 2 else 2
    commands = []
    for line in lines[command_start:]:
        parts = line.split(None, 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) == 2 else ""
        if cmd not in ("new", "erase", "zero"):
            raise ValueError(
                f"unsupported command {cmd!r}; this looks like an incremental OTA, not a full OTA"
            )
        commands.append((cmd, arg))

    if not commands:
        raise ValueError("transfer list contains no commands")

    max_block = 0
    new_blocks = 0
    for cmd, arg in commands:
        for start, end in parse_ranges(arg):
            if end < start:
                raise ValueError(f"invalid range {start},{end}")
            max_block = max(max_block, end)
            if cmd == "new":
                new_blocks += end - start

    return version, commands, max_block, new_blocks


def decompress_brotli(src_br: str, dst_dat: str):
    brotli = shutil.which("brotli")
    if not brotli:
        raise RuntimeError(
            "brotli command not found. On macOS install it with: brew install brotli"
        )

    with open(dst_dat, "wb") as out:
        proc = subprocess.run([brotli, "-d", "-c", src_br], stdout=out)
    if proc.returncode != 0:
        raise RuntimeError(f"brotli decompression failed with exit code {proc.returncode}")


def read_exact(src, size: int):
    data = src.read(size)
    if len(data) != size:
        raise EOFError(f"new.dat ended early: wanted {size} bytes, got {len(data)}")
    return data


def build_raw_image(transfer_text: str, new_dat: str, output: str):
    version, commands, max_block, new_blocks = parse_transfer_list(transfer_text)
    logical_size = max_block * BLOCK_SIZE
    expected_new_bytes = new_blocks * BLOCK_SIZE

    print(f"transfer-list version: {version}")
    print(f"logical image size: {logical_size} bytes")
    print(f"new-data payload: {expected_new_bytes} bytes")

    with open(new_dat, "rb") as src, open(output, "wb") as dst:
        dst.truncate(logical_size)

        for cmd, arg in commands:
            ranges = parse_ranges(arg)
            if cmd in ("erase", "zero"):
                # Newly-created sparse host file is already logically zeroed.
                continue

            for start, end in ranges:
                dst.seek(start * BLOCK_SIZE)
                remaining = (end - start) * BLOCK_SIZE
                while remaining:
                    n = min(16 * 1024 * 1024, remaining)
                    dst.write(read_exact(src, n))
                    remaining -= n

        extra = src.read(1)
        if extra:
            raise ValueError("new.dat contains more data than transfer.list consumes")

    # ext2/3/4 superblock magic is 0xEF53 at byte offset 1024 + 56.
    with open(output, "rb") as f:
        f.seek(1080)
        magic = f.read(2)
    if magic != b"\x53\xef":
        raise ValueError(
            f"output does not look like ext2/3/4 (superblock magic={magic.hex() or 'EOF'})"
        )

    print(f"ext filesystem magic: OK (53ef)")
    print(f"wrote: {output} ({os.path.getsize(output)} bytes logical size)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip", help="LineageOS installation ZIP")
    ap.add_argument("partition", help="partition name, e.g. system or vendor")
    ap.add_argument("output", help="raw output image path")
    args = ap.parse_args()

    zip_path = os.path.expanduser(args.zip)
    output = os.path.expanduser(args.output)
    part = args.partition.strip()

    transfer_name = f"{part}.transfer.list"
    br_name = f"{part}.new.dat.br"
    patch_name = f"{part}.patch.dat"

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        for required in (transfer_name, br_name):
            if required not in names:
                ap.error(f"ZIP does not contain {required}")

        if patch_name in names and zf.getinfo(patch_name).file_size != 0:
            ap.error(
                f"{patch_name} is non-empty; refusing because this script only handles full OTAs"
            )

        transfer_text = zf.read(transfer_name).decode("utf-8")

        with tempfile.TemporaryDirectory(prefix=f"lineage-{part}-") as td:
            br_path = os.path.join(td, br_name)
            dat_path = os.path.join(td, f"{part}.new.dat")

            print(f"extracting {br_name} from ZIP...")
            with zf.open(br_name, "r") as src, open(br_path, "wb") as dst:
                shutil.copyfileobj(src, dst, 16 * 1024 * 1024)

            print("decompressing Brotli payload...")
            decompress_brotli(br_path, dat_path)

            print("reconstructing raw partition image...")
            build_raw_image(transfer_text, dat_path, output)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
