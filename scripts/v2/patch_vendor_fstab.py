#!/usr/bin/env python3
import argparse
import hashlib
import shutil
from pathlib import Path


def make_padding(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative padding")
    if n == 0:
        return b""
    if n == 1:
        return b"\n"
    return b"#" + (b" " * (n - 2)) + b"\n"


def main():
    ap = argparse.ArgumentParser(description="Replace only /etc/fstab.flox file data inside a raw ext4 vendor image")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--stock-fstab", required=True, type=Path)
    ap.add_argument("--fstab", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    stock = args.stock_fstab.read_bytes()
    generated = args.fstab.read_bytes()
    if not generated.endswith(b"\n"):
        raise SystemExit("ERROR: generated fstab must end with newline")
    if b"msm_sdcc.1" in generated or b" f2fs " in generated:
        raise SystemExit("ERROR: generated fstab violates diskless contract")
    if len(generated) > len(stock):
        raise SystemExit(
            f"ERROR: generated fstab ({len(generated)} bytes) is larger than stock file ({len(stock)} bytes); "
            "in-place ext4 file-data replacement is not safe"
        )

    image = args.input.read_bytes()
    first = image.find(stock)
    if first < 0:
        raise SystemExit("ERROR: exact pinned stock fstab bytes not found in vendor raw image")
    second = image.find(stock, first + 1)
    if second >= 0:
        raise SystemExit("ERROR: pinned stock fstab occurs more than once in vendor raw image")

    replacement = generated + make_padding(len(stock) - len(generated))
    if len(replacement) != len(stock):
        raise SystemExit("ERROR: internal replacement length mismatch")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Copy first so sparse/source handling is delegated to the host filesystem,
    # then replace exactly the original fstab file-data byte range.
    shutil.copyfile(args.input, args.output)
    with args.output.open("r+b") as fp:
        fp.seek(first)
        fp.write(replacement)
        fp.flush()

    patched = args.output.read_bytes()
    if patched[:first] != image[:first] or patched[first + len(stock):] != image[first + len(stock):]:
        raise SystemExit("ERROR: vendor output changed outside the exact stock fstab byte range")
    if patched[first:first + len(generated)] != generated:
        raise SystemExit("ERROR: generated fstab was not written at the expected vendor offset")
    if stock in patched:
        raise SystemExit("ERROR: stock fstab still present after vendor replacement")

    print("DISKLESS_V2_VENDOR_FSTAB_PATCHED=1")
    print(f"input={args.input}")
    print(f"output={args.output}")
    print(f"fstab_offset={first}")
    print(f"stock_fstab_bytes={len(stock)}")
    print(f"generated_fstab_bytes={len(generated)}")
    print(f"input_sha256={hashlib.sha256(image).hexdigest()}")
    print(f"output_sha256={hashlib.sha256(patched).hexdigest()}")
    print("outside_fstab_region=unchanged")


if __name__ == "__main__":
    main()
