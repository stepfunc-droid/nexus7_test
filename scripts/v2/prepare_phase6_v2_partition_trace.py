#!/usr/bin/env python3
"""Build the Audit-V2 host trace map for post-first-stage partitions.

The map intentionally does not use p1/p2 file extents.  It records the exact
combined-disk ranges for cache/persist/userdata plus ext4 primary-superblock and
primary group-descriptor windows.  Those partitions are excluded from Android
first-stage by the accepted fstab/source contract.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import assemble_disk as diskbuild

SECTOR = 512
EXT4_SUPER_OFFSET = 1024
EXT4_SUPER_SIZE = 1024
EXT4_MAGIC_OFFSET = 56
EXT4_MAGIC = 0xEF53
EXT4_LOG_BLOCK_SIZE_OFFSET = 24

TARGETS = {
    "cache": {"number": 3, "stage": "second-stage-fs-early", "late": False},
    "persist": {"number": 6, "stage": "second-stage-fs-early", "late": False},
    "userdata": {"number": 5, "stage": "second-stage-late-fs", "late": True},
}


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return max(a0, b0) < min(a1, b1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare Phase6 V2 partition-stage NBD trace map")
    ap.add_argument("--disk", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--layout", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    for path in (args.disk, args.manifest, args.layout):
        if not path.is_file():
            die(f"required input missing: {path}")

    manifest = json.loads(args.manifest.read_text())
    layout = diskbuild.load_layout(str(args.layout))
    computed, disk_sectors = diskbuild.calculate_layout(layout)

    if int(manifest.get("sector_size", 0)) != SECTOR:
        die("disk manifest sector size is not 512")
    if int(layout.get("sector_size", 0)) != SECTOR:
        die("layout sector size is not 512")
    if args.disk.stat().st_size != disk_sectors * SECTOR:
        die(
            f"disk size={args.disk.stat().st_size} differs from layout-calculated "
            f"size={disk_sectors * SECTOR}"
        )
    if int(manifest.get("disk_size_bytes", -1)) != args.disk.stat().st_size:
        die("manifest disk_size_bytes differs from actual disk")

    manifest_parts = {p["name"]: p for p in manifest.get("partitions", [])}
    layout_parts = {p["name"]: p for p in layout.get("partitions", []) if "name" in p}
    computed_parts = {p["name"]: p for p in computed if "name" in p}

    entries = []
    with args.disk.open("rb") as fp:
        for name, spec in TARGETS.items():
            if name not in manifest_parts or name not in layout_parts or name not in computed_parts:
                die(f"missing target partition in manifest/layout/calculated geometry: {name}")
            mp = manifest_parts[name]
            lp = layout_parts[name]
            cp = computed_parts[name]

            number = int(mp["number"])
            if number != spec["number"] or int(lp["number"]) != number or int(cp["number"]) != number:
                die(f"{name}: partition number mismatch")
            # assemble_disk.py's manifest records realized geometry only;
            # filesystem semantics belong to layout.json.
            if lp.get("filesystem") != "ext4":
                die(f"{name}: layout filesystem={lp.get('filesystem')} expected=ext4")

            start_lba = int(mp["start_lba"])
            sectors = int(mp["sectors"])
            if start_lba != int(cp["start_lba"]):
                die(f"{name}: manifest start_lba differs from accepted layout calculator")
            if sectors != int(cp["sectors"]):
                die(f"{name}: manifest sectors differ from accepted layout calculator")
            layout_sectors = int(lp["size_bytes"]) // SECTOR
            if sectors != layout_sectors:
                die(f"{name}: sector count differs from layout size_bytes")
            if int(mp.get("size_bytes", sectors * SECTOR)) != sectors * SECTOR:
                die(f"{name}: manifest size_bytes disagrees with sectors")

            start = start_lba * SECTOR
            size = sectors * SECTOR
            end = start + size
            if end > args.disk.stat().st_size:
                die(f"{name}: partition extends beyond disk")

            fp.seek(start + EXT4_SUPER_OFFSET)
            superblock = fp.read(EXT4_SUPER_SIZE)
            if len(superblock) != EXT4_SUPER_SIZE:
                die(f"{name}: short ext4 superblock read")
            magic = struct.unpack_from("<H", superblock, EXT4_MAGIC_OFFSET)[0]
            if magic != EXT4_MAGIC:
                die(f"{name}: ext4 magic=0x{magic:04x} expected=0x{EXT4_MAGIC:04x}")
            log_block_size = struct.unpack_from("<I", superblock, EXT4_LOG_BLOCK_SIZE_OFFSET)[0]
            block_size = 1024 << log_block_size
            if block_size not in (1024, 2048, 4096):
                die(f"{name}: unsupported ext4 block size {block_size}")

            # ext4 primary GDT starts at block 2 for 1 KiB filesystems and at
            # block 1 for larger block sizes.
            gdt_rel = 2 * block_size if block_size == 1024 else block_size
            super_range = [start + EXT4_SUPER_OFFSET, start + EXT4_SUPER_OFFSET + EXT4_SUPER_SIZE]
            gdt_range = [start + gdt_rel, start + gdt_rel + block_size]
            if not (start <= super_range[0] < super_range[1] <= end):
                die(f"{name}: superblock evidence window outside partition")
            if not (start <= gdt_range[0] < gdt_range[1] <= end):
                die(f"{name}: GDT evidence window outside partition")
            if overlap(super_range[0], super_range[1], gdt_range[0], gdt_range[1]):
                die(f"{name}: superblock and GDT evidence windows unexpectedly overlap")

            entries.append({
                "name": name,
                "number": number,
                "stage": spec["stage"],
                "late_mount": spec["late"],
                "start_lba": start_lba,
                "sectors": sectors,
                "disk_start": start,
                "disk_end": end,
                "filesystem": "ext4",
                "block_size": block_size,
                "evidence": {
                    "superblock": {"start": super_range[0], "end": super_range[1]},
                    "primary_gdt": {"start": gdt_range[0], "end": gdt_range[1]},
                },
            })

    result = {
        "schema": 2,
        "disk": str(args.disk.resolve()),
        "disk_size": args.disk.stat().st_size,
        "sector_size": SECTOR,
        "partitions": entries,
        "semantics": {
            "first_stage_excluded": ["cache", "persist", "userdata"],
            "second_stage_early_candidates": ["cache", "persist"],
            "late_fs_candidate": "userdata",
            "acceptance_note": (
                "stage inference requires successful NBD READ replies overlapping both ext4 "
                "superblock and primary-GDT evidence windows on the same connection; mere MBR/EBR "
                "or partition-range overlap is insufficient"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    print("DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_MAP=PASS")
    print(f"trace_map={args.output}")
    for entry in entries:
        print(
            f"partition={entry['name']} p{entry['number']} stage={entry['stage']} "
            f"start={entry['disk_start']} end={entry['disk_end']} block_size={entry['block_size']} "
            f"super={entry['evidence']['superblock']['start']}:{entry['evidence']['superblock']['end']} "
            f"gdt={entry['evidence']['primary_gdt']['start']}:{entry['evidence']['primary_gdt']['end']}"
        )
    print("geometry_source=accepted-assemble_disk.calculate_layout")
    print("partition_table_traffic_is_not_stage_evidence=PASS")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
