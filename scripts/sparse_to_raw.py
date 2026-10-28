#!/usr/bin/env python3
"""Convert an Android sparse image to a raw image without external tools."""

import argparse
import os
import struct
import sys

SPARSE_HEADER_MAGIC = 0xED26FF3A
CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32 = 0xCAC4


def read_exact(f, n):
    b = f.read(n)
    if len(b) != n:
        raise EOFError(f"unexpected EOF: wanted {n}, got {len(b)}")
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args()

    with open(args.input, "rb") as src:
        hdr = read_exact(src, 28)
        magic, major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, checksum = struct.unpack(
            "<I4H4I", hdr
        )
        if magic != SPARSE_HEADER_MAGIC:
            ap.error(f"not an Android sparse image (magic=0x{magic:08x})")
        if major != 1:
            ap.error(f"unsupported sparse major version {major}")
        if file_hdr_sz < 28 or chunk_hdr_sz < 12:
            ap.error("invalid sparse header sizes")
        if file_hdr_sz > 28:
            read_exact(src, file_hdr_sz - 28)

        expected_size = total_blks * blk_sz
        print(f"sparse: block={blk_sz} blocks={total_blks} chunks={total_chunks}")
        print(f"raw size: {expected_size} bytes")

        with open(args.output, "wb") as dst:
            out_blocks = 0
            zero = bytes(min(1024 * 1024, blk_sz * 256))

            for idx in range(total_chunks):
                ch = read_exact(src, chunk_hdr_sz)
                chunk_type, _reserved, chunk_sz, total_sz = struct.unpack("<2H2I", ch[:12])
                data_sz = total_sz - chunk_hdr_sz
                chunk_bytes = chunk_sz * blk_sz

                if chunk_type == CHUNK_TYPE_RAW:
                    if data_sz != chunk_bytes:
                        raise ValueError(f"chunk {idx}: RAW size mismatch")
                    remaining = chunk_bytes
                    while remaining:
                        n = min(1024 * 1024, remaining)
                        dst.write(read_exact(src, n))
                        remaining -= n

                elif chunk_type == CHUNK_TYPE_FILL:
                    if data_sz != 4:
                        raise ValueError(f"chunk {idx}: FILL payload size {data_sz}")
                    pattern = read_exact(src, 4)
                    unit = pattern * (len(zero) // 4)
                    remaining = chunk_bytes
                    while remaining:
                        n = min(len(unit), remaining)
                        dst.write(unit[:n])
                        remaining -= n

                elif chunk_type == CHUNK_TYPE_DONT_CARE:
                    if data_sz:
                        read_exact(src, data_sz)
                    # Seek creates a sparse host file while preserving raw logical size.
                    dst.seek(chunk_bytes, os.SEEK_CUR)

                elif chunk_type == CHUNK_TYPE_CRC32:
                    if data_sz != 4:
                        raise ValueError(f"chunk {idx}: CRC32 payload size {data_sz}")
                    read_exact(src, 4)

                else:
                    raise ValueError(f"chunk {idx}: unknown chunk type 0x{chunk_type:04x}")

                out_blocks += chunk_sz

            if out_blocks != total_blks:
                raise ValueError(f"block count mismatch: {out_blocks} != {total_blks}")
            dst.truncate(expected_size)

    print(f"wrote raw image: {args.output} ({os.path.getsize(args.output)} bytes)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
