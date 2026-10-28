#!/usr/bin/env python3
import argparse
import mmap
from pathlib import Path

HEADER = b"# Android fstab file.\n"
END = b"/dev/block/zram0"

REMAP = {
    b"/dev/block/platform/msm_sdcc.1/by-name/system": b"/dev/block/nbd0",
    b"/dev/block/platform/msm_sdcc.1/by-name/vendor": b"/dev/block/nbd1",
    b"/dev/block/platform/msm_sdcc.1/by-name/cache": b"/dev/block/nbd2",
    b"/dev/block/platform/msm_sdcc.1/by-name/userdata": b"/dev/block/nbd3",
    b"/dev/block/platform/msm_sdcc.1/by-name/persist": b"/dev/block/nbd4",
}

EMMC_ONLY = {
    b"boot", b"recovery", b"misc", b"sbl1", b"sbl2", b"sbl3",
    b"tz", b"rpm", b"aboot", b"sbl2b", b"sbl3b", b"tzb", b"rpmb", b"abootb",
}

ENCRYPT_SUFFIX = b",encryptable=/dev/block/platform/msm_sdcc.1/by-name/metadata"


def pad_replace(blob: bytearray, old: bytes, new: bytes) -> int:
    if len(new) > len(old):
        raise RuntimeError(f"replacement longer than source: {new!r}")
    count = 0
    start = 0
    repl = new + b" " * (len(old) - len(new))
    while True:
        pos = blob.find(old, start)
        if pos < 0:
            break
        blob[pos:pos + len(old)] = repl
        count += 1
        start = pos + len(old)
    return count


def patch_region(region: bytes) -> bytes:
    out = bytearray(region)

    # Remove userdata metadata-encryption dependency while preserving byte length.
    enc_count = pad_replace(out, ENCRYPT_SUFFIX, b"")

    counts = {}
    for old, new in REMAP.items():
        counts[old] = pad_replace(out, old, new)

    # Comment out eMMC-only partition entries. Keep line length unchanged.
    lines = bytes(out).splitlines(keepends=True)
    patched_lines = []
    commented = 0
    for line in lines:
        if line.startswith(b"/dev/block/platform/msm_sdcc.1/by-name/"):
            tail = line[len(b"/dev/block/platform/msm_sdcc.1/by-name/"):]
            name = tail.split(None, 1)[0]
            if name in EMMC_ONLY:
                line = b"#" + line[1:]
                commented += 1
        patched_lines.append(line)
    out = bytearray(b"".join(patched_lines))

    required = {
        b"system": counts[b"/dev/block/platform/msm_sdcc.1/by-name/system"],
        b"vendor": counts[b"/dev/block/platform/msm_sdcc.1/by-name/vendor"],
        b"cache": counts[b"/dev/block/platform/msm_sdcc.1/by-name/cache"],
        b"userdata": counts[b"/dev/block/platform/msm_sdcc.1/by-name/userdata"],
        b"persist": counts[b"/dev/block/platform/msm_sdcc.1/by-name/persist"],
    }
    if required[b"system"] != 1 or required[b"vendor"] != 1 or required[b"persist"] != 1:
        raise RuntimeError(f"unexpected fstab counts: {required}")
    if required[b"cache"] != 2 or required[b"userdata"] != 2:
        raise RuntimeError(f"unexpected duplicate fstab counts: {required}")
    if enc_count != 2:
        raise RuntimeError(f"expected 2 encryptable metadata flags, found {enc_count}")
    if commented != len(EMMC_ONLY):
        raise RuntimeError(f"expected to comment {len(EMMC_ONLY)} eMMC-only entries, commented {commented}")
    if len(out) != len(region):
        raise RuntimeError("patch changed fstab byte length")
    return bytes(out)


def patch_image(path: Path) -> None:
    with path.open("r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
            starts = []
            pos = 0
            while True:
                pos = mm.find(HEADER, pos)
                if pos < 0:
                    break
                starts.append(pos)
                pos += len(HEADER)

            if not starts:
                print(f"{path}: no embedded fstab found; skipping")
                return

            patched = 0
            for start in starts:
                end_pos = mm.find(END, start, start + 16384)
                if end_pos < 0:
                    continue
                line_end = mm.find(b"\n", end_pos, start + 16384)
                if line_end < 0:
                    continue
                line_end += 1
                region = mm[start:line_end]
                if b"msm_sdcc.1/by-name/system" not in region:
                    continue
                new_region = patch_region(region)
                mm[start:line_end] = new_region
                patched += 1

            if patched == 0:
                if all(mm.find(x) >= 0 for x in (b"/dev/block/nbd0", b"/dev/block/nbd1", b"/dev/block/nbd2", b"/dev/block/nbd3", b"/dev/block/nbd4")):
                    print(f"{path}: already patched")
                    return
                raise SystemExit(f"{path}: found fstab header(s), but none matched expected flox layout")

            mm.flush()
            print(f"{path}: patched {patched} embedded fstab instance(s) in place")


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch embedded flox fstab text in raw ext4 image(s) for NBD diskless boot")
    ap.add_argument("images", nargs="+", help="raw ext4 images, e.g. system.raw.img vendor.raw.img")
    args = ap.parse_args()

    for name in args.images:
        patch_image(Path(name).expanduser())


if __name__ == "__main__":
    main()
