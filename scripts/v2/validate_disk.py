#!/usr/bin/env python3
"""Independently validate a diskless-v2 DOS/MBR disk image."""

import argparse
import json
import os
import struct
import sys

SECTOR = 512
PT_OFF = 446
ENTRY_SIZE = 16
SIG = b"\x55\xaa"


def fail(msg):
    raise RuntimeError(msg)


def read_sector(f, lba):
    f.seek(lba * SECTOR)
    data = f.read(SECTOR)
    if len(data) != SECTOR:
        fail(f"short read at LBA {lba}")
    return data


def parse_entry(raw):
    boot, _schs, type_id, _echs, start_lba, sectors = struct.unpack("<B3sB3sII", raw)
    return {
        "boot": boot,
        "type_id": type_id,
        "start_lba": start_lba,
        "sectors": sectors,
    }


def parse_table_sector(data):
    if data[510:512] != SIG:
        fail("missing 0x55aa partition-table signature")
    return [
        parse_entry(data[PT_OFF + i * ENTRY_SIZE:PT_OFF + (i + 1) * ENTRY_SIZE])
        for i in range(4)
    ]


def ext4_magic(f, start_lba):
    f.seek(start_lba * SECTOR + 1024 + 56)
    return f.read(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    disk = os.path.expanduser(args.disk)
    manifest_path = os.path.expanduser(args.manifest)
    if not os.path.isfile(disk):
        fail(f"disk not found: {disk}")
    if not os.path.isfile(manifest_path):
        fail(f"manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    if manifest.get("schema") != 1:
        fail("unsupported manifest schema")
    if manifest.get("sector_size") != SECTOR:
        fail("validator expects 512-byte sectors")
    if int(manifest.get("nbd_max_part", 0)) < 7:
        fail("manifest nbd_max_part is too small for p7")

    expected = {int(p["number"]): p for p in manifest["partitions"]}
    if sorted(expected) != [1, 2, 3, 4, 5, 6, 7]:
        fail("manifest must contain p1..p7")

    actual_size = os.path.getsize(disk)
    if actual_size != int(manifest["disk_size_bytes"]):
        fail(f"disk size mismatch: actual={actual_size} manifest={manifest['disk_size_bytes']}")

    with open(disk, "rb") as f:
        mbr = parse_table_sector(read_sector(f, 0))

        # Primary table: p1, p2, p3, p4(extended).
        for number in (1, 2, 3, 4):
            got = mbr[number - 1]
            exp = expected[number]
            if got["type_id"] != int(exp["type_id"]):
                fail(f"p{number} type mismatch: {got['type_id']:#x} != {int(exp['type_id']):#x}")
            if got["start_lba"] != int(exp["start_lba"]):
                fail(f"p{number} start mismatch: {got['start_lba']} != {exp['start_lba']}")
            if got["sectors"] != int(exp["sectors"]):
                fail(f"p{number} size mismatch: {got['sectors']} != {exp['sectors']}")

        ext_base = int(expected[4]["start_lba"])
        logical_number = 5
        ebr_lba = int(expected[logical_number]["ebr_lba"])

        while logical_number <= 7:
            table = parse_table_sector(read_sector(f, ebr_lba))
            data = table[0]
            exp = expected[logical_number]
            abs_start = ebr_lba + data["start_lba"]

            if data["type_id"] != int(exp["type_id"]):
                fail(f"p{logical_number} type mismatch")
            if abs_start != int(exp["start_lba"]):
                fail(f"p{logical_number} start mismatch: {abs_start} != {exp['start_lba']}")
            if data["sectors"] != int(exp["sectors"]):
                fail(f"p{logical_number} size mismatch")

            if logical_number < 7:
                link = table[1]
                if link["type_id"] not in (0x05, 0x0F, 0x85):
                    fail(f"p{logical_number} EBR has invalid next-link type {link['type_id']:#x}")
                next_ebr = ext_base + link["start_lba"]
                expected_next = int(expected[logical_number + 1]["ebr_lba"])
                if next_ebr != expected_next:
                    fail(f"EBR link after p{logical_number}: {next_ebr} != {expected_next}")
                ebr_lba = next_ebr
            else:
                if table[1]["type_id"] != 0 or table[1]["sectors"] != 0:
                    fail("last EBR unexpectedly contains a next-link")

            logical_number += 1

        # Filesystem checks are against the final combined disk, not components.
        ext4_names = {"system", "vendor", "cache", "userdata", "persist"}
        for number, exp in expected.items():
            if exp["name"] in ext4_names:
                if ext4_magic(f, int(exp["start_lba"])) != b"\x53\xef":
                    fail(f"p{number} {exp['name']} has no ext4 superblock magic")

    print("DISKLESS_V2_DISK_VERIFIED=1")
    print(f"disk={disk}")
    print(f"disk_size_bytes={actual_size}")
    print(f"nbd_max_part={manifest['nbd_max_part']}")
    for n in range(1, 8):
        p = expected[n]
        print(
            f"p{n}={p['name']} start={p['start_lba']} "
            f"sectors={p['sectors']} size={p['size_bytes']}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
