#!/usr/bin/env python3
import argparse
import hashlib
import lzma
import struct
import zlib
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
NEWC_MAGICS = {b"070701", b"070702"}
HEADER_SIZE = 8 + 10 * 4 + 16 + 512 + 32 + 1024


def align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def parse_boot(path: Path):
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or data[:8] != BOOT_MAGIC:
        raise SystemExit(f"ERROR: invalid legacy boot image: {path}")
    fields = list(struct.unpack_from("<10I", data, 8))
    ksz, kaddr, rsz, raddr, ssz, saddr, taddr, page, dsz, unused = fields
    if page <= 0 or page & (page - 1):
        raise SystemExit("ERROR: invalid boot page size")
    off = 48
    board = data[off:off + 16]; off += 16
    cmdline = data[off:off + 512]; off += 512
    image_id = data[off:off + 32]; off += 32
    extra = data[off:off + 1024]
    cursor = page
    k0, k1 = cursor, cursor + ksz
    cursor = align_up(k1, page)
    r0, r1 = cursor, cursor + rsz
    cursor = align_up(r1, page)
    s0, s1 = cursor, cursor + ssz
    cursor = align_up(s1, page)
    d0, d1 = cursor, cursor + dsz
    if max(k1, r1, s1, d1) > len(data):
        raise SystemExit("ERROR: truncated boot image")
    return {
        "fields": fields,
        "board": board,
        "cmdline": cmdline,
        "extra": extra,
        "kernel": data[k0:k1],
        "ramdisk": data[r0:r1],
        "second": data[s0:s1],
        "dt": data[d0:d1],
    }


def decompress_ramdisk(blob: bytes) -> bytes:
    if blob.startswith(b"\x1f\x8b"):
        return zlib.decompress(blob, 16 + zlib.MAX_WBITS)
    if blob.startswith(b"\xfd7zXZ\x00"):
        return lzma.decompress(blob)
    if any(blob.startswith(m) for m in NEWC_MAGICS):
        return blob
    raise SystemExit("ERROR: unsupported ramdisk format")


def parse_newc_payloads(data: bytes):
    entries = []
    off = 0
    while True:
        if off + 110 > len(data):
            raise SystemExit("ERROR: truncated newc archive")
        magic = data[off:off + 6]
        if magic not in NEWC_MAGICS:
            raise SystemExit(f"ERROR: bad newc magic at {off}")
        vals = [int(data[off + 6 + i:off + 14 + i], 16) for i in range(0, 104, 8)]
        filesize = vals[6]
        namesize = vals[11]
        n0 = off + 110
        n1 = n0 + namesize
        name_raw = data[n0:n1]
        if not name_raw.endswith(b"\x00"):
            raise SystemExit("ERROR: malformed newc filename")
        name = name_raw[:-1].decode("utf-8", "surrogateescape")
        d0 = align_up(n1, 4)
        d1 = d0 + filesize
        payload = data[d0:d1]
        entries.append((name, tuple(vals[:6] + vals[7:12]), payload))
        off = align_up(d1, 4)
        if name == "TRAILER!!!":
            break
    return entries


def normalized(name: str) -> str:
    return name[2:] if name.startswith("./") else name


def validate_boot(stock_path: Path, patched_path: Path, generated: bytes):
    stock = parse_boot(stock_path)
    patched = parse_boot(patched_path)

    # Header geometry and all non-ramdisk boot payloads must remain identical.
    sf, pf = stock["fields"], patched["fields"]
    for idx, label in ((0, "kernel_size"), (1, "kernel_addr"), (3, "ramdisk_addr"),
                       (4, "second_size"), (5, "second_addr"), (6, "tags_addr"),
                       (7, "page_size"), (8, "dt_size"), (9, "unused")):
        if sf[idx] != pf[idx]:
            raise SystemExit(f"ERROR: boot header field changed unexpectedly: {label}")
    for key in ("board", "cmdline", "extra", "kernel", "second", "dt"):
        if stock[key] != patched[key]:
            raise SystemExit(f"ERROR: boot component/header changed unexpectedly: {key}")

    before = parse_newc_payloads(decompress_ramdisk(stock["ramdisk"]))
    after = parse_newc_payloads(decompress_ramdisk(patched["ramdisk"]))
    if [e[0] for e in before] != [e[0] for e in after]:
        raise SystemExit("ERROR: boot ramdisk entry order/names changed")

    fstab_count = 0
    init_checked = False
    for b, a in zip(before, after):
        if b[1] != a[1]:
            raise SystemExit(f"ERROR: cpio metadata changed for {b[0]}")
        name = normalized(b[0])
        if name == "fstab.flox":
            fstab_count += 1
            if a[2] != generated:
                raise SystemExit("ERROR: boot ramdisk fstab does not equal generated fstab")
        else:
            if b[2] != a[2]:
                raise SystemExit(f"ERROR: non-fstab ramdisk payload changed: {b[0]}")
        if name == "init":
            init_checked = True
            if b[2] != a[2]:
                raise SystemExit("ERROR: /init changed during Phase 5B")
    if fstab_count != 1:
        raise SystemExit(f"ERROR: expected one boot fstab, found {fstab_count}")
    if not init_checked:
        raise SystemExit("ERROR: /init not found in boot ramdisk")


def validate_vendor(stock_img: Path, patched_img: Path, stock_fstab: bytes, generated: bytes):
    before = stock_img.read_bytes()
    after = patched_img.read_bytes()
    if len(before) != len(after):
        raise SystemExit("ERROR: vendor image length changed")
    off = before.find(stock_fstab)
    if off < 0 or before.find(stock_fstab, off + 1) >= 0:
        raise SystemExit("ERROR: stock vendor image does not contain exactly one pinned fstab")
    if before[:off] != after[:off] or before[off + len(stock_fstab):] != after[off + len(stock_fstab):]:
        raise SystemExit("ERROR: vendor image changed outside pinned fstab file-data region")
    region = after[off:off + len(stock_fstab)]
    if not region.startswith(generated):
        raise SystemExit("ERROR: vendor fstab region does not start with generated fstab")
    padding = region[len(generated):]
    if padding and not (padding == b"\n" or (padding.startswith(b"#") and padding.endswith(b"\n") and set(padding[1:-1]) <= {0x20})):
        raise SystemExit("ERROR: vendor fstab padding is not inert comment/whitespace")
    if b"msm_sdcc.1" in region or b" f2fs " in region:
        raise SystemExit("ERROR: vendor fstab region still contains forbidden diskless entries")


def main():
    ap = argparse.ArgumentParser(description="Independent validator for Phase 5B fstab-only artifacts")
    ap.add_argument("--stock-boot", required=True, type=Path)
    ap.add_argument("--patched-boot", required=True, type=Path)
    ap.add_argument("--stock-vendor", required=True, type=Path)
    ap.add_argument("--patched-vendor", required=True, type=Path)
    ap.add_argument("--stock-fstab", required=True, type=Path)
    ap.add_argument("--generated-fstab", required=True, type=Path)
    args = ap.parse_args()

    generated = args.generated_fstab.read_bytes()
    stock_fstab = args.stock_fstab.read_bytes()
    validate_boot(args.stock_boot, args.patched_boot, generated)
    validate_vendor(args.stock_vendor, args.patched_vendor, stock_fstab, generated)

    print("DISKLESS_V2_ANDROID_FSTAB_ARTIFACTS_VERIFIED=1")
    print(f"generated_fstab_sha256={hashlib.sha256(generated).hexdigest()}")
    print(f"patched_boot_sha256={hashlib.sha256(args.patched_boot.read_bytes()).hexdigest()}")
    print(f"patched_vendor_sha256={hashlib.sha256(args.patched_vendor.read_bytes()).hexdigest()}")
    print("boot_init=unchanged")
    print("boot_non_fstab_entries=unchanged")
    print("vendor_outside_fstab_region=unchanged")
    print("v1_rc_bypasses=absent-by-construction")


if __name__ == "__main__":
    main()
