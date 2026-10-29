#!/usr/bin/env python3
"""Assemble the diskless-v2 single-NBD disk image.

The layout is deliberately DOS/MBR so the old flo Linux 3.4 partition scanner can
consume it. Three primary partitions are followed by one extended partition and
logical partitions. All data partitions are aligned to 1 MiB by default.

This script does not create filesystems. It combines already-prepared raw
filesystem images and writes deterministic MBR/EBR metadata around them.
"""

import argparse
import errno
import json
import os
import struct
import sys
from pathlib import Path

MBR_SIZE = 512
PART_TABLE_OFFSET = 446
PART_ENTRY_SIZE = 16
MBR_SIGNATURE = b"\x55\xaa"
DISK_SIGNATURE = b"N7V2"  # deterministic four-byte MBR disk signature
COPY_CHUNK = 8 * 1024 * 1024


def fail(msg):
    raise RuntimeError(msg)


def align_up(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


def part_entry(type_id, start_lba, sectors, bootable=False):
    if not (0 <= start_lba <= 0xFFFFFFFF):
        fail(f"start LBA out of MBR range: {start_lba}")
    if not (0 < sectors <= 0xFFFFFFFF):
        fail(f"partition length out of MBR range: {sectors}")
    # Linux uses the LBA fields. Mark CHS as saturated/invalid rather than
    # attempting geometry that has no meaning for an NBD disk.
    chs = b"\xfe\xff\xff"
    return struct.pack(
        "<B3sB3sII",
        0x80 if bootable else 0x00,
        chs,
        type_id,
        chs,
        start_lba,
        sectors,
    )


def load_layout(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("schema") != 1:
        fail("unsupported layout schema")
    if cfg.get("partition_table") != "dos":
        fail("v2 currently requires partition_table=dos")
    sector_size = int(cfg.get("sector_size", 0))
    if sector_size != 512:
        fail("DOS layout currently requires 512-byte sectors")
    alignment = int(cfg.get("alignment_sectors", 0))
    if alignment <= 0 or alignment & (alignment - 1):
        fail("alignment_sectors must be a positive power of two")
    parts = cfg.get("partitions") or []
    numbers = [int(p["number"]) for p in parts]
    if numbers != [1, 2, 3, 4, 5, 6, 7]:
        fail("v2 DOS layout must define partition numbers 1..7 in order")
    if [p["kind"] for p in parts] != [
        "primary", "primary", "primary", "extended", "logical", "logical", "logical"
    ]:
        fail("v2 DOS layout must be 3 primary + extended + 3 logical")
    for p in parts:
        if p["kind"] == "extended":
            continue
        size = int(p["size_bytes"])
        if size <= 0 or size % sector_size:
            fail(f"{p['name']}: size_bytes must be positive and sector-aligned")
    return cfg


def calculate_layout(cfg):
    ss = cfg["sector_size"]
    align = cfg["alignment_sectors"]
    parts = cfg["partitions"]
    result = []

    cursor = align  # reserve the first MiB for MBR/alignment
    for p in parts[:3]:
        sectors = p["size_bytes"] // ss
        start = align_up(cursor, align)
        result.append({**p, "start_lba": start, "sectors": sectors})
        cursor = start + sectors

    ext = parts[3]
    ext_start = align_up(cursor, align)
    ebr_cursor = ext_start

    logicals = []
    for p in parts[4:]:
        ebr_lba = align_up(ebr_cursor, align)
        start = ebr_lba + align
        sectors = p["size_bytes"] // ss
        logicals.append({
            **p,
            "ebr_lba": ebr_lba,
            "start_lba": start,
            "sectors": sectors,
        })
        ebr_cursor = start + sectors

    # One aligned tail region makes the final logical partition and EBR chain
    # unambiguous and leaves room for future metadata without moving partitions.
    disk_sectors = align_up(ebr_cursor, align) + align
    ext_sectors = disk_sectors - ext_start
    result.append({**ext, "start_lba": ext_start, "sectors": ext_sectors})
    result.extend(logicals)

    return result, disk_sectors


def write_sector(f, lba, data, sector_size=512):
    if len(data) != sector_size:
        fail(f"internal error: sector write is {len(data)} bytes")
    f.seek(lba * sector_size)
    f.write(data)


def write_partition_tables(f, computed, disk_sectors, sector_size=512):
    primaries = computed[:4]
    logicals = computed[4:]
    extended = primaries[3]

    mbr = bytearray(MBR_SIZE)
    mbr[440:444] = DISK_SIGNATURE
    for i, p in enumerate(primaries):
        entry = part_entry(int(p["type_id"]), int(p["start_lba"]), int(p["sectors"]))
        off = PART_TABLE_OFFSET + i * PART_ENTRY_SIZE
        mbr[off:off + PART_ENTRY_SIZE] = entry
    mbr[510:512] = MBR_SIGNATURE
    write_sector(f, 0, bytes(mbr), sector_size)

    ext_base = int(extended["start_lba"])
    ext_end = ext_base + int(extended["sectors"])

    for idx, p in enumerate(logicals):
        ebr = bytearray(MBR_SIZE)
        # Entry 0 is relative to this EBR.
        rel_start = int(p["start_lba"]) - int(p["ebr_lba"])
        ebr[PART_TABLE_OFFSET:PART_TABLE_OFFSET + PART_ENTRY_SIZE] = part_entry(
            int(p["type_id"]), rel_start, int(p["sectors"])
        )

        # Entry 1 links to the next EBR, relative to the extended-partition base.
        if idx + 1 < len(logicals):
            nxt = logicals[idx + 1]
            rel_ebr = int(nxt["ebr_lba"]) - ext_base
            remaining = ext_end - int(nxt["ebr_lba"])
            ebr[PART_TABLE_OFFSET + PART_ENTRY_SIZE:PART_TABLE_OFFSET + 2 * PART_ENTRY_SIZE] = part_entry(
                0x0F, rel_ebr, remaining
            )

        ebr[510:512] = MBR_SIGNATURE
        write_sector(f, int(p["ebr_lba"]), bytes(ebr), sector_size)


def ext4_magic(path, offset=0):
    with open(path, "rb") as f:
        f.seek(offset + 1024 + 56)
        return f.read(2)


def sparse_copy_fallback(src, dst, dst_offset, size):
    zeros = bytes(COPY_CHUNK)
    pos = 0
    while pos < size:
        chunk = src.read(min(COPY_CHUNK, size - pos))
        if not chunk:
            fail("source image ended early during copy")
        if chunk != zeros[:len(chunk)]:
            dst.seek(dst_offset + pos)
            dst.write(chunk)
        pos += len(chunk)


def sparse_copy(src_path, dst, dst_offset):
    size = os.path.getsize(src_path)
    with open(src_path, "rb", buffering=0) as src:
        # Prefer filesystem hole information. APFS/ext4 sparse component images
        # then copy only allocated regions instead of scanning multi-GiB zeros.
        if hasattr(os, "SEEK_DATA") and hasattr(os, "SEEK_HOLE"):
            pos = 0
            try:
                while pos < size:
                    try:
                        data_off = os.lseek(src.fileno(), pos, os.SEEK_DATA)
                    except OSError as exc:
                        if exc.errno == errno.ENXIO:
                            return
                        raise
                    hole_off = os.lseek(src.fileno(), data_off, os.SEEK_HOLE)
                    end = min(hole_off, size)
                    os.lseek(src.fileno(), data_off, os.SEEK_SET)
                    dst.seek(dst_offset + data_off)
                    remaining = end - data_off
                    while remaining:
                        chunk = src.read(min(COPY_CHUNK, remaining))
                        if not chunk:
                            fail("source image ended early during sparse extent copy")
                        dst.write(chunk)
                        remaining -= len(chunk)
                    pos = end
                return
            except OSError as exc:
                if exc.errno not in (errno.EINVAL, errno.ENOTSUP, getattr(errno, "EOPNOTSUPP", errno.ENOTSUP)):
                    raise
                src.seek(0)

        src.seek(0)
        sparse_copy_fallback(src, dst, dst_offset, size)


def parse_sources(values):
    result = {}
    for item in values:
        if "=" not in item:
            fail(f"bad --source value {item!r}; expected key=/path/image")
        key, value = item.split("=", 1)
        if not key or not value:
            fail(f"bad --source value {item!r}")
        result[key] = os.path.expanduser(value)
    return result


def validate_component_sources(computed, sources, sector_size):
    used = {}
    for p in computed:
        source_key = p.get("source")
        if not source_key or source_key == "zero" or p["kind"] == "extended":
            continue
        path = sources.get(source_key)
        if not path:
            fail(f"missing --source {source_key}=/path for partition {p['name']}")
        if not os.path.isfile(path):
            fail(f"source image not found: {path}")
        source_size = os.path.getsize(path)
        capacity = int(p["sectors"]) * sector_size
        if source_size > capacity:
            fail(f"{p['name']}: source is {source_size} bytes but partition is only {capacity}")
        if p.get("filesystem") == "ext4" and ext4_magic(path) != b"\x53\xef":
            fail(f"{p['name']}: source does not contain ext4 magic: {path}")
        used[p["number"]] = (path, source_size)
    return used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--source", action="append", default=[], help="key=/path/image; may repeat")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    layout_path = os.path.expanduser(args.layout)
    output = os.path.expanduser(args.output)
    manifest = os.path.expanduser(args.manifest) if args.manifest else output + ".manifest.json"
    cfg = load_layout(layout_path)
    computed, disk_sectors = calculate_layout(cfg)
    sources = parse_sources(args.source)
    used = validate_component_sources(computed, sources, cfg["sector_size"])

    if os.path.exists(output) and not args.force:
        fail(f"refusing to overwrite existing disk: {output} (use --force)")
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)

    disk_size = disk_sectors * cfg["sector_size"]
    print(f"==> Creating sparse disk: {output}")
    print(f"    logical size: {disk_size} bytes ({disk_size / (1024**3):.3f} GiB)")

    with open(output, "w+b", buffering=0) as dst:
        dst.truncate(disk_size)
        write_partition_tables(dst, computed, disk_sectors, cfg["sector_size"])

        for p in computed:
            if p["number"] not in used:
                continue
            path, source_size = used[p["number"]]
            dst_offset = int(p["start_lba"]) * cfg["sector_size"]
            print(
                f"==> p{p['number']} {p['name']}: {path} -> "
                f"LBA {p['start_lba']} ({source_size} bytes)"
            )
            sparse_copy(path, dst, dst_offset)

        dst.flush()
        os.fsync(dst.fileno())

    # Verify ext4 magic in the assembled image at the actual partition offsets.
    for p in computed:
        if p.get("filesystem") != "ext4":
            continue
        magic = ext4_magic(output, int(p["start_lba"]) * cfg["sector_size"])
        if magic != b"\x53\xef":
            fail(f"assembled p{p['number']} {p['name']} failed ext4 magic check")

    manifest_obj = {
        "schema": 1,
        "layout": os.path.abspath(layout_path),
        "disk": os.path.abspath(output),
        "disk_size_bytes": disk_size,
        "sector_size": cfg["sector_size"],
        "alignment_sectors": cfg["alignment_sectors"],
        "nbd_max_part": cfg["nbd_max_part"],
        "partitions": [],
    }
    for p in computed:
        item = {
            "number": p["number"],
            "name": p["name"],
            "kind": p["kind"],
            "type_id": p["type_id"],
            "start_lba": p["start_lba"],
            "sectors": p["sectors"],
            "size_bytes": p["sectors"] * cfg["sector_size"],
        }
        if "ebr_lba" in p:
            item["ebr_lba"] = p["ebr_lba"]
        if p["number"] in used:
            item["source_path"] = os.path.abspath(used[p["number"]][0])
            item["source_size_bytes"] = used[p["number"]][1]
        manifest_obj["partitions"].append(item)

    os.makedirs(os.path.dirname(os.path.abspath(manifest)), exist_ok=True)
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_obj, f, indent=2, sort_keys=True)
        f.write("\n")

    print("\nDISKLESS_V2_DISK_ASSEMBLED=1")
    print(f"disk={output}")
    print(f"manifest={manifest}")
    for p in computed:
        extra = f" ebr={p['ebr_lba']}" if "ebr_lba" in p else ""
        print(
            f"p{p['number']}={p['name']} start={p['start_lba']} "
            f"sectors={p['sectors']}{extra}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
