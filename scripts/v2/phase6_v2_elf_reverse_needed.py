#!/usr/bin/env python3
"""Host-only reverse DT_NEEDED mapper for the accepted system ext4 image.

This is a forensic helper for Phase6 Audit V2. It never writes the image.
It walks selected directories inside the accepted system image, parses ELF
PT_DYNAMIC entries directly (no host readelf dependency), and reports files
whose DT_NEEDED contains a requested SONAME.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import struct
from pathlib import Path

from ext4_readonly import Ext4Error, Ext4Image, S_IFDIR, S_IFREG, u16, u32

EXPECTED_SYSTEM_SHA256 = "a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880"
SECTOR = 512
PT_LOAD = 1
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
            raw = data[off + 8:off + 8 + name_len]
            name = raw.decode("utf-8", "surrogateescape")
            if name not in (".", ".."):
                yield name, ino
        off += rec_len


def walk_regular_files(fs: Ext4Image, root_path: str):
    try:
        root = fs.resolve(root_path)
    except (FileNotFoundError, Ext4Error):
        return
    if root.kind != S_IFDIR:
        return
    stack = [(posixpath.normpath(root_path), root)]
    seen_dirs = set()
    while stack:
        path, inode = stack.pop()
        if inode.number in seen_dirs:
            continue
        seen_dirs.add(inode.number)
        try:
            children = list(iter_dir_entries(fs, inode))
        except Ext4Error:
            continue
        for name, ino in reversed(children):
            child_path = path.rstrip("/") + "/" + name
            try:
                child = fs.inode(ino)
            except Ext4Error:
                continue
            if child.kind == S_IFDIR:
                stack.append((child_path, child))
            elif child.kind == S_IFREG:
                yield child_path, child


def cstring(blob: bytes, off: int) -> str:
    if off < 0 or off >= len(blob):
        raise ValueError("string offset outside dynstr")
    end = blob.find(b"\0", off)
    if end < 0:
        raise ValueError("unterminated dynstr")
    return blob[off:end].decode("utf-8", "replace")


def parse_elf_dynamic(data: bytes):
    if len(data) < 52 or data[:4] != b"\x7fELF":
        return None
    elf_class = data[4]
    endian = data[5]
    if endian != 1 or elf_class not in (1, 2):
        return None
    if elf_class == 1:
        if len(data) < 52:
            return None
        e_phoff = struct.unpack_from("<I", data, 28)[0]
        e_phentsize = struct.unpack_from("<H", data, 42)[0]
        e_phnum = struct.unpack_from("<H", data, 44)[0]
        ph_fmt = "<IIIIIIII"
        ph_need = 32
        dyn_fmt = "<II"
        dyn_size = 8
    else:
        if len(data) < 64:
            return None
        e_phoff = struct.unpack_from("<Q", data, 32)[0]
        e_phentsize = struct.unpack_from("<H", data, 54)[0]
        e_phnum = struct.unpack_from("<H", data, 56)[0]
        ph_fmt = "<IIQQQQQQ"
        ph_need = 56
        dyn_fmt = "<QQ"
        dyn_size = 16
    if e_phentsize < ph_need or e_phoff + e_phentsize * e_phnum > len(data):
        return None

    loads = []
    dynamic = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        fields = struct.unpack_from(ph_fmt, data, off)
        if elf_class == 1:
            p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_flags, _p_align = fields
        else:
            p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = fields
        if p_type == PT_LOAD:
            loads.append((p_vaddr, p_vaddr + p_memsz, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        return {"needed": [], "soname": None}
    d_off, d_size = dynamic
    if d_off + d_size > len(data):
        return None

    strtab_va = None
    strsz = None
    needed_offsets = []
    soname_off = None
    end = d_off + d_size
    cur = d_off
    while cur + dyn_size <= end:
        tag, val = struct.unpack_from(dyn_fmt, data, cur)
        cur += dyn_size
        if tag == DT_NULL:
            break
        if tag == DT_NEEDED:
            needed_offsets.append(int(val))
        elif tag == DT_STRTAB:
            strtab_va = int(val)
        elif tag == DT_STRSZ:
            strsz = int(val)
        elif tag == DT_SONAME:
            soname_off = int(val)
    if strtab_va is None:
        return {"needed": [], "soname": None}

    strtab_file = None
    max_available = None
    for va0, va1, file0, filesz in loads:
        if va0 <= strtab_va < va1:
            delta = strtab_va - va0
            if delta >= filesz:
                continue
            strtab_file = file0 + delta
            max_available = filesz - delta
            break
    if strtab_file is None or strtab_file >= len(data):
        return None
    available = min(len(data) - strtab_file, max_available if max_available is not None else len(data))
    if strsz is not None:
        available = min(available, strsz)
    dynstr = data[strtab_file:strtab_file + available]
    try:
        needed = [cstring(dynstr, off) for off in needed_offsets]
        soname = cstring(dynstr, soname_off) if soname_off is not None else None
    except ValueError:
        return None
    return {"needed": needed, "soname": soname}


def main() -> None:
    ap = argparse.ArgumentParser(description="Reverse-map ELF DT_NEEDED in accepted system image")
    ap.add_argument("--manifest", type=Path,
                    default=Path.home() / "nexus7-diskless-v2/diskless-v2-android.raw.img.manifest.json")
    ap.add_argument("--needed", default="libkeystore_aidl.so")
    ap.add_argument("--root", action="append", default=[],
                    help="filesystem root to scan; repeatable (default: /system/bin,/system/lib,/system/lib64)")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    p1s = [p for p in manifest.get("partitions", []) if int(p.get("number", -1)) == 1]
    if len(p1s) != 1 or p1s[0].get("name") != "system":
        die("manifest does not contain exactly one p1/system")
    source = p1s[0].get("source_path")
    if not source:
        die("p1/system has no source_path")
    system = Path(source)
    if not system.is_file():
        die(f"system image missing: {system}")
    digest = sha256_file(system)
    if digest != EXPECTED_SYSTEM_SHA256:
        die(f"system sha256={digest} expected accepted={EXPECTED_SYSTEM_SHA256}")

    roots = args.root or ["/system/bin", "/system/lib", "/system/lib64"]
    scanned = 0
    elf_count = 0
    direct = []
    soname_paths = {}
    deps_by_path = {}

    with Ext4Image(system) as fs:
        seen_inodes = set()
        for root in roots:
            for path, inode in walk_regular_files(fs, root):
                if inode.number in seen_inodes:
                    continue
                seen_inodes.add(inode.number)
                scanned += 1
                try:
                    data = fs.read_inode(inode)
                except Ext4Error:
                    continue
                parsed = parse_elf_dynamic(data)
                if parsed is None:
                    continue
                elf_count += 1
                deps_by_path[path] = parsed["needed"]
                soname = parsed["soname"] or posixpath.basename(path)
                soname_paths.setdefault(soname, []).append(path)
                if args.needed in parsed["needed"]:
                    direct.append(path)

    direct.sort()
    print("DISKLESS_V2_PHASE6_V2_ELF_REVERSE_NEEDED=PASS")
    print(f"system_image={system}")
    print(f"system_sha256={digest}")
    print(f"target_needed={args.needed}")
    print("scan_roots=" + ",".join(roots))
    print(f"regular_files_scanned={scanned}")
    print(f"elf_files_parsed={elf_count}")
    print(f"direct_dependents={len(direct)}")
    for path in direct:
        print(f"DIRECT_NEEDED path={path!r} needed={args.needed!r}")

    # Also show one-hop parents of direct-dependent libraries. This is useful
    # for cases such as vold -> libkeystore_binder.so -> libkeystore_aidl.so.
    direct_sonames = set()
    for path in direct:
        for soname, paths in soname_paths.items():
            if path in paths:
                direct_sonames.add(soname)
    parents = []
    for path, needed in deps_by_path.items():
        hits = sorted(set(needed) & direct_sonames)
        if hits:
            parents.append((path, hits))
    parents.sort()
    print(f"one_hop_parent_dependents={len(parents)}")
    for path, hits in parents:
        print(f"ONE_HOP_PARENT path={path!r} via={','.join(hits)!r}")


if __name__ == "__main__":
    main()
