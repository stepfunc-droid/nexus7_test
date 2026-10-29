#!/usr/bin/env python3
"""Reverse-map a combined-disk NBD READ into the accepted p1/system ext4 image.

Host-only forensic helper for Phase6 Audit V2.  It never writes the filesystem.
It resolves the realized partition geometry from the assembled-disk manifest,
verifies the p1 source is the accepted system image, then walks the ext4 tree and
reports file/directory extents overlapping the requested byte range.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ext4_readonly import Ext4Error, Ext4Image, S_IFDIR, S_IFLNK, S_IFREG, u16, u32

EXPECTED_SYSTEM_SHA256 = "a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880"
SECTOR = 512


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)


def iter_dir_entries(fs: Ext4Image, inode):
    data = fs.read_inode(inode)
    off = 0
    while off + 8 <= len(data):
        ino = u32(data, off)
        rec_len = u16(data, off + 4)
        name_len = data[off + 6]
        if rec_len < 8 or off + rec_len > len(data):
            raise Ext4Error(f"bad directory record in inode {inode.number} at offset {off}")
        if ino and 8 + name_len <= rec_len:
            raw_name = data[off + 8:off + 8 + name_len]
            name = raw_name.decode("utf-8", "surrogateescape")
            if name not in (".", ".."):
                yield name, ino
        off += rec_len


def inode_kind_name(kind: int) -> str:
    if kind == S_IFREG:
        return "file"
    if kind == S_IFDIR:
        return "dir"
    if kind == S_IFLNK:
        return "symlink"
    return f"kind-0x{kind:x}"


def collect_overlaps(fs: Ext4Image, target_start: int, target_end: int):
    matches = []
    seen_dirs = set()
    seen_paths = set()
    stack = [("/", fs.inode(2))]

    while stack:
        path, inode = stack.pop()
        key = (path, inode.number)
        if key in seen_paths:
            continue
        seen_paths.add(key)

        try:
            extents = fs.extents(inode)
        except Ext4Error:
            extents = []

        for ex in extents:
            if ex.unwritten:
                continue
            phys_start = ex.physical_block * fs.block_size
            phys_end = phys_start + ex.blocks * fs.block_size
            if not overlaps(target_start, target_end, phys_start, phys_end):
                continue
            ov0 = max(target_start, phys_start)
            ov1 = min(target_end, phys_end)
            logical_start = ex.logical_block * fs.block_size + (ov0 - phys_start)
            matches.append({
                "path": path,
                "inode": inode.number,
                "kind": inode_kind_name(inode.kind),
                "inode_size": inode.size,
                "extent_logical_block": ex.logical_block,
                "extent_physical_block": ex.physical_block,
                "extent_blocks": ex.blocks,
                "overlap_image_start": ov0,
                "overlap_image_end": ov1,
                "overlap_length": ov1 - ov0,
                "file_offset_start": logical_start,
                "file_offset_end": logical_start + (ov1 - ov0),
            })

        if inode.kind == S_IFDIR and inode.number not in seen_dirs:
            seen_dirs.add(inode.number)
            try:
                children = list(iter_dir_entries(fs, inode))
            except Ext4Error:
                children = []
            for name, ino in reversed(children):
                child_path = (path.rstrip("/") + "/" + name) if path != "/" else "/" + name
                try:
                    child = fs.inode(ino)
                except Ext4Error:
                    continue
                stack.append((child_path, child))

    matches.sort(key=lambda m: (m["overlap_image_start"], m["path"], m["inode"]))
    return matches


def primary_group_metadata(fs: Ext4Image, target_start: int, target_end: int):
    """Report overlap with primary per-group block/inode bitmaps or inode tables."""
    matches = []
    target_block0 = target_start // fs.block_size
    target_block1 = (target_end + fs.block_size - 1) // fs.block_size
    first_group = target_block0 // fs.blocks_per_group
    last_group = max(first_group, (max(target_block1 - 1, target_block0)) // fs.blocks_per_group)
    inode_table_blocks = (fs.inodes_per_group * fs.inode_size + fs.block_size - 1) // fs.block_size

    for group in range(first_group, last_group + 1):
        gd = fs.pread(fs.desc_size, fs.gdt_offset + group * fs.desc_size)
        block_bitmap = u32(gd, 0x00) | ((u32(gd, 0x20) << 32) if fs.desc_size >= 64 else 0)
        inode_bitmap = u32(gd, 0x04) | ((u32(gd, 0x24) << 32) if fs.desc_size >= 64 else 0)
        inode_table = u32(gd, 0x08) | ((u32(gd, 0x28) << 32) if fs.desc_size >= 64 else 0)
        regions = [
            ("block_bitmap", block_bitmap, 1),
            ("inode_bitmap", inode_bitmap, 1),
            ("inode_table", inode_table, inode_table_blocks),
        ]
        for name, block, blocks in regions:
            start = block * fs.block_size
            end = start + blocks * fs.block_size
            if overlaps(target_start, target_end, start, end):
                matches.append({
                    "group": group,
                    "region": name,
                    "image_start": start,
                    "image_end": end,
                    "overlap_start": max(target_start, start),
                    "overlap_end": min(target_end, end),
                })
    return matches


def main() -> None:
    ap = argparse.ArgumentParser(description="Reverse-map one Phase6 V2 NBD read into p1/system")
    ap.add_argument("--manifest", type=Path,
                    default=Path.home() / "nexus7-diskless-v2/diskless-v2-android.raw.img.manifest.json")
    ap.add_argument("--disk-offset", required=True, type=lambda s: int(s, 0))
    ap.add_argument("--length", required=True, type=lambda s: int(s, 0))
    args = ap.parse_args()

    if args.length <= 0:
        die("length must be positive")
    if not args.manifest.is_file():
        die(f"manifest not found: {args.manifest}")

    manifest = json.loads(args.manifest.read_text())
    if int(manifest.get("sector_size", 0)) != SECTOR:
        die("manifest sector size is not 512")
    p1s = [p for p in manifest.get("partitions", []) if int(p.get("number", -1)) == 1]
    if len(p1s) != 1:
        die(f"expected exactly one p1 entry, got {len(p1s)}")
    p1 = p1s[0]
    if p1.get("name") != "system":
        die(f"p1 is not system: {p1.get('name')}")

    p1_start = int(p1["start_lba"]) * SECTOR
    p1_end = p1_start + int(p1["sectors"]) * SECTOR
    disk_start = args.disk_offset
    disk_end = disk_start + args.length
    if not (p1_start <= disk_start < disk_end <= p1_end):
        die(
            f"requested disk range {disk_start}:{disk_end} is not wholly inside "
            f"p1/system {p1_start}:{p1_end}"
        )

    source_path = p1.get("source_path")
    if not source_path:
        die("manifest p1 lacks source_path; cannot bind reverse mapping to accepted source")
    system = Path(source_path)
    if not system.is_file():
        die(f"system source image not found: {system}")
    digest = sha256_file(system)
    if digest != EXPECTED_SYSTEM_SHA256:
        die(f"system sha256={digest} expected accepted={EXPECTED_SYSTEM_SHA256}")

    image_start = disk_start - p1_start
    image_end = disk_end - p1_start

    with Ext4Image(system) as fs:
        if image_start % fs.block_size or args.length % fs.block_size:
            alignment = "not-block-aligned"
        else:
            alignment = "block-aligned"
        file_matches = collect_overlaps(fs, image_start, image_end)
        metadata_matches = primary_group_metadata(fs, image_start, image_end)

        print("DISKLESS_V2_PHASE6_V2_SYSTEM_READ_REVERSE_MAP=PASS")
        print(f"manifest={args.manifest}")
        print(f"system_image={system}")
        print(f"system_sha256={digest}")
        print(f"disk_range={disk_start}:{disk_end}")
        print(f"p1_disk_start={p1_start}")
        print(f"p1_relative_range={image_start}:{image_end}")
        print(f"p1_relative_hex=0x{image_start:x}:0x{image_end:x}")
        print(f"ext4_block_size={fs.block_size}")
        print(f"alignment={alignment}")
        print(f"file_extent_matches={len(file_matches)}")
        for i, m in enumerate(file_matches, 1):
            print(
                "FILE_MATCH "
                f"index={i} path={m['path']!r} inode={m['inode']} kind={m['kind']} "
                f"inode_size={m['inode_size']} overlap={m['overlap_image_start']}:{m['overlap_image_end']} "
                f"file_offset={m['file_offset_start']}:{m['file_offset_end']} "
                f"extent_pblk={m['extent_physical_block']} extent_blocks={m['extent_blocks']}"
            )
        print(f"primary_metadata_matches={len(metadata_matches)}")
        for i, m in enumerate(metadata_matches, 1):
            print(
                "METADATA_MATCH "
                f"index={i} group={m['group']} region={m['region']} "
                f"image_range={m['image_start']}:{m['image_end']} "
                f"overlap={m['overlap_start']}:{m['overlap_end']}"
            )
        if not file_matches and not metadata_matches:
            print("classification=no-directory-reachable-file-extent-or-primary-group-metadata-match")
        elif file_matches:
            print("classification=directory-reachable-file-or-directory-extent-overlap")
        else:
            print("classification=primary-ext4-group-metadata-overlap")


if __name__ == "__main__":
    main()
