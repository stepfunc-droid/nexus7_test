#!/usr/bin/env python3
"""Build a minimal Qualcomm QCDT v1 image containing exactly one DTB.

The msm8960/flo lk2nd target understands the legacy Qualcomm device-tree table
used by old Android boot images.  For Nexus 7 (flo) we only need one entry:
APQ8064 (platform id 109), MTP hardware id 8, generic soc revision 0.
"""

import argparse
import struct
from pathlib import Path

QCDT_MAGIC = 0x54444351  # bytes: b"QCDT" on little-endian ARM
QCDT_VERSION = 1
HEADER_SIZE = 12
ENTRY_V1_SIZE = 20


def parse_int(value: str) -> int:
    return int(value, 0)


def align_up(value: int, align: int) -> int:
    return (value + align - 1) & ~(align - 1)


def main() -> None:
    p = argparse.ArgumentParser(description="Create a single-entry Qualcomm QCDT v1 image")
    p.add_argument("--dtb", required=True)
    p.add_argument("--platform-id", type=parse_int, required=True)
    p.add_argument("--variant-id", type=parse_int, required=True)
    p.add_argument("--soc-rev", type=parse_int, default=0)
    p.add_argument("--pagesize", type=parse_int, default=2048)
    p.add_argument("--output", "-o", required=True)
    args = p.parse_args()

    if args.pagesize <= 0 or args.pagesize & (args.pagesize - 1):
        raise SystemExit("pagesize must be a positive power of two")

    dtb = Path(args.dtb).read_bytes()
    if len(dtb) < 4 or dtb[:4] != b"\xd0\x0d\xfe\xed":
        raise SystemExit("input is not a flattened device tree (bad FDT magic)")

    dtb_offset = align_up(HEADER_SIZE + ENTRY_V1_SIZE, args.pagesize)

    with open(args.output, "wb") as out:
        out.write(struct.pack("<III", QCDT_MAGIC, QCDT_VERSION, 1))
        out.write(struct.pack(
            "<IIIII",
            args.platform_id,
            args.variant_id,
            args.soc_rev,
            dtb_offset,
            len(dtb),
        ))
        out.write(b"\x00" * (dtb_offset - out.tell()))
        out.write(dtb)

    print(f"created {args.output} ({Path(args.output).stat().st_size} bytes)")
    print(
        "entry: "
        f"platform_id={args.platform_id} "
        f"variant_id={args.variant_id} "
        f"soc_rev=0x{args.soc_rev:x} "
        f"dtb_offset=0x{dtb_offset:x} "
        f"dtb_size={len(dtb)}"
    )


if __name__ == "__main__":
    main()
