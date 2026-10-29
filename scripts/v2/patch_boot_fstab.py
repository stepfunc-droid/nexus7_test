#!/usr/bin/env python3
import argparse
import hashlib
import struct
import zlib
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
NEWC_MAGICS = {b"070701", b"070702"}
HEADER_SIZE = 8 + 10 * 4 + 16 + 512 + 32 + 1024


def align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def gzip_deterministic(data: bytes) -> bytes:
    header = b"\x1f\x8b\x08\x00" + struct.pack("<I", 0) + b"\x02\xff"
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = co.compress(data) + co.flush()
    trailer = struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF)
    return header + body + trailer


def gunzip(data: bytes) -> bytes:
    return zlib.decompress(data, 16 + zlib.MAX_WBITS)


def parse_boot(path: Path):
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or data[:8] != BOOT_MAGIC:
        raise SystemExit(f"ERROR: not a legacy Android boot image: {path}")

    fields = list(struct.unpack_from("<10I", data, 8))
    (
        kernel_size, kernel_addr,
        ramdisk_size, ramdisk_addr,
        second_size, second_addr,
        tags_addr, page_size,
        dt_size, unused,
    ) = fields
    if page_size <= 0 or page_size & (page_size - 1):
        raise SystemExit(f"ERROR: invalid boot page size: {page_size}")

    off = 8 + 40
    board = data[off:off + 16]; off += 16
    cmdline = data[off:off + 512]; off += 512
    old_id = data[off:off + 32]; off += 32
    extra = data[off:off + 1024]

    cursor = page_size
    k0, k1 = cursor, cursor + kernel_size
    cursor = align_up(k1, page_size)
    r0, r1 = cursor, cursor + ramdisk_size
    cursor = align_up(r1, page_size)
    s0, s1 = cursor, cursor + second_size
    cursor = align_up(s1, page_size)
    d0, d1 = cursor, cursor + dt_size
    if max(k1, r1, s1, d1) > len(data):
        raise SystemExit("ERROR: boot image is truncated")

    return {
        "fields": fields,
        "board": board,
        "cmdline": cmdline,
        "extra": extra,
        "kernel": data[k0:k1],
        "ramdisk": data[r0:r1],
        "second": data[s0:s1],
        "dt": data[d0:d1],
        "page_size": page_size,
    }


def decompress_ramdisk(blob: bytes) -> bytes:
    if blob.startswith(b"\x1f\x8b"):
        return gunzip(blob)
    if blob.startswith(b"\xfd7zXZ\x00"):
        import lzma
        return lzma.decompress(blob)
    if blob.startswith(tuple(NEWC_MAGICS)):
        return blob
    raise SystemExit("ERROR: unsupported ramdisk compression; expected gzip, xz, or raw newc")


def parse_newc(data: bytes):
    entries = []
    off = 0
    while True:
        if off + 110 > len(data):
            raise SystemExit("ERROR: truncated newc archive")
        magic = data[off:off + 6]
        if magic not in NEWC_MAGICS:
            raise SystemExit(f"ERROR: invalid newc magic at offset {off}: {magic!r}")
        raw_fields = data[off + 6:off + 110]
        try:
            vals = [int(raw_fields[i:i + 8], 16) for i in range(0, 104, 8)]
        except ValueError as exc:
            raise SystemExit(f"ERROR: invalid newc header at offset {off}") from exc
        namesize = vals[11]
        filesize = vals[6]
        n0 = off + 110
        n1 = n0 + namesize
        if namesize <= 0 or n1 > len(data):
            raise SystemExit("ERROR: invalid newc name size")
        name_blob = data[n0:n1]
        if not name_blob.endswith(b"\x00"):
            raise SystemExit("ERROR: newc filename is not NUL terminated")
        name = name_blob[:-1].decode("utf-8", "surrogateescape")
        d0 = align_up(n1, 4)
        d1 = d0 + filesize
        if d1 > len(data):
            raise SystemExit(f"ERROR: truncated newc payload for {name}")
        payload = data[d0:d1]
        entries.append((magic, vals, name, payload))
        off = align_up(d1, 4)
        if name == "TRAILER!!!":
            break
    return entries


def build_newc(entries) -> bytes:
    out = bytearray()
    for magic, original_vals, name, payload in entries:
        vals = list(original_vals)
        name_bytes = name.encode("utf-8", "surrogateescape") + b"\x00"
        vals[6] = len(payload)
        vals[11] = len(name_bytes)
        vals[12] = (sum(payload) & 0xFFFFFFFF) if magic == b"070702" else 0
        out += magic
        out += b"".join(f"{v:08x}".encode("ascii") for v in vals)
        out += name_bytes
        out += b"\x00" * ((-len(out)) % 4)
        out += payload
        out += b"\x00" * ((-len(out)) % 4)
    return bytes(out)


def replace_fstab(entries, stock_fstab: bytes, generated_fstab: bytes):
    count = 0
    result = []
    for magic, vals, name, payload in entries:
        normalized = name[2:] if name.startswith("./") else name
        if normalized == "fstab.flox":
            if payload != stock_fstab:
                raise SystemExit(
                    "ERROR: boot ramdisk fstab does not equal the verified actual-ROM stock baseline"
                )
            payload = generated_fstab
            count += 1
        result.append((magic, vals, name, payload))
    if count != 1:
        raise SystemExit(f"ERROR: expected exactly one root fstab.flox in boot ramdisk, found {count}")
    return result


def update_sha(sha, blob: bytes):
    sha.update(blob)
    sha.update(struct.pack("<I", len(blob)))


def repack_boot(meta, new_ramdisk: bytes, output: Path):
    fields = list(meta["fields"])
    fields[2] = len(new_ramdisk)
    kernel = meta["kernel"]
    second = meta["second"]
    dt = meta["dt"]
    page_size = meta["page_size"]

    sha = hashlib.sha1()
    update_sha(sha, kernel)
    update_sha(sha, new_ramdisk)
    update_sha(sha, second)
    if dt:
        update_sha(sha, dt)
    image_id = sha.digest().ljust(32, b"\x00")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as fp:
        fp.write(BOOT_MAGIC)
        fp.write(struct.pack("<10I", *fields))
        fp.write(meta["board"])
        fp.write(meta["cmdline"])
        fp.write(image_id)
        fp.write(meta["extra"])
        fp.write(b"\x00" * ((-fp.tell()) % page_size))
        for blob in (kernel, new_ramdisk, second, dt):
            if blob:
                fp.write(blob)
                fp.write(b"\x00" * ((-fp.tell()) % page_size))


def main():
    ap = argparse.ArgumentParser(description="Replace only /fstab.flox in a legacy Lineage boot ramdisk")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--stock-fstab", required=True, type=Path)
    ap.add_argument("--fstab", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    stock_fstab = args.stock_fstab.read_bytes()
    fstab = args.fstab.read_bytes()
    if not fstab.endswith(b"\n"):
        raise SystemExit("ERROR: generated fstab must end with newline")
    if b"msm_sdcc.1" in fstab or b" f2fs " in fstab:
        raise SystemExit("ERROR: generated fstab violates diskless contract")

    meta = parse_boot(args.input)
    cpio = decompress_ramdisk(meta["ramdisk"])
    original_entries = parse_newc(cpio)
    patched_entries = replace_fstab(original_entries, stock_fstab, fstab)

    for before, after in zip(original_entries, patched_entries):
        bname = before[2][2:] if before[2].startswith("./") else before[2]
        if bname != "fstab.flox" and before[3] != after[3]:
            raise SystemExit(f"ERROR: non-fstab ramdisk payload changed: {before[2]}")

    new_cpio = build_newc(patched_entries)
    new_ramdisk = gzip_deterministic(new_cpio)
    repack_boot(meta, new_ramdisk, args.output)

    boot_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    fstab_sha = hashlib.sha256(fstab).hexdigest()
    stock_sha = hashlib.sha256(stock_fstab).hexdigest()
    print("DISKLESS_V2_BOOT_FSTAB_PATCHED=1")
    print(f"input={args.input}")
    print(f"output={args.output}")
    print(f"stock_fstab_sha256={stock_sha}")
    print(f"fstab_sha256={fstab_sha}")
    print(f"boot_sha256={boot_sha}")
    print("ramdisk_init=unchanged")
    print("non_fstab_ramdisk_payloads=unchanged")
    print("ramdisk_compression=gzip-deterministic")


if __name__ == "__main__":
    main()
