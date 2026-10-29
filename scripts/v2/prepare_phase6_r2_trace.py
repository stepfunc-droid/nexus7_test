#!/usr/bin/env python3
"""Build and validate the Phase6 R2/R3 host-side NBD trace map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ext4_readonly import Ext4Image, Ext4Error, S_IFREG

SECTOR = 512

MARKERS = [
    {
        "name": "pre_enforce_vendor_precompiled_sepolicy",
        "order": 1,
        "partition": "vendor",
        "stage": "policy-load-before-security_setenforce",
        "candidates": [
            "/etc/selinux/precompiled_sepolicy",
            "/vendor/etc/selinux/precompiled_sepolicy",
        ],
    },
    {
        "name": "post_enforce_second_stage_init_rc",
        "order": 2,
        "partition": "system",
        "stage": "second-stage-init-config-after-enforcing",
        "candidates": [
            "/system/etc/init/hw/init.rc",
            "/etc/init/hw/init.rc",
        ],
    },
    {
        "name": "post_enforce_flox_rc",
        "order": 3,
        "partition": "system",
        "stage": "second-stage-device-config-after-enforcing",
        "candidates": [
            "/init.flox.rc",
            "/system/init.flox.rc",
        ],
    },
]


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_dense_ranges(ranges: list[dict[str, int]], size: int, label: str) -> None:
    pos = 0
    for r in sorted(ranges, key=lambda x: x["file_offset"]):
        if r["file_offset"] != pos:
            die(f"{label} has sparse/non-dense extent coverage at file offset {pos}")
        if r["length"] <= 0:
            die(f"{label} has zero-length extent")
        pos += r["length"]
    if pos != size:
        die(f"{label} extent coverage={pos} file_size={size}")


def verify_disk_mapping(disk: Path, source: Path, ranges: list[dict[str, int]],
                        partition_start: int, file_bytes: bytes, label: str) -> None:
    rebuilt = bytearray(len(file_bytes))
    with disk.open("rb") as df, source.open("rb") as sf:
        for r in ranges:
            image_off = int(r["image_offset"])
            file_off = int(r["file_offset"])
            length = int(r["length"])
            disk_off = partition_start + image_off

            sf.seek(image_off)
            source_bytes = sf.read(length)
            if len(source_bytes) != length:
                die(f"{label}: short source range read")
            df.seek(disk_off)
            disk_bytes = df.read(length)
            if len(disk_bytes) != length:
                die(f"{label}: short assembled-disk range read")
            if disk_bytes != source_bytes:
                die(f"{label}: assembled disk differs from source at disk offset {disk_off}")
            rebuilt[file_off:file_off + length] = disk_bytes

    if bytes(rebuilt) != file_bytes:
        die(f"{label}: reconstructed file bytes from assembled disk do not match ext4 file")


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare Phase6 R2/R3 file-range trace map")
    ap.add_argument("--disk", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--system", required=True, type=Path)
    ap.add_argument("--vendor", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    for path in (args.disk, args.manifest, args.system, args.vendor):
        if not path.is_file():
            die(f"required input not found: {path}")

    manifest = json.loads(args.manifest.read_text())
    if int(manifest.get("sector_size", 0)) != SECTOR:
        die("trace builder requires 512-byte disk sectors")
    parts = {p["name"]: p for p in manifest["partitions"]}
    for name in ("system", "vendor"):
        if name not in parts:
            die(f"disk manifest missing {name} partition")

    images = {"system": args.system, "vendor": args.vendor}
    fs = {}
    try:
        for name, image in images.items():
            fs[name] = Ext4Image(image)

        output_markers = []
        for spec in MARKERS:
            part_name = spec["partition"]
            filesystem = fs[part_name]
            try:
                resolved_path, inode = filesystem.first_existing(spec["candidates"])
            except Ext4Error as exc:
                die(f"{spec['name']}: {exc}")
            if inode.kind != S_IFREG:
                die(f"{spec['name']}: resolved path is not a regular file: {resolved_path}")

            file_bytes = filesystem.read_inode(inode)
            ranges = filesystem.file_ranges(inode)
            if not file_bytes:
                die(f"{spec['name']}: marker file is empty")
            assert_dense_ranges(ranges, len(file_bytes), spec["name"])

            part = parts[part_name]
            partition_start = int(part["start_lba"]) * SECTOR
            verify_disk_mapping(
                args.disk, images[part_name], ranges, partition_start,
                file_bytes, spec["name"],
            )

            disk_ranges = []
            for r in ranges:
                disk_ranges.append({
                    "file_offset": int(r["file_offset"]),
                    "disk_offset": partition_start + int(r["image_offset"]),
                    "length": int(r["length"]),
                })

            output_markers.append({
                "name": spec["name"],
                "order": spec["order"],
                "stage": spec["stage"],
                "partition": part_name,
                "resolved_path": resolved_path,
                "inode": inode.number,
                "file_size": len(file_bytes),
                "file_sha256": sha256(file_bytes),
                "required_coverage": len(file_bytes),
                "ranges": disk_ranges,
            })

        trace = {
            "schema": 1,
            "disk": str(args.disk.resolve()),
            "disk_size": args.disk.stat().st_size,
            "manifest": str(args.manifest.resolve()),
            "markers": output_markers,
            "acceptance": {
                "same_connection": True,
                "ordered_complete_markers": [m["name"] for m in output_markers],
                "meaning": (
                    "policy file read occurs before security_setenforce; init.rc and init.flox.rc "
                    "are second-stage reads after enforcing"
                ),
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n")

        print("DISKLESS_V2_PHASE6_R2_TRACE_MAP=PASS")
        print(f"trace_map={args.output}")
        for marker in output_markers:
            print(
                f"marker={marker['order']}:{marker['name']} "
                f"partition={marker['partition']} path={marker['resolved_path']} "
                f"inode={marker['inode']} size={marker['file_size']} "
                f"sha256={marker['file_sha256']} extents={len(marker['ranges'])}"
            )
        print("assembled_disk_mapping=byte-verified")
        print("nexus_boot_required=no")
    finally:
        for image in fs.values():
            image.close()


if __name__ == "__main__":
    main()
