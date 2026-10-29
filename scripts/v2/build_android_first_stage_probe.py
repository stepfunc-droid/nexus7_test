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


def die(msg: str):
    raise SystemExit(f"ERROR: {msg}")


def align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def parse_env(path: Path) -> dict[str, str]:
    out = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            die(f"invalid env line: {raw}")
        k, v = line.split("=", 1)
        out[k] = v
    return out


def gzip_deterministic(data: bytes) -> bytes:
    header = b"\x1f\x8b\x08\x00" + struct.pack("<I", 0) + b"\x02\xff"
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = co.compress(data) + co.flush()
    trailer = struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF)
    return header + body + trailer


def parse_boot(path: Path):
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or data[:8] != BOOT_MAGIC:
        die(f"not a legacy Android boot image: {path}")
    fields = list(struct.unpack_from("<10I", data, 8))
    ksz, kaddr, rsz, raddr, ssz, saddr, taddr, page, dsz, unused = fields
    if page <= 0 or page & (page - 1):
        die(f"invalid boot page size: {page}")
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
        die(f"truncated boot image: {path}")
    full_cmdline = (cmdline.split(b"\0", 1)[0] + extra.split(b"\0", 1)[0]).decode("utf-8", "replace").strip()
    return {
        "data": data,
        "fields": fields,
        "board": board,
        "cmdline_raw": cmdline,
        "extra_raw": extra,
        "cmdline": full_cmdline,
        "kernel": data[k0:k1],
        "ramdisk": data[r0:r1],
        "second": data[s0:s1],
        "dt": data[d0:d1],
        "page": page,
    }


def decompress_ramdisk(blob: bytes) -> bytes:
    if blob.startswith(b"\x1f\x8b"):
        return zlib.decompress(blob, 16 + zlib.MAX_WBITS)
    if blob.startswith(b"\xfd7zXZ\x00"):
        return lzma.decompress(blob)
    if any(blob.startswith(m) for m in NEWC_MAGICS):
        return blob
    die("unsupported ramdisk compression")


def parse_newc(data: bytes):
    entries = []
    off = 0
    while True:
        if off + 110 > len(data):
            die("truncated newc archive")
        magic = data[off:off + 6]
        if magic not in NEWC_MAGICS:
            die(f"bad newc magic at offset {off}: {magic!r}")
        raw = data[off + 6:off + 110]
        try:
            vals = [int(raw[i:i + 8], 16) for i in range(0, 104, 8)]
        except ValueError as exc:
            raise SystemExit(f"ERROR: bad newc header at offset {off}") from exc
        namesize = vals[11]
        filesize = vals[6]
        n0 = off + 110
        n1 = n0 + namesize
        if namesize <= 0 or n1 > len(data):
            die("invalid newc namesize")
        name_blob = data[n0:n1]
        if not name_blob.endswith(b"\0"):
            die("newc filename not NUL terminated")
        name = name_blob[:-1].decode("utf-8", "surrogateescape")
        d0 = align_up(n1, 4)
        d1 = d0 + filesize
        if d1 > len(data):
            die(f"truncated newc payload: {name}")
        entries.append([magic, vals, name, data[d0:d1]])
        off = align_up(d1, 4)
        if name == "TRAILER!!!":
            break
    return entries


def norm(name: str) -> str:
    return name[2:] if name.startswith("./") else name


def entry_map(entries):
    out = {}
    for e in entries:
        n = norm(e[2])
        if n in out:
            die(f"duplicate cpio entry: {n}")
        out[n] = e
    return out


def make_entry(name: str, payload: bytes, mode: int, ino: int):
    # ino, mode, uid, gid, nlink, mtime, filesize, devmajor, devminor,
    # rdevmajor, rdevminor, namesize, check
    vals = [ino, mode, 0, 0, 2 if (mode & 0o170000) == 0o040000 else 1,
            0, len(payload), 0, 0, 0, 0, len(name.encode()) + 1, 0]
    return [b"070701", vals, name, payload]


def build_newc(entries) -> bytes:
    out = bytearray()
    for magic, vals0, name, payload in entries:
        vals = list(vals0)
        name_bytes = name.encode("utf-8", "surrogateescape") + b"\0"
        vals[6] = len(payload)
        vals[11] = len(name_bytes)
        vals[12] = (sum(payload) & 0xFFFFFFFF) if magic == b"070702" else 0
        out += magic
        out += b"".join(f"{v:08x}".encode("ascii") for v in vals)
        out += name_bytes
        out += b"\0" * ((-len(out)) % 4)
        out += payload
        out += b"\0" * ((-len(out)) % 4)
    return bytes(out)


def update_sha(sha, blob: bytes):
    sha.update(blob)
    sha.update(struct.pack("<I", len(blob)))


def clean_cmdline(stock: str) -> str:
    remove_prefixes = ("androidboot.diskless=", "nbd.max_part=", "panic=", "rdinit=")
    tokens = [t for t in stock.split() if not t.startswith(remove_prefixes)]
    if any(t == "androidboot.selinux=permissive" for t in tokens):
        die("stock Android boot unexpectedly already requests SELinux permissive")
    tokens += ["androidboot.diskless=1", "nbd.max_part=8", "panic=5", "rdinit=/init"]
    result = " ".join(tokens)
    if len(result.encode()) > 1536:
        die("probe cmdline exceeds legacy boot header capacity")
    return result


def repack(meta, kernel: bytes, ramdisk: bytes, cmdline: str, output: Path):
    fields = list(meta["fields"])
    fields[0] = len(kernel)
    fields[2] = len(ramdisk)
    page = meta["page"]
    cmd = cmdline.encode()

    sha = hashlib.sha1()
    update_sha(sha, kernel)
    update_sha(sha, ramdisk)
    update_sha(sha, meta["second"])
    if meta["dt"]:
        update_sha(sha, meta["dt"])
    image_id = sha.digest().ljust(32, b"\0")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as fp:
        fp.write(BOOT_MAGIC)
        fp.write(struct.pack("<10I", *fields))
        fp.write(meta["board"])
        fp.write(cmd[:512].ljust(512, b"\0"))
        fp.write(image_id)
        fp.write(cmd[512:].ljust(1024, b"\0"))
        fp.write(b"\0" * ((-fp.tell()) % page))
        for blob in (kernel, ramdisk, meta["second"], meta["dt"]):
            if blob:
                fp.write(blob)
                fp.write(b"\0" * ((-fp.tell()) % page))


def main():
    ap = argparse.ArgumentParser(description="Build a deterministic single-NBD Android first-stage mount probe")
    ap.add_argument("--android-boot", required=True, type=Path,
                    help="Phase 5B boot-fstab-only.img")
    ap.add_argument("--transport-boot", required=True, type=Path,
                    help="accepted Phase 4 diskless-v2-transport.img")
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--wrapper", required=True, type=Path)
    ap.add_argument("--phase4-env", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    env = parse_env(args.phase4_env)
    expected_kernel_sha = env.get("KERNEL_ZIMAGE_SHA256")
    if not expected_kernel_sha:
        die("phase4 env missing KERNEL_ZIMAGE_SHA256")

    android = parse_boot(args.android_boot)
    transport = parse_boot(args.transport_boot)

    # Header geometry was already proven on real hardware in Phase 4. Require
    # the Android artifact to use the same physical load geometry before mixing
    # its stock ramdisk with the accepted diskless kernel.
    for idx, label in ((1, "kernel_addr"), (3, "ramdisk_addr"), (5, "second_addr"),
                       (6, "tags_addr"), (7, "page_size")):
        if android["fields"][idx] != transport["fields"][idx]:
            die(f"boot geometry mismatch for {label}: android={android['fields'][idx]} transport={transport['fields'][idx]}")

    kernel = transport["kernel"]
    kernel_sha = hashlib.sha256(kernel).hexdigest()
    if kernel_sha != expected_kernel_sha:
        die(f"transport kernel sha256={kernel_sha} expected accepted Phase4={expected_kernel_sha}")
    if "androidboot.diskless=1" not in transport["cmdline"] or "nbd.max_part=8" not in transport["cmdline"]:
        die("transport boot cmdline does not carry accepted diskless policy")

    android_entries = parse_newc(decompress_ramdisk(android["ramdisk"]))
    transport_entries = entry_map(parse_newc(decompress_ramdisk(transport["ramdisk"])))
    amap = entry_map(android_entries)

    if "init" not in amap:
        die("Android ramdisk missing /init")
    if "init.android" in amap or "bin/busybox" in amap or "etc/diskless-v2-layout" in amap:
        die("Android ramdisk already contains probe-only entries")
    if "bin/busybox" not in transport_entries or "etc/diskless-v2-layout" not in transport_entries:
        die("accepted transport ramdisk missing BusyBox/layout contract")

    generated_fstab = args.generated_fstab.read_bytes()
    if hashlib.sha256(generated_fstab).hexdigest() == "":
        die("generated fstab digest failure")
    fstab_entries = [e for e in android_entries if norm(e[2]) == "fstab.flox"]
    if len(fstab_entries) != 1 or fstab_entries[0][3] != generated_fstab:
        die("Android input boot does not contain the exact Phase 5 generated fstab")

    wrapper = args.wrapper.read_bytes()
    if not wrapper.startswith(b"#!/bin/busybox sh\n"):
        die("probe wrapper must use the injected static BusyBox interpreter")

    original_init = bytes(amap["init"][3])
    original_init_sha = hashlib.sha256(original_init).hexdigest()

    # Replace only the original /init payload. Preserve its metadata and keep an
    # exact copy as /init.android for the handoff.
    patched = []
    trailer = None
    max_ino = 0
    for e in android_entries:
        max_ino = max(max_ino, int(e[1][0]))
        if norm(e[2]) == "TRAILER!!!":
            trailer = e
            continue
        if norm(e[2]) == "init":
            e = [e[0], list(e[1]), e[2], wrapper]
        patched.append(e)

    if trailer is None:
        die("Android ramdisk missing cpio trailer")

    next_ino = max_ino + 1
    names = {norm(e[2]) for e in patched}
    if "bin" not in names:
        patched.append(make_entry("bin", b"", 0o040755, next_ino)); next_ino += 1
    if "etc" not in names:
        patched.append(make_entry("etc", b"", 0o040755, next_ino)); next_ino += 1

    init_meta = list(amap["init"][1])
    init_meta[0] = next_ino; next_ino += 1
    patched.append([amap["init"][0], init_meta, "init.android", original_init])

    busy = transport_entries["bin/busybox"]
    busy_meta = list(busy[1]); busy_meta[0] = next_ino; next_ino += 1
    patched.append([busy[0], busy_meta, "bin/busybox", bytes(busy[3])])

    layout = transport_entries["etc/diskless-v2-layout"]
    layout_meta = list(layout[1]); layout_meta[0] = next_ino; next_ino += 1
    patched.append([layout[0], layout_meta, "etc/diskless-v2-layout", bytes(layout[3])])
    patched.append(trailer)

    cpio = build_newc(patched)
    ramdisk = gzip_deterministic(cpio)
    cmdline = clean_cmdline(android["cmdline"])
    repack(android, kernel, ramdisk, cmdline, args.output)

    # Parse the result again rather than trusting the construction path.
    result = parse_boot(args.output)
    rmap = entry_map(parse_newc(decompress_ramdisk(result["ramdisk"])))
    if rmap.get("init.android", [None, None, None, None])[3] != original_init:
        die("repacked probe lost exact original /init payload")
    if rmap.get("init", [None, None, None, None])[3] != wrapper:
        die("repacked probe /init is not the supervisor wrapper")
    if rmap.get("fstab.flox", [None, None, None, None])[3] != generated_fstab:
        die("repacked probe fstab differs from Phase 5 fstab")
    if hashlib.sha256(result["kernel"]).hexdigest() != expected_kernel_sha:
        die("repacked probe kernel differs from accepted Phase 4 kernel")

    print("DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1")
    print(f"output={args.output}")
    print(f"output_sha256={hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print(f"kernel_sha256={kernel_sha}")
    print(f"android_init_sha256={original_init_sha}")
    print(f"generated_fstab_sha256={hashlib.sha256(generated_fstab).hexdigest()}")
    print(f"busybox_sha256={hashlib.sha256(bytes(busy[3])).hexdigest()}")
    print("android_init=preserved-as-/init.android")
    print("probe_init=single-nbd-supervisor")
    print("selinux_policy=stock-cmdline-unchanged")
    print("late_android_boot=intentionally-stopped-after-first-stage-mounts")
    print(f"cmdline={cmdline}")


if __name__ == "__main__":
    main()
